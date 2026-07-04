# McPy-Core SDKs

Official language SDKs for [McPy-Core](https://github.com/og-py3/McPy-Core).

All SDKs connect to the **McPy-Core bridge server** (Python process) via
WebSocket. The bridge handles the full Minecraft protocol internally so your
bot code stays clean and concise in any language.

## Architecture

```
Your bot (any language)
       │  WebSocket (JSON)
       ▼
McPy-Core Bridge  ←─── python -m mcpycore.bridge --port 25580
       │  Minecraft protocol (TCP, binary, encrypted)
       ▼
Minecraft Server
```

## Start the Bridge

```bash
pip install mcpy-core
python -m mcpycore.bridge --port 25580
```

The bridge supports multiple concurrent bot sessions — each WebSocket
connection is an independent bot.

---

## SDKs

| Language | Directory | Package Registry | Install |
|---|---|---|---|
| Python | *(root package)* | [PyPI](https://pypi.org/project/mcpy-core/) | `pip install mcpy-core` |
| JavaScript / TypeScript | `sdks/javascript/` | [npm](https://www.npmjs.com/package/mcpy-core-js) | `npm install mcpy-core-js` |
| Java | `sdks/java/` | [Maven Central](https://search.maven.org/) | see below |
| Go | `sdks/go/` | [pkg.go.dev](https://pkg.go.dev/) | `go get github.com/og-py3/McPy-Core/sdks/go` |
| Rust | `sdks/rust/` | [crates.io](https://crates.io/crates/mcpy-core) | `cargo add mcpy-core` |
| C# / .NET | `sdks/csharp/` | [NuGet](https://www.nuget.org/packages/McPyCore) | `dotnet add package McPyCore` |

---

## JavaScript / TypeScript

```bash
npm install mcpy-core-js
```

```typescript
import { McPyCoreClient } from 'mcpy-core-js';

const bot = new McPyCoreClient({ bridgeUrl: 'ws://localhost:25580' });
bot.on('connected', () => console.log('Online!'));
bot.on('chat', ({ message }) => console.log(message));
await bot.connect({ host: 'play.example.com', username: 'JSBot', protocol: 775 });
```

---

## Java (Maven)

```xml
<dependency>
  <groupId>io.mcpycore</groupId>
  <artifactId>mcpy-core-java</artifactId>
  <version>2.0.0</version>
</dependency>
```

```java
McPyCore bot = new McPyCore();
bot.on("chat", e -> System.out.println(e.get("message").getAsString()));
bot.connect(ConnectOptions.builder().host("play.example.com").username("JavaBot").build());
```

---

## Go

```bash
go get github.com/og-py3/McPy-Core/sdks/go@v2.0.0
```

```go
client := mcpycore.New("ws://localhost:25580")
client.On("chat", func(e mcpycore.Event) { fmt.Println(e["message"]) })
client.Connect(mcpycore.ConnectOptions{Host: "play.example.com", Username: "GoBot"})
```

---

## Rust

```bash
cargo add mcpy-core
```

```rust
let mut client = Client::default_bridge();
client.on("chat", |e| println!("{}", e["message"]));
client.connect(ConnectOptions { host: "play.example.com".into(), ..Default::default() }).await?;
```

---

## C# / .NET

```bash
dotnet add package McPyCore
```

```csharp
await using var bot = new McPyCoreClient("ws://localhost:25580");
bot.OnChat += e => Console.WriteLine($"[{e.Sender}] {e.Message}");
await bot.ConnectAsync(new() { Host = "play.example.com", Username = "CSharpBot" });
await Task.Delay(-1);
```

---

## Supported Minecraft Versions

All SDKs support every Minecraft Java Edition release from **1.7.2** (protocol 4)
through **1.21.11** (protocol 775). Set the `protocol` field to match your server:

| Version | Protocol |
|---|---|
| 1.7.2 | 4 |
| 1.8 | 47 |
| 1.12.2 | 340 |
| 1.16.5 | 754 |
| 1.18.2 | 758 |
| 1.19.4 | 762 |
| 1.20.4 | 765 |
| 1.21.1 | 767 |
| 1.21.11 | 775 |

---

## Bridge Protocol Reference

See [`mcpycore/bridge/__init__.py`](../mcpycore/bridge/__init__.py) for the full
JSON message specification.
