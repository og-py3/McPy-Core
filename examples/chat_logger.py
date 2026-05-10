"""
Chat Logger — logs all chat and system messages to stdout and a file.

Usage:
    python examples/chat_logger.py <host> [port] [username] [logfile]
    python examples/chat_logger.py play.example.com 25565 Logger chat.log
"""

import sys
import datetime

from mcpycore import MinecraftClient, OfflineAuth
from mcpycore.events import (
    EVT_CONNECTED, EVT_CHAT, EVT_SYSTEM, EVT_ACTION_BAR,
    EVT_TITLE, EVT_SUBTITLE, EVT_DISCONNECT,
)


def main():
    host     = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port     = int(sys.argv[2]) if len(sys.argv) > 2 else 25565
    username = sys.argv[3] if len(sys.argv) > 3 else "ChatLogger"
    logfile  = sys.argv[4] if len(sys.argv) > 4 else None

    log_fh = open(logfile, "a", encoding="utf-8") if logfile else None

    def log(tag: str, text: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{tag}] {text}"
        print(line)
        if log_fh:
            log_fh.write(line + "\n")
            log_fh.flush()

    client = MinecraftClient(host, port=port, auth=OfflineAuth(username))

    @client.on(EVT_CONNECTED)
    def on_connected(c):
        log("INFO", f"Connected as {c.profile.username} | {c.version_name}")

    @client.on(EVT_CHAT)
    def on_chat(pkt):
        msg = getattr(pkt, "message", str(pkt))
        sender = getattr(pkt, "sender", "?")
        log("CHAT", f"{sender}: {msg}")

    @client.on(EVT_SYSTEM)
    def on_system(pkt):
        content = getattr(pkt, "content", str(pkt))
        log("SYS", content)

    @client.on(EVT_ACTION_BAR)
    def on_ab(pkt):
        log("ACTIONBAR", pkt.text)

    @client.on(EVT_TITLE)
    def on_title(pkt):
        log("TITLE", pkt.text)

    @client.on(EVT_SUBTITLE)
    def on_sub(pkt):
        log("SUBTITLE", pkt.text)

    @client.on(EVT_DISCONNECT)
    def on_dc(reason):
        log("DC", reason)
        if log_fh:
            log_fh.close()

    log("INFO", f"Connecting to {host}:{port} as {username}…")
    try:
        client.connect()
        client.run()
    except KeyboardInterrupt:
        log("INFO", "Stopped by user.")
        if log_fh:
            log_fh.close()


if __name__ == "__main__":
    main()
