package io.mcpycore;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;

import java.net.URI;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;
import java.util.logging.Logger;

/**
 * McPy-Core Java SDK — official Java client for driving Minecraft bots
 * through the McPy-Core WebSocket bridge server.
 *
 * <p>Prerequisites: start the Python bridge first:</p>
 * <pre>
 *   pip install mcpy-core
 *   python -m mcpycore.bridge --port 25580
 * </pre>
 *
 * <p>Quick start:</p>
 * <pre>{@code
 * McPyCore client = new McPyCore("ws://localhost:25580");
 *
 * client.on("connected", msg -> System.out.println("Online! " + msg));
 * client.on("chat", msg -> {
 *     String message = msg.get("message").getAsString();
 *     String sender  = msg.get("sender").getAsString();
 *     System.out.println("[" + sender + "] " + message);
 *     if (message.equals("ping")) client.chat("pong!");
 * });
 * client.on("spawn", msg -> System.out.println("Spawned!"));
 *
 * client.connect(ConnectOptions.builder()
 *     .host("play.example.com")
 *     .username("JavaBot")
 *     .protocol(775)
 *     .humanize(true)
 *     .build());
 * }</pre>
 */
public class McPyCore {
    private static final Logger log = Logger.getLogger(McPyCore.class.getName());
    private static final Gson GSON = new Gson();

    private final String bridgeUrl;
    private BridgeSocket ws;
    private final Map<String, List<Consumer<JsonObject>>> listeners = new ConcurrentHashMap<>();

    // Player state
    public volatile double x, y, z, yaw, pitch;
    public volatile float health = 20f;
    public volatile int food = 20, gameMode = 0, entityId = 0;

    // ── Constructor ───────────────────────────────────────────────────────

    public McPyCore(String bridgeUrl) {
        this.bridgeUrl = bridgeUrl;
    }

    /** Create with default bridge URL ws://localhost:25580 */
    public McPyCore() {
        this("ws://localhost:25580");
    }

    // ── Bridge connection ─────────────────────────────────────────────────

    /** Open the WebSocket connection to the McPy-Core bridge. Blocks until open. */
    public McPyCore openBridge() throws Exception {
        CountDownLatch latch = new CountDownLatch(1);
        ws = new BridgeSocket(new URI(bridgeUrl), latch);
        ws.connect();
        if (!latch.await(10, TimeUnit.SECONDS)) {
            throw new RuntimeException("Timed out connecting to bridge at " + bridgeUrl);
        }
        return this;
    }

    // ── MC actions ────────────────────────────────────────────────────────

    /**
     * Connect to a Minecraft server. Opens the bridge if not already open.
     */
    public void connect(ConnectOptions opts) {
        if (ws == null || !ws.isOpen()) {
            try { openBridge(); } catch (Exception e) { throw new RuntimeException(e); }
        }
        JsonObject msg = new JsonObject();
        msg.addProperty("action",       "connect");
        msg.addProperty("host",          opts.host);
        msg.addProperty("port",          opts.port);
        msg.addProperty("username",      opts.username);
        msg.addProperty("protocol",      opts.protocol);
        if (opts.accessToken != null) msg.addProperty("access_token", opts.accessToken);
        msg.addProperty("humanize",      opts.humanize);
        send(msg);
    }

    /** Disconnect from the Minecraft server. */
    public void disconnect() { send(action("disconnect")); }

    /** Send a chat message or slash command. */
    public void chat(String message) {
        JsonObject msg = action("chat");
        msg.addProperty("message", message);
        send(msg);
    }

    /** Move to coordinates. */
    public void move(double x, double y, double z, double yaw, double pitch) {
        JsonObject msg = action("move");
        msg.addProperty("x", x); msg.addProperty("y", y); msg.addProperty("z", z);
        msg.addProperty("yaw", yaw); msg.addProperty("pitch", pitch);
        send(msg);
        this.x = x; this.y = y; this.z = z; this.yaw = yaw; this.pitch = pitch;
    }

    /** Change look direction without moving. */
    public void look(double yaw, double pitch) {
        JsonObject msg = action("look");
        msg.addProperty("yaw", yaw);
        msg.addProperty("pitch", pitch);
        send(msg);
        this.yaw = yaw; this.pitch = pitch;
    }

    /** Swing main hand (0) or off hand (1). */
    public void swingArm(int hand) {
        JsonObject msg = action("swing_arm");
        msg.addProperty("hand", hand);
        send(msg);
    }

