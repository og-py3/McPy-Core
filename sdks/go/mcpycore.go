// Package mcpycore provides the official Go SDK for McPy-Core.
//
// It connects to a running McPy-Core bridge server (Python) and exposes a
// clean, event-driven API for driving Minecraft Java Edition bots from Go.
//
// Prerequisites: start the Python bridge first:
//
//	pip install mcpy-core
//	python -m mcpycore.bridge --port 25580
//
// Quick start:
//
//	client := mcpycore.New("ws://localhost:25580")
//	client.On("connected", func(e mcpycore.Event) {
//	    fmt.Println("Connected!", e["version"])
//	})
//	client.On("chat", func(e mcpycore.Event) {
//	    fmt.Printf("[%s] %s\n", e["sender"], e["message"])
//	    if e["message"] == "ping" {
//	        client.Chat("pong!")
//	    }
//	})
//	if err := client.Connect(mcpycore.ConnectOptions{
//	    Host:     "play.example.com",
//	    Username: "GoBot",
//	    Protocol: 775,
//	    Humanize: true,
//	}); err != nil {
//	    log.Fatal(err)
//	}
//	select {} // block forever
package mcpycore

import (
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// Event is a map of string → interface{} representing a JSON event message.
type Event map[string]interface{}

// EventHandler is a callback for a bridge event.
type EventHandler func(Event)

// ConnectOptions configures the Minecraft server connection.
type ConnectOptions struct {
	// Minecraft server hostname or IP.
	Host string
	// Minecraft server port (default: 25565).
	Port int
	// Player username.
	Username string
	// Microsoft access token (empty = offline mode).
	AccessToken string
	// Minecraft protocol version integer (default: 775 = 1.21.11).
	Protocol int
	// Enable humanized anti-bot timing.
	Humanize bool
}

func (o *ConnectOptions) defaults() {
	if o.Port == 0     { o.Port = 25565 }
	if o.Username == "" { o.Username = "GoBot" }
	if o.Protocol == 0  { o.Protocol = 775 }
}

// Client connects to the McPy-Core bridge and drives a Minecraft bot.
type Client struct {
	bridgeURL string
	conn      *websocket.Conn
	mu        sync.RWMutex
	listeners map[string][]EventHandler

	// Player state (updated from events, safe to read between event callbacks).
	X, Y, Z, Yaw, Pitch float64
	Health               float32
	Food                 int
	GameMode             int
	EntityID             int
}

// New creates a new Client connected to the bridge at bridgeURL.
func New(bridgeURL string) *Client {
	return &Client{
		bridgeURL: bridgeURL,
		listeners: make(map[string][]EventHandler),
	}
}

// NewDefault creates a Client that connects to ws://localhost:25580.
func NewDefault() *Client { return New("ws://localhost:25580") }

// On registers an event handler.
//
// Event names: connected, disconnected, error, chat, system_chat, health,
// position, spawn, login, keepalive, death, block_update, chunk_load,
// chunk_unload, title, action_bar, game_mode, time_update,
// remove_entities, transfer.
func (c *Client) On(event string, handler EventHandler) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.listeners[event] = append(c.listeners[event], handler)
}

// OpenBridge opens the WebSocket connection to the bridge server.
func (c *Client) OpenBridge() error {
	u, err := url.Parse(c.bridgeURL)
	if err != nil {
		return fmt.Errorf("invalid bridge URL: %w", err)
	}
	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		return fmt.Errorf("bridge connect failed: %w", err)
	}
	c.conn = conn
	go c.readLoop()
	return nil
}

// Connect connects to a Minecraft server. Opens the bridge if not already open.
func (c *Client) Connect(opts ConnectOptions) error {
	opts.defaults()
	if c.conn == nil {
		if err := c.OpenBridge(); err != nil {
			return err
		}
	}
	msg := map[string]interface{}{
		"action":       "connect",
		"host":         opts.Host,
		"port":         opts.Port,
		"username":     opts.Username,
		"protocol":     opts.Protocol,
		"access_token": opts.AccessToken,
		"humanize":     opts.Humanize,
	}
	return c.send(msg)
}

// Disconnect disconnects from the Minecraft server.
func (c *Client) Disconnect() error { return c.send(map[string]interface{}{"action": "disconnect"}) }

