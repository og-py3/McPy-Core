//! Basic McPy-Core bot example.
//!
//! Prerequisites:
//!   pip install mcpy-core
//!   python -m mcpycore.bridge --port 25580
//!
//! Run:
//!   cargo run --example basic_bot

use mcpy_core::{Client, ConnectOptions};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();

    let mut client = Client::default_bridge();

    client.on("connected", |e| {
        println!("Connected! version={}", e.get("version").and_then(|v| v.as_str()).unwrap_or("?"));
    });

    client.on("disconnected", |e| {
        println!("Disconnected: {}", e.get("reason").and_then(|v| v.as_str()).unwrap_or("?"));
    });

    client.on("spawn", |e| {
        let x = e.get("x").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let y = e.get("y").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let z = e.get("z").and_then(|v| v.as_f64()).unwrap_or(0.0);
        println!("Spawned at ({:.1}, {:.1}, {:.1})", x, y, z);
    });

    client.on("chat", |e| {
        let msg    = e.get("message").and_then(|v| v.as_str()).unwrap_or("");
        let sender = e.get("sender").and_then(|v| v.as_str()).unwrap_or("?");
        println!("[{}] {}", sender, msg);
    });

    client.on("death", |_| println!("Died!"));

    client.connect(ConnectOptions {
        host:     "play.example.com".into(),
        username: "RustBot".into(),
        protocol: 775,
        humanize: true,
        ..Default::default()
    }).await?;

    tokio::signal::ctrl_c().await?;
    println!("Shutting down...");
    client.disconnect()?;
    Ok(())
}
