// McPy-Core C# SDK — official .NET client for McPy-Core.
//
// Connects to a running McPy-Core bridge server (Python) and exposes a clean,
// event-driven API for driving Minecraft Java Edition bots from .NET.
//
// Prerequisites: start the Python bridge first:
//   pip install mcpy-core
//   python -m mcpycore.bridge --port 25580
//
// Quick start:
//   var client = new McPyCoreClient("ws://localhost:25580");
//   client.OnChat += e => Console.WriteLine($"[{e.Sender}] {e.Message}");
//   client.OnSpawn += e => Console.WriteLine($"Spawned at {e.X:F1}, {e.Y:F1}, {e.Z:F1}");
//   await client.ConnectAsync(new() { Host = "play.example.com", Username = "CSharpBot" });
//   await Task.Delay(-1);  // run forever

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using Websocket.Client;

namespace McPyCore;

// ── Event records ─────────────────────────────────────────────────────────────

public record ConnectedEvent(string Version, int Protocol);
public record DisconnectedEvent(string Reason);
public record ChatEvent(string Message, string Sender);
public record SystemChatEvent(string Content, bool Overlay);
public record HealthEvent(float Health, int Food, float Saturation);
public record PositionEvent(double X, double Y, double Z, double Yaw, double Pitch);
public record SpawnEvent(double X, double Y, double Z);
public record LoginEvent(int EntityId, int GameMode);
public record BlockUpdateEvent(int X, int Y, int Z, int StateId);
public record ChunkEvent(int Cx, int Cz);

// ── ConnectOptions ────────────────────────────────────────────────────────────

public class ConnectOptions
{
    /// <summary>Minecraft server hostname or IP.</summary>
    public string Host { get; init; } = "localhost";
    /// <summary>Minecraft server port (default: 25565).</summary>
    public int Port { get; init; } = 25565;
    /// <summary>Player username.</summary>
    public string Username { get; init; } = "CSharpBot";
    /// <summary>Microsoft access token (null = offline mode).</summary>
    public string? AccessToken { get; init; }
    /// <summary>Minecraft protocol version integer (default: 775 = 1.21.11).</summary>
    public int Protocol { get; init; } = 775;
    /// <summary>Enable humanized anti-bot timing and delays.</summary>
    public bool Humanize { get; init; }
}

// ── McPyCoreClient ────────────────────────────────────────────────────────────

/// <summary>
/// Official C# client for McPy-Core.
///
/// Each instance manages one Minecraft bot session through the McPy-Core
/// WebSocket bridge server.
/// </summary>
public sealed class McPyCoreClient : IAsyncDisposable
{
    private readonly Uri _bridgeUri;
    private WebsocketClient? _ws;

    // ── Player state ──────────────────────────────────────────────────────
    public double X { get; private set; }
    public double Y { get; private set; }
    public double Z { get; private set; }
    public double Yaw { get; private set; }
    public double Pitch { get; private set; }
    public float Health { get; private set; } = 20f;
    public int Food { get; private set; } = 20;
    public int GameMode { get; private set; }
    public int EntityId { get; private set; }
    public bool IsConnected { get; private set; }

    // ── Events ────────────────────────────────────────────────────────────
    public event Action<ConnectedEvent>?    OnConnected;
    public event Action<DisconnectedEvent>? OnDisconnected;
    public event Action<Exception>?         OnError;
    public event Action<ChatEvent>?         OnChat;
    public event Action<SystemChatEvent>?   OnSystemChat;
    public event Action<HealthEvent>?       OnHealth;
    public event Action<PositionEvent>?     OnPosition;
    public event Action<SpawnEvent>?        OnSpawn;
    public event Action<LoginEvent>?        OnLogin;
    public event Action<double>?            OnKeepalive;
    public event Action?                    OnDeath;
    public event Action<BlockUpdateEvent>?  OnBlockUpdate;
    public event Action<ChunkEvent>?        OnChunkLoad;
    public event Action<ChunkEvent>?        OnChunkUnload;
    public event Action<string>?            OnTitle;
    public event Action<string>?            OnActionBar;
    public event Action<int>?               OnGameMode;
    public event Action<JsonObject>?        OnRawEvent;

    // ── Constructors ──────────────────────────────────────────────────────

    public McPyCoreClient(string bridgeUrl = "ws://localhost:25580")
        => _bridgeUri = new Uri(bridgeUrl);

    // ── Bridge connection ─────────────────────────────────────────────────

    /// <summary>Open the WebSocket connection to the McPy-Core bridge.</summary>
    public async Task OpenBridgeAsync(CancellationToken ct = default)
    {
        _ws = new WebsocketClient(_bridgeUri);
        _ws.MessageReceived.Subscribe(msg => HandleMessage(msg.Text ?? ""));
        await _ws.Start();
    }

    // ── MC actions ────────────────────────────────────────────────────────

    /// <summary>Connect to a Minecraft server. Opens the bridge if needed.</summary>
    public async Task ConnectAsync(ConnectOptions opts, CancellationToken ct = default)
    {
        if (_ws is null || !_ws.IsRunning)
            await OpenBridgeAsync(ct);

        Send(new {
            action       = "connect",
            host         = opts.Host,
            port         = opts.Port,
            username     = opts.Username,
            access_token = opts.AccessToken,
            protocol     = opts.Protocol,
            humanize     = opts.Humanize,
        });
    }

    /// <summary>Disconnect from the Minecraft server.</summary>
    public void Disconnect() => Send(new { action = "disconnect" });

