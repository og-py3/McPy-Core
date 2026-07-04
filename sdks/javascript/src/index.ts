/**
 * mcpy-core-js — Official JavaScript/TypeScript SDK for McPy-Core.
 *
 * Connects to a running McPy-Core bridge server (Python) and exposes a clean,
 * event-driven API for driving Minecraft Java Edition bots from Node.js.
 *
 * Prerequisites
 * -------------
 * Start the Python bridge first:
 *   python -m mcpycore.bridge --port 25580
 *
 * Quick start
 * -----------
 *   import { McPyCoreClient } from 'mcpy-core-js';
 *
 *   const client = new McPyCoreClient({ bridgeUrl: 'ws://localhost:25580' });
 *
 *   client.on('connected', (info) => console.log('Online!', info));
 *   client.on('chat', ({ message, sender }) => client.chat(`Echo: ${message}`));
 *
 *   await client.connect({ host: 'play.example.com', username: 'JSBot' });
 */

import WebSocket from 'ws';
import { EventEmitter } from 'events';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ClientOptions {
  /** URL of the McPy-Core bridge WebSocket server (default: ws://localhost:25580) */
  bridgeUrl?: string;
  /** Reconnect to bridge if connection drops (default: true) */
  autoReconnect?: boolean;
  /** Delay in ms before reconnecting to bridge (default: 2000) */
  reconnectDelay?: number;
}

export interface ConnectOptions {
  /** Minecraft server hostname or IP */
  host: string;
  /** Minecraft server port (default: 25565) */
  port?: number;
  /** Player username */
  username?: string;
  /** Microsoft access token (omit for offline mode) */
  accessToken?: string | null;
  /** Minecraft protocol version integer (default: 775 = 1.21.11) */
  protocol?: number;
  /** Enable humanized anti-bot timing (true = defaults, or config object) */
  humanize?: boolean | HumanizeOptions;
}

export interface HumanizeOptions {
  authme_enabled?: boolean;
  authme_password?: string;
  authme_register_password?: string;
  pre_handshake_delay?: [number, number];
  pre_login_delay?: [number, number];
  post_login_delay?: [number, number];
  keepalive_jitter?: [number, number];
  settle_on_spawn?: boolean;
  chat_triggers?: Array<[string, string]>;
}

export interface Position {
  x: number; y: number; z: number;
  yaw: number; pitch: number;
}

// ── McPyCoreClient ────────────────────────────────────────────────────────────

export class McPyCoreClient extends EventEmitter {
  private readonly bridgeUrl: string;
  private readonly autoReconnect: boolean;
  private readonly reconnectDelay: number;

  private ws: WebSocket | null = null;
  private _connected = false;
  private _reconnecting = false;

  // Player state (updated from events)
  public position: Position = { x: 0, y: 64, z: 0, yaw: 0, pitch: 0 };
  public health = 20;
  public food = 20;
  public gameMode = 0;
  public entityId = 0;

  constructor(options: ClientOptions = {}) {
    super();
    this.bridgeUrl   = options.bridgeUrl    ?? 'ws://localhost:25580';
    this.autoReconnect = options.autoReconnect ?? true;
    this.reconnectDelay = options.reconnectDelay ?? 2000;
  }

  // ── Bridge connection ───────────────────────────────────────────────────

