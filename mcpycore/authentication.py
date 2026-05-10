"""
Authentication providers for Mcpycore.

Supported modes:
- OfflineAuth   — cracked/offline servers (no session check)
- MicrosoftAuth — online-mode servers via Microsoft OAuth flow

Microsoft auth flow (Device Code / OAuth):
    1. Request a device code from Microsoft
    2. User visits the URL and enters the code
    3. Poll for the access token
    4. Exchange for a Minecraft token via Xbox Live → XSTS → Minecraft
    5. Fetch the player profile (UUID + username)
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass

import requests

from mcpycore import exceptions as exc

logger = logging.getLogger(__name__)

# ── Minecraft session server ──────────────────────────────────────────────────

SESSION_SERVER = "https://sessionserver.mojang.com/session/minecraft"
MINECRAFT_SERVICES = "https://api.minecraftservices.com"

# Microsoft OAuth endpoints
MS_DEVICE_CODE_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
MS_TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
XBOX_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_AUTH_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MC_AUTH_URL = f"{MINECRAFT_SERVICES}/authentication/login_with_xbox"
MC_PROFILE_URL = f"{MINECRAFT_SERVICES}/minecraft/profile"

# Public client ID (the one Minecraft launcher uses — no secrets needed)
MS_CLIENT_ID = "00000000402b5328"


@dataclass
class PlayerProfile:
    """A logged-in player's identity."""
    username: str
    player_uuid: uuid.UUID
    access_token: str = ""

    def __str__(self) -> str:
        return f"{self.username} ({self.player_uuid})"


class OfflineAuth:
    """
    Offline / cracked authentication.

    Generates a deterministic UUID from the username using the same algorithm
    Minecraft offline servers use: MD5("OfflinePlayer:<name>") with UUID v3
    variant bits applied.  No network calls are made.
    Only works on offline-mode servers.
    """

    def __init__(self, username: str) -> None:
        self.username = username

    def get_profile(self) -> PlayerProfile:
        # Minecraft's offline UUID algorithm: MD5("OfflinePlayer:<name>"),
        # then set version=3 (nibble 6) and variant bits (byte 8).
        digest = hashlib.md5(f"OfflinePlayer:{self.username}".encode()).digest()
        raw = bytearray(digest)
        raw[6] = (raw[6] & 0x0F) | 0x30  # version 3
        raw[8] = (raw[8] & 0x3F) | 0x80  # RFC 4122 variant
        return PlayerProfile(
            username=self.username,
            player_uuid=uuid.UUID(bytes=bytes(raw)),
            access_token="",
        )

    def join_session(self, server_hash: str, profile: PlayerProfile) -> None:
        """No-op for offline mode."""

    def __repr__(self) -> str:
        return f"OfflineAuth(username={self.username!r})"