// Chat sends a chat message or slash command.
func (c *Client) Chat(message string) error {
	return c.send(map[string]interface{}{"action": "chat", "message": message})
}

// Move sends a position + rotation update.
func (c *Client) Move(x, y, z, yaw, pitch float64) error {
	c.X, c.Y, c.Z, c.Yaw, c.Pitch = x, y, z, yaw, pitch
	return c.send(map[string]interface{}{
		"action": "move",
		"x": x, "y": y, "z": z, "yaw": yaw, "pitch": pitch,
	})
}

// Look changes look direction without moving.
func (c *Client) Look(yaw, pitch float64) error {
	c.Yaw, c.Pitch = yaw, pitch
	return c.send(map[string]interface{}{"action": "look", "yaw": yaw, "pitch": pitch})
}

// SwingArm swings the given hand (0 = main, 1 = off hand).
func (c *Client) SwingArm(hand int) error {
	return c.send(map[string]interface{}{"action": "swing_arm", "hand": hand})
}

// SetHeldSlot switches the hotbar slot (0–8).
func (c *Client) SetHeldSlot(slot int) error {
	return c.send(map[string]interface{}{"action": "set_held_slot", "slot": slot})
}

// Respawn respawns after death.
func (c *Client) Respawn() error { return c.send(map[string]interface{}{"action": "respawn"}) }

// Close closes the bridge WebSocket.
func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

// send serialises msg as JSON and writes it to the bridge WebSocket.
func (c *Client) send(msg interface{}) error {
	if c.conn == nil {
		return fmt.Errorf("bridge not connected — call OpenBridge() or Connect() first")
	}
	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	return c.conn.WriteMessage(websocket.TextMessage, data)
}

// readLoop reads messages from the bridge and dispatches events.
func (c *Client) readLoop() {
	defer func() {
		if c.conn != nil {
			_ = c.conn.Close()
		}
	}()
	for {
		_, data, err := c.conn.ReadMessage()
		if err != nil {
			log.Printf("mcpycore: bridge read error: %v", err)
			return
		}
		var ev Event
		if err := json.Unmarshal(data, &ev); err != nil {
			continue
		}
		c.updateState(ev)
		c.dispatch(ev)
	}
}

func (c *Client) updateState(ev Event) {
	name, _ := ev["event"].(string)
	switch name {
	case "position":
		c.X, _   = ev["x"].(float64)
		c.Y, _   = ev["y"].(float64)
		c.Z, _   = ev["z"].(float64)
		c.Yaw, _ = ev["yaw"].(float64)
		c.Pitch, _ = ev["pitch"].(float64)
	case "health":
		if h, ok := ev["health"].(float64); ok { c.Health = float32(h) }
		if f, ok := ev["food"].(float64);   ok { c.Food   = int(f) }
	case "login":
		if eid, ok := ev["entity_id"].(float64); ok { c.EntityID = int(eid) }
		if gm,  ok := ev["game_mode"].(float64);  ok { c.GameMode = int(gm) }
	case "game_mode":
		if gm, ok := ev["game_mode"].(float64); ok { c.GameMode = int(gm) }
	}
}

func (c *Client) dispatch(ev Event) {
	name, _ := ev["event"].(string)
	c.mu.RLock()
	handlers := append([]EventHandler(nil), c.listeners[name]...)
	c.mu.RUnlock()
	for _, h := range handlers {
		go func(fn EventHandler) {
			defer func() {
				if r := recover(); r != nil {
					log.Printf("mcpycore: panic in %q handler: %v", name, r)
				}
			}()
			fn(ev)
		}(h)
	}
}

// WaitFor blocks until an event matching pred is received or timeout elapses.
// Returns the matched event and true, or nil and false on timeout.
func (c *Client) WaitFor(event string, pred func(Event) bool, timeout time.Duration) (Event, bool) {
	ch := make(chan Event, 1)
	id := fmt.Sprintf("__waitfor_%d", time.Now().UnixNano())
	c.mu.Lock()
	c.listeners[event] = append(c.listeners[event], func(e Event) {
		if pred == nil || pred(e) {
			select {
			case ch <- e:
			default:
			}
		}
	})
	_ = id
	c.mu.Unlock()
	select {
	case ev := <-ch:
		return ev, true
	case <-time.After(timeout):
		return nil, false
	}
}
