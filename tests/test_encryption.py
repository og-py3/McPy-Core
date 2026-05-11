"""Tests for EncryptionManager."""
from __future__ import annotations

import os
import pytest

from mcpycore.crypto.encryption import EncryptionManager


def test_disabled_by_default():
    enc = EncryptionManager()
    assert not enc.enabled
    assert enc.shared_secret is None


def test_generate_shared_secret_length():
    enc = EncryptionManager()
    secret = enc.generate_shared_secret()
    assert len(secret) == 16


def test_generate_returns_bytes():
    enc = EncryptionManager()
    assert isinstance(enc.generate_shared_secret(), bytes)


def test_enable_switches_on():
    enc = EncryptionManager()
    secret = enc.generate_shared_secret()
    enc.enable(secret)
    assert enc.enabled


def test_enable_wrong_length_raises():
    enc = EncryptionManager()
    with pytest.raises(ValueError, match="16 bytes"):
        enc.enable(b"\x00" * 8)


def test_encrypt_decrypt_roundtrip():
    enc = EncryptionManager()
    secret = enc.generate_shared_secret()
    enc.enable(secret)

    plaintext = b"Hello, Minecraft!"
    ciphertext = enc.encrypt(plaintext)
    assert ciphertext != plaintext

    # Use a second instance with the same secret to decrypt
    dec = EncryptionManager()
    dec.enable(secret)
    recovered = dec.decrypt(ciphertext)
    assert recovered == plaintext


def test_no_op_when_disabled():
    enc = EncryptionManager()
    data = b"\x01\x02\x03"
    assert enc.encrypt(data) == data
    assert enc.decrypt(data) == data


def test_server_hash_format():
    enc = EncryptionManager()
    enc.generate_shared_secret()
    enc.enable(enc.shared_secret)
    h = enc.compute_server_hash("", b"", )
    # Hash is a hex string (may be negative/have leading -)
    assert isinstance(h, str)
    assert len(h) > 0


def test_server_hash_deterministic():
    enc1 = EncryptionManager()
    enc1.enable(b"\x00" * 16)
    enc2 = EncryptionManager()
    enc2.enable(b"\x00" * 16)
    h1 = enc1.compute_server_hash("test", b"\x01\x02")
    h2 = enc2.compute_server_hash("test", b"\x01\x02")
    assert h1 == h2


def test_encrypt_multiple_chunks():
    enc = EncryptionManager()
    secret = enc.generate_shared_secret()
    enc.enable(secret)

    dec = EncryptionManager()
    dec.enable(secret)

    for chunk in [b"chunk1", b"chunk2", b"chunk3"]:
        ct = enc.encrypt(chunk)
        pt = dec.decrypt(ct)
        assert pt == chunk


def test_repr():
    enc = EncryptionManager()
    assert "enabled=False" in repr(enc)
    enc.enable(b"\x00" * 16)
    assert "enabled=True" in repr(enc)


def test_shared_secret_stored():
    enc = EncryptionManager()
    secret = enc.generate_shared_secret()
    assert enc.shared_secret == secret
