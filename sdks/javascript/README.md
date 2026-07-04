# mcpy-core-js

Official JavaScript/TypeScript SDK for [McPy-Core](https://github.com/og-py3/McPy-Core) — drive Minecraft Java Edition bots from Node.js.

## Prerequisites

Start the Python bridge server first:

```bash
pip install mcpy-core
python -m mcpycore.bridge --port 25580
```

## Installation

```bash
npm install mcpy-core-js
```

## Quick Start (TypeScript)

```typescript
import { McPyCoreClient } from 'mcpy-core-js';

const client = new McPyCoreClient({ bridgeUrl: 'ws://localhost:25580' });

client.on('connected', (info) => {
  console.log(`Connected! Minecraft ${info.version} (protocol ${info.protocol})`);
});

client.on('chat', ({ message, sender }) => {
  console.log(`[${sender}] ${message}`);
  if (message === 'ping') client.chat('pong!');
});

client.on('spawn', ({ x, y, z }) => {
  console.log(`Spawned at ${x.toFixed(1)}, ${y.toFixed(1)}, ${z.toFixed(1)}`);
});

client.on('death', () => {
  console.log('Died — respawning...');
  client.respawn();
});

// Connect with humanized anti-bot bypass
await client.connect({
  host: 'play.example.com',
  username: 'JSBot',
  protocol: 775,           // 1.21.11 — match your server version
  humanize: {
    authme_enabled: true,
    authme_password: 'your_password',
  },
});
```

## Quick Start (CommonJS)

```javascript
const { McPyCoreClient } = require('mcpy-core-js');

const client = new McPyCoreClient({ bridgeUrl: 'ws://localhost:25580' });

client.on('connected', () => console.log('Online!'));

client.connect({ host: 'localhost', username: 'Bot' });
```

## API Reference

### `new McPyCoreClient(options?)`

| Option | Type | Default | Description |
|---|---|---|---|
| `bridgeUrl` | `string` | `'ws://localhost:25580'` | Bridge server URL |
| `autoReconnect` | `boolean` | `true` | Reconnect to bridge on drop |
| `reconnectDelay` | `number` | `2000` | Delay (ms) before bridge reconnect |

### `client.connect(opts)`

| Field | Type | Default | Description |
|---|---|---|---|
| `host` | `string` | — | Minecraft server host |
| `port` | `number` | `25565` | Minecraft server port |
| `username` | `string` | `'JSBot'` | Player username |
| `accessToken` | `string\|null` | `null` | Microsoft token (null = offline mode) |
| `protocol` | `number` | `775` | Protocol version (e.g. `47` for 1.8) |
| `humanize` | `boolean\|HumanizeOptions` | `false` | Anti-bot timing |

### Actions

```typescript
client.chat(message: string)
client.move(x, y, z, yaw?, pitch?)
client.look(yaw, pitch)
client.swingArm(hand?)     // 0 = main, 1 = off
client.setHeldSlot(slot)   // 0–8
client.respawn()
client.disconnect()
```

## Supported Protocol Versions

All versions from **1.7.2** (protocol 4) through **1.21.11** (protocol 775).
Set the `protocol` option to match your server.
