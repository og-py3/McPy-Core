"""Cryptography helpers used during online-mode login."""

from __future__ import annotations

import hashlib


def minecraft_server_hash(server_id: str, shared_secret: bytes, public_key: bytes) -> str:
    """
    Compute the Minecraft session server hash.

    This is a signed, big-endian SHA-1 digest formatted as a hex string
    (without leading zeros, with a '-' prefix if negative).
    """
    sha1 = hashlib.sha1()
    sha1.update(server_id.encode("ascii"))
    sha1.update(shared_secret)
    sha1.update(public_key)
    digest = int.from_bytes(sha1.digest(), "big", signed=True)
    return format(digest, "x")