  /** Open the WebSocket connection to the bridge (does NOT connect to MC yet). */
  openBridge(): Promise<void> {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(this.bridgeUrl);
      this.ws = ws;

      ws.once('open', () => {
        this._reconnecting = false;
        resolve();
      });

      ws.once('error', (err) => reject(err));

      ws.on('message', (data) => {
        try {
          const msg = JSON.parse(data.toString());
          this._handleEvent(msg);
        } catch {
          // ignore malformed messages
        }
      });

      ws.on('close', () => {
        this._connected = false;
        this.emit('bridge_close');
        if (this.autoReconnect && !this._reconnecting) {
          this._reconnecting = true;
          setTimeout(() => this.openBridge().catch(() => {}), this.reconnectDelay);
        }
      });
    });
  }

  /** Send a raw action to the bridge. */
  private send(action: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(action));
    }
  }

  // ── MC actions ─────────────────────────────────────────────────────────

  /**
   * Connect to a Minecraft server through the bridge.
   * Opens the bridge first if not already open.
   */
  async connect(opts: ConnectOptions): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      await this.openBridge();
    }
    this.send({
      action:       'connect',
      host:         opts.host,
      port:         opts.port        ?? 25565,
      username:     opts.username    ?? 'JSBot',
      access_token: opts.accessToken ?? null,
      protocol:     opts.protocol    ?? 775,
      humanize:     opts.humanize    ?? false,
    });
  }

  /** Disconnect from the Minecraft server. */
  disconnect(): void {
    this.send({ action: 'disconnect' });
  }

  /** Send a chat message or slash command. */
  chat(message: string): void {
    this.send({ action: 'chat', message });
  }

  /** Move to a position. */
  move(x: number, y: number, z: number, yaw = 0, pitch = 0): void {
    this.send({ action: 'move', x, y, z, yaw, pitch });
    Object.assign(this.position, { x, y, z, yaw, pitch });
  }

  /** Change look direction without moving. */
  look(yaw: number, pitch: number): void {
    this.send({ action: 'look', yaw, pitch });
    this.position.yaw   = yaw;
    this.position.pitch = pitch;
  }

  /** Swing arm (0 = main hand, 1 = off hand). */
  swingArm(hand = 0): void {
    this.send({ action: 'swing_arm', hand });
  }

  /** Switch hotbar slot (0–8). */
  setHeldSlot(slot: number): void {
    this.send({ action: 'set_held_slot', slot });
  }

  /** Respawn after death. */
  respawn(): void {
    this.send({ action: 'respawn' });
  }

  get isConnected(): boolean { return this._connected; }

  // ── Event routing ───────────────────────────────────────────────────────

  private _handleEvent(msg: Record<string, unknown>): void {
    const ev = msg.event as string;
    switch (ev) {
      case 'connected':
        this._connected = true;
        this.emit('connected', { version: msg.version, protocol: msg.protocol });
        break;
      case 'disconnected':
        this._connected = false;
        this.emit('disconnected', msg.reason as string);
        break;
      case 'error':
        this.emit('error', new Error(msg.message as string));
        break;
      case 'chat':
        this.emit('chat', { message: msg.message, sender: msg.sender });
        break;
      case 'system_chat':
        this.emit('system_chat', { content: msg.content, overlay: msg.overlay });
        break;
      case 'health':
        this.health = msg.health as number;
        this.food   = msg.food   as number;
        this.emit('health', { health: msg.health, food: msg.food, saturation: msg.saturation });
        break;
      case 'position':
        Object.assign(this.position, { x: msg.x, y: msg.y, z: msg.z, yaw: msg.yaw, pitch: msg.pitch });
        this.emit('position', this.position);
        break;
      case 'spawn':
        this.emit('spawn', { x: msg.x, y: msg.y, z: msg.z });
        break;
      case 'login':
        this.entityId = msg.entity_id as number;
        this.gameMode = msg.game_mode as number;
        this.emit('login', { entityId: msg.entity_id, gameMode: msg.game_mode });
        break;
      case 'keepalive':
        this.emit('keepalive', msg.latency_ms as number);
        break;
      case 'death':
        this.emit('death');
        break;
      case 'block_update':
        this.emit('block_update', { x: msg.x, y: msg.y, z: msg.z, stateId: msg.state_id });
        break;
      case 'chunk_load':
        this.emit('chunk_load', { cx: msg.cx, cz: msg.cz });
        break;
      case 'chunk_unload':
        this.emit('chunk_unload', { cx: msg.cx, cz: msg.cz });
        break;
      case 'title':
        this.emit('title', msg.text as string);
        break;
      case 'action_bar':
        this.emit('action_bar', msg.text as string);
        break;
      case 'game_mode':
        this.gameMode = msg.game_mode as number;
        this.emit('game_mode', msg.game_mode);
        break;
      case 'time_update':
        this.emit('time_update', { worldAge: msg.world_age, timeOfDay: msg.time_of_day });
        break;
      case 'remove_entities':
        this.emit('remove_entities', msg.ids as number[]);
        break;
      case 'transfer':
        this.emit('transfer', { host: msg.host, port: msg.port });
        break;
      default:
        this.emit('unknown_event', msg);
    }
  }

  // ── Typed event overloads ───────────────────────────────────────────────
  on(event: 'connected',      listener: (info: { version: string; protocol: number }) => void): this;
  on(event: 'disconnected',   listener: (reason: string) => void): this;
  on(event: 'error',          listener: (err: Error) => void): this;
  on(event: 'chat',           listener: (data: { message: string; sender: string }) => void): this;
  on(event: 'system_chat',    listener: (data: { content: string; overlay: boolean }) => void): this;
  on(event: 'health',         listener: (data: { health: number; food: number; saturation: number }) => void): this;
  on(event: 'position',       listener: (pos: Position) => void): this;
  on(event: 'spawn',          listener: (pos: { x: number; y: number; z: number }) => void): this;
  on(event: 'login',          listener: (data: { entityId: number; gameMode: number }) => void): this;
  on(event: 'keepalive',      listener: (latencyMs: number) => void): this;
  on(event: 'death',          listener: () => void): this;
  on(event: 'block_update',   listener: (data: { x: number; y: number; z: number; stateId: number }) => void): this;
  on(event: 'chunk_load',     listener: (data: { cx: number; cz: number }) => void): this;
  on(event: 'chunk_unload',   listener: (data: { cx: number; cz: number }) => void): this;
  on(event: 'title',          listener: (text: string) => void): this;
  on(event: 'action_bar',     listener: (text: string) => void): this;
  on(event: 'game_mode',      listener: (mode: number) => void): this;
  on(event: 'time_update',    listener: (data: { worldAge: number; timeOfDay: number }) => void): this;
  on(event: 'remove_entities', listener: (ids: number[]) => void): this;
  on(event: 'transfer',       listener: (data: { host: string; port: number }) => void): this;
  on(event: string, listener: (...args: unknown[]) => void): this;
  on(event: string, listener: (...args: unknown[]) => void): this {
    return super.on(event, listener);
  }
}

export default McPyCoreClient;
