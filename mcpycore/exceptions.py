"""Custom exceptions for Mcpycore."""


class McpycoreError(Exception):
    """Base exception for all Mcpycore errors."""


class McpycoreConnectionError(McpycoreError):
    """Raised when a connection to the server fails or is lost."""


# Backward-compatible alias.
# NOTE: importing ``ConnectionError`` from this module will shadow Python's
# built-in ``ConnectionError`` at the call site.  Prefer the fully-qualified
# ``mcpycore.exceptions.McpycoreConnectionError`` in new code.
ConnectionError = McpycoreConnectionError


class AuthenticationError(McpycoreError):
    """Raised when authentication with Mojang/Microsoft fails."""


class PacketError(McpycoreError):
    """Raised when a packet cannot be read or written correctly."""


class ProtocolError(McpycoreError):
    """Raised when the server sends unexpected protocol data."""


class LoginKickError(McpycoreError):
    """Raised when the server kicks the player during login."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Kicked during login: {reason}")


class PlayKickError(McpycoreError):
    """Raised when the server kicks the player during play."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Kicked: {reason}")
