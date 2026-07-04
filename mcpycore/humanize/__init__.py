"""
mcpycore.humanize — anti-bot-detection layer for McPy-Core.

Makes a bot's join sequence and in-game behaviour indistinguishable
from a real player by injecting realistic timing jitter, natural look
angles, and human-paced responses throughout the protocol handshake.
"""

from mcpycore.humanize.humanizer import HumanizeConfig, Humanizer

__all__ = ["HumanizeConfig", "Humanizer"]