    /// <summary>Send a chat message or slash command.</summary>
    public void Chat(string message) => Send(new { action = "chat", message });

    /// <summary>Move to a position.</summary>
    public void Move(double x, double y, double z, double yaw = 0, double pitch = 0)
    {
        X = x; Y = y; Z = z; Yaw = yaw; Pitch = pitch;
        Send(new { action = "move", x, y, z, yaw, pitch });
    }

    /// <summary>Change look direction without moving.</summary>
    public void Look(double yaw, double pitch)
    {
        Yaw = yaw; Pitch = pitch;
        Send(new { action = "look", yaw, pitch });
    }

    /// <summary>Swing arm (0 = main hand, 1 = off hand).</summary>
    public void SwingArm(int hand = 0) => Send(new { action = "swing_arm", hand });

    /// <summary>Switch hotbar slot (0–8).</summary>
    public void SetHeldSlot(int slot) => Send(new { action = "set_held_slot", slot });

    /// <summary>Respawn after death.</summary>
    public void Respawn() => Send(new { action = "respawn" });

    // ── Internal ──────────────────────────────────────────────────────────

    private void Send(object payload) =>
        _ws?.Send(JsonSerializer.Serialize(payload));

    private void HandleMessage(string raw)
    {
        try
        {
            var obj = JsonNode.Parse(raw)?.AsObject();
            if (obj is null) return;

            OnRawEvent?.Invoke(obj);

            var ev = obj["event"]?.GetValue<string>() ?? "";
            switch (ev)
            {
                case "connected":
                    IsConnected = true;
                    OnConnected?.Invoke(new(
                        obj["version"]?.GetValue<string>() ?? "",
                        obj["protocol"]?.GetValue<int>() ?? 0));
                    break;

                case "disconnected":
                    IsConnected = false;
                    OnDisconnected?.Invoke(new(obj["reason"]?.GetValue<string>() ?? ""));
                    break;

                case "error":
                    OnError?.Invoke(new Exception(obj["message"]?.GetValue<string>() ?? "Unknown"));
                    break;

                case "chat":
                    OnChat?.Invoke(new(
                        obj["message"]?.GetValue<string>() ?? "",
                        obj["sender"]?.GetValue<string>()  ?? ""));
                    break;

                case "system_chat":
                    OnSystemChat?.Invoke(new(
                        obj["content"]?.GetValue<string>() ?? "",
                        obj["overlay"]?.GetValue<bool>() ?? false));
                    break;

                case "health":
                    Health = obj["health"]?.GetValue<float>() ?? Health;
                    Food   = obj["food"]?.GetValue<int>()   ?? Food;
                    OnHealth?.Invoke(new(Health, Food, obj["saturation"]?.GetValue<float>() ?? 0));
                    break;

                case "position":
                    X = obj["x"]?.GetValue<double>() ?? X;
                    Y = obj["y"]?.GetValue<double>() ?? Y;
                    Z = obj["z"]?.GetValue<double>() ?? Z;
                    Yaw   = obj["yaw"]?.GetValue<double>()   ?? Yaw;
                    Pitch = obj["pitch"]?.GetValue<double>() ?? Pitch;
                    OnPosition?.Invoke(new(X, Y, Z, Yaw, Pitch));
                    break;

                case "spawn":
                    OnSpawn?.Invoke(new(
                        obj["x"]?.GetValue<double>() ?? 0,
                        obj["y"]?.GetValue<double>() ?? 0,
                        obj["z"]?.GetValue<double>() ?? 0));
                    break;

                case "login":
                    EntityId = obj["entity_id"]?.GetValue<int>() ?? EntityId;
                    GameMode = obj["game_mode"]?.GetValue<int>() ?? GameMode;
                    OnLogin?.Invoke(new(EntityId, GameMode));
                    break;

                case "keepalive":
                    OnKeepalive?.Invoke(obj["latency_ms"]?.GetValue<double>() ?? 0);
                    break;

                case "death":
                    OnDeath?.Invoke();
                    break;

                case "block_update":
                    OnBlockUpdate?.Invoke(new(
                        obj["x"]?.GetValue<int>()        ?? 0,
                        obj["y"]?.GetValue<int>()        ?? 0,
                        obj["z"]?.GetValue<int>()        ?? 0,
                        obj["state_id"]?.GetValue<int>() ?? 0));
                    break;

                case "chunk_load":
                    OnChunkLoad?.Invoke(new(
                        obj["cx"]?.GetValue<int>() ?? 0,
                        obj["cz"]?.GetValue<int>() ?? 0));
                    break;

                case "chunk_unload":
                    OnChunkUnload?.Invoke(new(
                        obj["cx"]?.GetValue<int>() ?? 0,
                        obj["cz"]?.GetValue<int>() ?? 0));
                    break;

                case "title":
                    OnTitle?.Invoke(obj["text"]?.GetValue<string>() ?? "");
                    break;

                case "action_bar":
                    OnActionBar?.Invoke(obj["text"]?.GetValue<string>() ?? "");
                    break;

                case "game_mode":
                    GameMode = obj["game_mode"]?.GetValue<int>() ?? GameMode;
                    OnGameMode?.Invoke(GameMode);
                    break;
            }
        }
        catch (Exception ex)
        {
            OnError?.Invoke(ex);
        }
    }

    public async ValueTask DisposeAsync()
    {
        Disconnect();
        if (_ws is not null)
        {
            await _ws.Stop(System.Net.WebSockets.WebSocketCloseStatus.NormalClosure, "Disposed");
            _ws.Dispose();
        }
    }
}
