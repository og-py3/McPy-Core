"""
EncryptionManager — handles AES-128/CFB8 stream encryption.

Used during the login sequence after the server sends EncryptionRequest.
The shared secret is negotiated via RSA and then used for the symmetric cipher.
"""
from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.backends import default_backend


class EncryptionManager:
    """
    Manages AES-128-CFB8 encryption for one connection.

    Usage::

        enc = EncryptionManager()
        shared_secret = enc.generate_shared_secret()

        # After server confirms:
        enc.enable(shared_secret)

        encrypted_data = enc.encrypt(plaintext)
        plaintext_data = enc.decrypt(ciphertext)
    """

    def __init__(self) -> None:
        self._enabled = False
        self._encryptor = None
        self._decryptor = None
        self._shared_secret: bytes | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def shared_secret(self) -> bytes | None:
        return self._shared_secret

    def generate_shared_secret(self) -> bytes:
        """Generate a fresh 16-byte shared secret."""
        self._shared_secret = os.urandom(16)
        return self._shared_secret

    def enable(self, shared_secret: bytes) -> None:
        """Activate encryption using the given 16-byte shared secret."""
        if len(shared_secret) != 16:
            raise ValueError(f"Shared secret must be 16 bytes, got {len(shared_secret)}")
        self._shared_secret = shared_secret
        cipher_enc = Cipher(
            algorithms.AES(shared_secret),
            modes.CFB8(shared_secret),
            backend=default_backend(),
        )
        cipher_dec = Cipher(
            algorithms.AES(shared_secret),
            modes.CFB8(shared_secret),
            backend=default_backend(),
        )
        self._encryptor = cipher_enc.encryptor()
        self._decryptor = cipher_dec.decryptor()
        self._enabled = True

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt *data*. No-op if encryption is not enabled."""
        if not self._enabled or self._encryptor is None:
            return data
        return self._encryptor.update(data)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt *data*. No-op if encryption is not enabled."""
        if not self._enabled or self._decryptor is None:
            return data
        return self._decryptor.update(data)

    def encrypt_rsa(self, der_public_key: bytes, plaintext: bytes) -> bytes:
        """
        Encrypt *plaintext* with the server's RSA public key (PKCS#1 v1.5).

        Used for the EncryptionResponse to securely send the shared secret
        and verify token to the server.
        """
        pub_key = load_der_public_key(der_public_key, backend=default_backend())
        return pub_key.encrypt(plaintext, PKCS1v15())  # type: ignore[arg-type]

    def compute_server_hash(self, server_id: str, public_key: bytes) -> str:
        """
        Compute the server hash for session-server verification.

        Returns a hex string (may be negative, following Java's signed convention).
        """
        import hashlib
        sha1 = hashlib.sha1()
        sha1.update(server_id.encode("ascii"))
        sha1.update(self._shared_secret or b"")
        sha1.update(public_key)
        digest = int.from_bytes(sha1.digest(), "big", signed=True)
        return format(digest, "x")

    def __repr__(self) -> str:
        return f"EncryptionManager(enabled={self._enabled})"
