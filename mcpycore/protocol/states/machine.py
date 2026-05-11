"""
Protocol State Machine.

Manages the client's current protocol state and validates transitions.

States (per wiki.vg):
  HANDSHAKING   → STATUS or LOGIN
  STATUS        → (closed after response)
  LOGIN         → CONFIGURATION or PLAY (older versions)
  CONFIGURATION → PLAY
  PLAY          → (closed on disconnect)
"""
from __future__ import annotations

from enum import Enum
from typing import Callable


class State(str, Enum):
    """Minecraft protocol states."""
    HANDSHAKING     = "handshaking"
    STATUS          = "status"
    LOGIN           = "login"
    CONFIGURATION   = "configuration"
    PLAY            = "play"

    def __str__(self) -> str:
        return self.value


# Valid state transitions: state → frozenset of allowed next states
_TRANSITIONS: dict[State, frozenset[State]] = {
    State.HANDSHAKING:   frozenset({State.STATUS, State.LOGIN}),
    State.STATUS:        frozenset({State.STATUS}),
    State.LOGIN:         frozenset({State.CONFIGURATION, State.PLAY}),
    State.CONFIGURATION: frozenset({State.PLAY}),
    State.PLAY:          frozenset(),          # terminal; closed by disconnect
}


class InvalidTransition(Exception):
    """Raised when an illegal state transition is attempted."""


class ProtocolStateMachine:
    """
    Tracks and validates the Minecraft protocol state for one connection.

    Parameters
    ----------
    on_transition:
        Optional async callback invoked on every state change.
        Signature: ``async def callback(old: State, new: State) -> None``
    """

    def __init__(
        self,
        on_transition: Callable[[State, State], None] | None = None,
    ) -> None:
        self._state = State.HANDSHAKING
        self._on_transition = on_transition
        self._history: list[State] = [State.HANDSHAKING]

    @property
    def current(self) -> State:
        return self._state

    def transition(self, new_state: State) -> None:
        """
        Move to *new_state*.

        Raises ``InvalidTransition`` if the move is not allowed.
        """
        allowed = _TRANSITIONS.get(self._state, frozenset())
        if new_state not in allowed:
            raise InvalidTransition(
                f"Cannot transition {self._state} → {new_state}. "
                f"Allowed: {', '.join(s.value for s in allowed) or 'none'}"
            )
        old = self._state
        self._state = new_state
        self._history.append(new_state)
        if self._on_transition:
            self._on_transition(old, new_state)

    def force(self, state: State) -> None:
        """Force-set the state without validation (use sparingly)."""
        old = self._state
        self._state = state
        self._history.append(state)
        if self._on_transition:
            self._on_transition(old, state)

    def is_in(self, *states: State) -> bool:
        return self._state in states

    @property
    def history(self) -> list[State]:
        return list(self._history)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, State):
            return self._state == other
        return NotImplemented

    def __repr__(self) -> str:
        return f"ProtocolStateMachine(state={self._state.value!r})"
