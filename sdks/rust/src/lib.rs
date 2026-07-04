//! # mcpy-core
//!
//! Official Rust SDK for [McPy-Core](https://github.com/og-py3/McPy-Core).
//!
//! Connects to a running McPy-Core bridge server and exposes an async,
//! event-driven API for driving Minecraft Java Edition bots from Rust.
//!
//! ## Prerequisites
//!
//! Start the Python bridge first:
//! ```bash
//! pip install mcpy-core
//! python -m mcpycore.bridge --port 25580
//! ```
//!
//! ## Quick Start
//!
//! ```rust,no_run
//! use mcpy_core::{Client, ConnectOptions};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let mut client = Client::new("ws://localhost:25580");
//!
//!     client.on("chat", |event| {
//!         if let (Some(msg), Some(sender)) = (
//!             event.get("message").and_then(|v| v.as_str()),
//!             event.get("sender").and_then(|v| v.as_str()),
//!         ) {
//!             println!("[{}] {}", sender, msg);
//!         }
//!     });
//!
//!     client.connect(ConnectOptions {
//!         host: "play.example.com".into(),
//!         username: "RustBot".into(),
//!         protocol: 775,
//!         humanize: true,
//!         ..Default::default()
//!     }).await?;
//!
//!     // Keep running
//!     tokio::signal::ctrl_c().await?;
//!     Ok(())
//! }
//! ```

use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Map, Value};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use url::Url;

// ── Public types ──────────────────────────────────────────────────────────────

/// A JSON event received from the bridge.
pub type Event = Map<String, Value>;

/// Callback for a bridge event.
pub type Handler = Box<dyn Fn(&Event) + Send + Sync + 'static>;

/// Options for connecting to a Minecraft server.
#[derive(Debug, Clone)]
pub struct ConnectOptions {
    /// Minecraft server hostname or IP.
    pub host: String,
    /// Minecraft server port (default: 25565).
    pub port: u16,
    /// Player username.
    pub username: String,
    /// Microsoft access token (`None` = offline mode).
    pub access_token: Option<String>,
    /// Minecraft protocol version (default: 775 = 1.21.11).
    pub protocol: u32,
    /// Enable humanized anti-bot timing.
    pub humanize: bool,
}

impl Default for ConnectOptions {
    fn default() -> Self {
        Self {
            host:         "localhost".into(),
            port:         25565,
            username:     "RustBot".into(),
            access_token: None,
            protocol:     775,
            humanize:     false,
        }
    }
}

/// Player state, updated automatically from events.
#[derive(Debug, Default, Clone)]
pub struct PlayerState {
    pub x: f64, pub y: f64, pub z: f64,
    pub yaw: f64, pub pitch: f64,
    pub health: f32, pub food: i32,
    pub game_mode: i32, pub entity_id: i32,
}

// ── Client ────────────────────────────────────────────────────────────────────

/// McPy-Core Rust client — drives a Minecraft bot through the bridge server.
pub struct Client {
    bridge_url: String,
    listeners:  Arc<Mutex<HashMap<String, Vec<Handler>>>>,
    sender:     Arc<Mutex<Option<mpsc::UnboundedSender<String>>>>,
    /// Player state updated from events (clone on each read for thread safety).
    pub state: Arc<Mutex<PlayerState>>,
}

impl Client {
    /// Create a new client that will connect to the given bridge URL.
    pub fn new(bridge_url: impl Into<String>) -> Self {
        Self {
            bridge_url: bridge_url.into(),
            listeners:  Arc::new(Mutex::new(HashMap::new())),
            sender:     Arc::new(Mutex::new(None)),
            state:      Arc::new(Mutex::new(PlayerState::default())),
        }
    }

    /// Create a client that connects to `ws://localhost:25580`.
    pub fn default_bridge() -> Self { Self::new("ws://localhost:25580") }

    // ── Event API ─────────────────────────────────────────────────────────

    /// Register an event handler.
    ///
    /// Common event names: `connected`, `disconnected`, `error`, `chat`,
    /// `system_chat`, `health`, `position`, `spawn`, `login`, `keepalive`,
    /// `death`, `block_update`, `chunk_load`, `chunk_unload`, `title`,
    /// `action_bar`, `game_mode`, `time_update`, `remove_entities`, `transfer`.
    pub fn on<F>(&mut self, event: impl Into<String>, handler: F)
    where F: Fn(&Event) + Send + Sync + 'static
    {
        let mut ls = self.listeners.lock().unwrap();
        ls.entry(event.into()).or_default().push(Box::new(handler));
    }

    // ── Bridge connection ─────────────────────────────────────────────────