    /** Switch hotbar slot (0–8). */
    public void setHeldSlot(int slot) {
        JsonObject msg = action("set_held_slot");
        msg.addProperty("slot", slot);
        send(msg);
    }

    /** Respawn after death. */
    public void respawn() { send(action("respawn")); }

    // ── Event API ─────────────────────────────────────────────────────────

    /**
     * Register an event listener.
     *
     * <p>Event names: connected, disconnected, error, chat, system_chat,
     * health, position, spawn, login, keepalive, death, block_update,
     * chunk_load, chunk_unload, title, action_bar, game_mode, time_update,
     * remove_entities, transfer.</p>
     *
     * @param event    Event name
     * @param listener Called with the raw JSON event object
     */
    public McPyCore on(String event, Consumer<JsonObject> listener) {
        listeners.computeIfAbsent(event, k -> new CopyOnWriteArrayList<>()).add(listener);
        return this;
    }

    /** Remove all listeners for an event. */
    public McPyCore off(String event) {
        listeners.remove(event);
        return this;
    }

    // ── Internal ──────────────────────────────────────────────────────────

    private void send(JsonObject msg) {
        if (ws != null && ws.isOpen()) {
            ws.send(GSON.toJson(msg));
        }
    }

    private static JsonObject action(String name) {
        JsonObject o = new JsonObject();
        o.addProperty("action", name);
        return o;
    }

    private void dispatch(String raw) {
        try {
            JsonObject msg   = JsonParser.parseString(raw).getAsJsonObject();
            String eventName = msg.has("event") ? msg.get("event").getAsString() : "";

            // Update player state from events
            switch (eventName) {
                case "position" -> { x = msg.get("x").getAsDouble(); y = msg.get("y").getAsDouble();
                    z = msg.get("z").getAsDouble(); yaw = msg.get("yaw").getAsDouble();
                    pitch = msg.get("pitch").getAsDouble(); }
                case "health"   -> { health = msg.get("health").getAsFloat();
                    food = msg.get("food").getAsInt(); }
                case "login"    -> { entityId = msg.get("entity_id").getAsInt();
                    gameMode = msg.get("game_mode").getAsInt(); }
                case "game_mode" -> { gameMode = msg.get("game_mode").getAsInt(); }
            }

            List<Consumer<JsonObject>> handlers = listeners.get(eventName);
            if (handlers != null) handlers.forEach(h -> {
                try { h.accept(msg); } catch (Exception ex) {
                    log.warning("Listener error for event " + eventName + ": " + ex.getMessage());
                }
            });
        } catch (Exception ex) {
            log.warning("Failed to dispatch event: " + ex.getMessage());
        }
    }

    // ── Inner WebSocket ───────────────────────────────────────────────────

    private class BridgeSocket extends WebSocketClient {
        private final CountDownLatch openLatch;

        BridgeSocket(URI uri, CountDownLatch latch) {
            super(uri);
            this.openLatch = latch;
        }

        @Override public void onOpen(ServerHandshake h)   { openLatch.countDown(); }
        @Override public void onClose(int c, String r, boolean re) { /* auto-reconnect could go here */ }
        @Override public void onError(Exception ex)        { log.warning("Bridge error: " + ex.getMessage()); }
        @Override public void onMessage(String message)    { dispatch(message); }
    }

    // ── ConnectOptions builder ────────────────────────────────────────────

    public static class ConnectOptions {
        public final String  host;
        public final int     port;
        public final String  username;
        public final String  accessToken;
        public final int     protocol;
        public final boolean humanize;

        private ConnectOptions(Builder b) {
            this.host        = b.host;
            this.port        = b.port;
            this.username    = b.username;
            this.accessToken = b.accessToken;
            this.protocol    = b.protocol;
            this.humanize    = b.humanize;
        }

        public static Builder builder() { return new Builder(); }

        public static class Builder {
            private String  host        = "localhost";
            private int     port        = 25565;
            private String  username    = "JavaBot";
            private String  accessToken = null;
            private int     protocol    = 775;
            private boolean humanize    = false;

            public Builder host(String v)        { host = v; return this; }
            public Builder port(int v)           { port = v; return this; }
            public Builder username(String v)    { username = v; return this; }
            public Builder accessToken(String v) { accessToken = v; return this; }
            public Builder protocol(int v)       { protocol = v; return this; }
            public Builder humanize(boolean v)   { humanize = v; return this; }
            public ConnectOptions build()        { return new ConnectOptions(this); }
        }
    }
}