class MicrosoftAuth:
    """
    Microsoft / Xbox Live authentication for online-mode servers.

    Uses the Device Code Flow — no browser automation needed.
    The user must visit a short URL and enter a code (printed to stdout).

    Usage::

        auth = MicrosoftAuth(client_id="...")
        profile = auth.authenticate()          # prompts user, blocks until done
        client = MinecraftClient("server.com", auth=auth)
    """

    def __init__(self, client_id: str = MS_CLIENT_ID) -> None:
        self.client_id = client_id
        self._profile: PlayerProfile | None = None
        self._session = requests.Session()

    # ── Public API ────────────────────────────────────────────────────────────

    def authenticate(self) -> PlayerProfile:
        """
        Run the full auth flow interactively.
        Prints instructions for the user and blocks until login completes.
        Returns a PlayerProfile on success.
        """
        ms_token = self._device_code_flow()
        mc_token = self._exchange_for_minecraft_token(ms_token)
        profile = self._fetch_profile(mc_token)
        self._profile = profile
        return profile

    def get_profile(self) -> PlayerProfile:
        if self._profile is None:
            return self.authenticate()
        return self._profile

    def join_session(self, server_hash: str, profile: PlayerProfile) -> None:
        """
        POST to the Minecraft session server so the server can verify us
        during the online-mode handshake.
        """
        payload = {
            "accessToken": profile.access_token,
            "selectedProfile": str(profile.player_uuid).replace("-", ""),
            "serverId": server_hash,
        }
        resp = self._session.post(f"{SESSION_SERVER}/join", json=payload, timeout=10)
        if resp.status_code != 204:
            raise exc.AuthenticationError(
                f"Session join failed ({resp.status_code}): {resp.text}"
            )

    # ── Internal OAuth / token exchange steps ─────────────────────────────────

    def _device_code_flow(self) -> str:
        """Initiate the device code flow and poll until approved."""
        resp = self._session.post(
            MS_DEVICE_CODE_URL,
            data={
                "client_id": self.client_id,
                "scope": "XboxLive.signin offline_access",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # Use print here intentionally — this is a user-facing interactive prompt,
        # not a log message.  Suppressing it via the logging system would hide the
        # login URL from users who haven't configured a logging handler.
        print(
            f"\n[Mcpycore] To log in with Microsoft, visit:\n"
            f"  {data['verification_uri']}\n"
            f"  and enter the code: {data['user_code']}\n"
            f"  Waiting up to {data['expires_in']} seconds…\n"
        )
        logger.info(
            "Device code flow started: url=%s code=%s expires_in=%s",
            data["verification_uri"],
            data["user_code"],
            data["expires_in"],
        )

        interval = data.get("interval", 5)
        deadline = time.time() + data["expires_in"]
        device_code = data["device_code"]

        while time.time() < deadline:
            time.sleep(interval)
            token_resp = self._session.post(
                MS_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                },
                timeout=10,
            )
            token_data = token_resp.json()
            if "access_token" in token_data:
                logger.info("Microsoft device code flow succeeded.")
                return token_data["access_token"]
            error = token_data.get("error", "")
            if error == "authorization_pending":
                continue
            if error == "authorization_declined":
                raise exc.AuthenticationError("User declined the authorization request.")
            if error == "expired_token":
                raise exc.AuthenticationError("Device code expired. Please try again.")
            raise exc.AuthenticationError(f"Unexpected auth error: {token_data}")

        raise exc.AuthenticationError("Device code expired (timeout).")

    def _exchange_for_minecraft_token(self, ms_access_token: str) -> str:
        """Xbox Live → XSTS → Minecraft token exchange."""
        # Step 1: Xbox Live
        xbox_resp = self._session.post(
            XBOX_AUTH_URL,
            json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={ms_access_token}",
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        xbox_resp.raise_for_status()
        xbox_data = xbox_resp.json()
        xbox_token = xbox_data["Token"]
        user_hash = xbox_data["DisplayClaims"]["xui"][0]["uhs"]

        # Step 2: XSTS
        xsts_resp = self._session.post(
            XSTS_AUTH_URL,
            json={
                "Properties": {
                    "SandboxId": "RETAIL",
                    "UserTokens": [xbox_token],
                },
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        xsts_resp.raise_for_status()
        xsts_token = xsts_resp.json()["Token"]

        # Step 3: Minecraft
        mc_resp = self._session.post(
            MC_AUTH_URL,
            json={"identityToken": f"XBL3.0 x={user_hash};{xsts_token}"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        mc_resp.raise_for_status()
        return mc_resp.json()["access_token"]

    def _fetch_profile(self, mc_access_token: str) -> PlayerProfile:
        """Fetch the Minecraft player profile (UUID + username)."""
        resp = self._session.get(
            MC_PROFILE_URL,
            headers={"Authorization": f"Bearer {mc_access_token}"},
            timeout=10,
        )
        if resp.status_code == 404:
            raise exc.AuthenticationError(
                "This Microsoft account does not own Minecraft."
            )
        resp.raise_for_status()
        data = resp.json()
        raw_uuid = data["id"]
        formatted = (
            f"{raw_uuid[:8]}-{raw_uuid[8:12]}-{raw_uuid[12:16]}"
            f"-{raw_uuid[16:20]}-{raw_uuid[20:]}"
        )
        return PlayerProfile(
            username=data["name"],
            player_uuid=uuid.UUID(formatted),
            access_token=mc_access_token,
        )

    def __repr__(self) -> str:
        return f"MicrosoftAuth(client_id={self.client_id!r})"