    /// Open the WebSocket bridge and start the read loop. Non-blocking.
    pub async fn open_bridge(&self) -> Result<(), Box<dyn std::error::Error>> {
        let url = Url::parse(&self.bridge_url)?;
        let (ws_stream, _) = connect_async(url).await?;
        let (mut write, mut read) = ws_stream.split();

        let (tx, mut rx) = mpsc::unbounded_channel::<String>();
        *self.sender.lock().unwrap() = Some(tx);

        // Write task
        tokio::spawn(async move {
            while let Some(msg) = rx.recv().await {
                if write.send(Message::Text(msg)).await.is_err() { break; }
            }
        });

        // Read task
        let listeners = Arc::clone(&self.listeners);
        let state     = Arc::clone(&self.state);
        tokio::spawn(async move {
            while let Some(Ok(Message::Text(text))) = read.next().await {
                if let Ok(Value::Object(event)) = serde_json::from_str(&text) {
                    // Update player state
                    if let Some(Value::String(name)) = event.get("event") {
                        Self::update_state(&state, name, &event);
                        // Dispatch handlers
                        let ls = listeners.lock().unwrap();
                        if let Some(handlers) = ls.get(name.as_str()) {
                            for h in handlers { h(&event); }
                        }
                    }
                }
            }
        });

        Ok(())
    }

    fn update_state(state: &Arc<Mutex<PlayerState>>, event: &str, e: &Event) {
        let mut s = state.lock().unwrap();
        match event {
            "position" => {
                s.x   = e.get("x").and_then(|v| v.as_f64()).unwrap_or(s.x);
                s.y   = e.get("y").and_then(|v| v.as_f64()).unwrap_or(s.y);
                s.z   = e.get("z").and_then(|v| v.as_f64()).unwrap_or(s.z);
                s.yaw = e.get("yaw").and_then(|v| v.as_f64()).unwrap_or(s.yaw);
                s.pitch = e.get("pitch").and_then(|v| v.as_f64()).unwrap_or(s.pitch);
            }
            "health" => {
                s.health = e.get("health").and_then(|v| v.as_f64()).unwrap_or(s.health as f64) as f32;
                s.food   = e.get("food").and_then(|v| v.as_i64()).unwrap_or(s.food as i64) as i32;
            }
            "login" => {
                s.entity_id = e.get("entity_id").and_then(|v| v.as_i64()).unwrap_or(s.entity_id as i64) as i32;
                s.game_mode = e.get("game_mode").and_then(|v| v.as_i64()).unwrap_or(s.game_mode as i64) as i32;
            }
            "game_mode" => {
                s.game_mode = e.get("game_mode").and_then(|v| v.as_i64()).unwrap_or(s.game_mode as i64) as i32;
            }
            _ => {}
        }
    }

    // ── MC actions ────────────────────────────────────────────────────────

    /// Connect to a Minecraft server. Opens the bridge if needed.
    pub async fn connect(&self, opts: ConnectOptions) -> Result<(), Box<dyn std::error::Error>> {
        if self.sender.lock().unwrap().is_none() {
            self.open_bridge().await?;
        }
        self.send(json!({
            "action":       "connect",
            "host":         opts.host,
            "port":         opts.port,
            "username":     opts.username,
            "access_token": opts.access_token,
            "protocol":     opts.protocol,
            "humanize":     opts.humanize,
        }))
    }

    /// Disconnect from the Minecraft server.
    pub fn disconnect(&self) -> Result<(), Box<dyn std::error::Error>> {
        self.send(json!({"action": "disconnect"}))
    }

    /// Send a chat message or slash command.
    pub fn chat(&self, message: impl Into<String>) -> Result<(), Box<dyn std::error::Error>> {
        self.send(json!({"action": "chat", "message": message.into()}))
    }

    /// Move to a position.
    pub fn move_to(&self, x: f64, y: f64, z: f64, yaw: f64, pitch: f64)
        -> Result<(), Box<dyn std::error::Error>>
    {
        {
            let mut s = self.state.lock().unwrap();
            s.x = x; s.y = y; s.z = z; s.yaw = yaw; s.pitch = pitch;
        }
        self.send(json!({"action": "move", "x": x, "y": y, "z": z, "yaw": yaw, "pitch": pitch}))
    }

    /// Change look direction without moving.
    pub fn look(&self, yaw: f64, pitch: f64) -> Result<(), Box<dyn std::error::Error>> {
        { let mut s = self.state.lock().unwrap(); s.yaw = yaw; s.pitch = pitch; }
        self.send(json!({"action": "look", "yaw": yaw, "pitch": pitch}))
    }

    /// Swing hand (0 = main, 1 = off hand).
    pub fn swing_arm(&self, hand: u8) -> Result<(), Box<dyn std::error::Error>> {
        self.send(json!({"action": "swing_arm", "hand": hand}))
    }

    /// Switch hotbar slot (0–8).
    pub fn set_held_slot(&self, slot: u8) -> Result<(), Box<dyn std::error::Error>> {
        self.send(json!({"action": "set_held_slot", "slot": slot}))
    }

    /// Respawn after death.
    pub fn respawn(&self) -> Result<(), Box<dyn std::error::Error>> {
        self.send(json!({"action": "respawn"}))
    }

    // ── Internal ──────────────────────────────────────────────────────────

    fn send(&self, value: Value) -> Result<(), Box<dyn std::error::Error>> {
        let tx = self.sender.lock().unwrap();
        let tx = tx.as_ref().ok_or("Bridge not connected")?;
        tx.send(value.to_string())?;
        Ok(())
    }
}
