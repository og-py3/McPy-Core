"""Tests for packet encode/decode round-trips."""

import uuid
import time
import pytest

from mcpycore.packets.packet import PacketBuffer
from mcpycore.packets.login.serverbound import (
    LoginStart, EncryptionResponse, LoginPluginResponse, LoginAcknowledged,
)
from mcpycore.packets.login.clientbound import (
    LoginDisconnect, EncryptionRequest, LoginSuccess, SetCompression,
)
from mcpycore.packets.status.serverbound import StatusRequest, PingRequest
from mcpycore.packets.status.clientbound import StatusResponse, PingResponse
from mcpycore.packets.play.serverbound import (
    ConfirmTeleportation, ChatMessageSB, ClientInformation,
    KeepAliveSB, MovePlayerPosRot, MovePlayerPos, SwingArm,
)
from mcpycore.packets.play.clientbound import (
    KeepAlive, PlayerPositionAndLook, SetHealth, SystemChatMessage, TimeUpdate,
    BlockUpdate, UnloadChunk, Disconnect,
)
from mcpycore.utils.datatypes import write_varint


def encode_then_decode(packet, decoder_cls):
    """Helper: encode → strip packet_id VarInt → decode → compare."""
    raw = packet.to_bytes()
    # raw = varint(total_len) + varint(packet_id) + payload
    # Strip outer length
    _, consumed_outer = _read_varint_at(raw, 0)
    # Strip packet_id
    _, consumed_id = _read_varint_at(raw, consumed_outer)
    payload = raw[consumed_outer + consumed_id:]
    buf = PacketBuffer(payload)
    return decoder_cls.decode(buf)


def _read_varint_at(data: bytes, offset: int):
    result = 0
    for i in range(5):
        byte = data[offset + i]
        result |= (byte & 0x7F) << (7 * i)
        if not (byte & 0x80):
            return result if result < 0x80000000 else result - 0x100000000, i + 1
    raise ValueError("VarInt too big")


# ── Login serverbound ─────────────────────────────────────────────────────────

def test_login_start_roundtrip():
    uid = uuid.uuid4()
    pkt = LoginStart(username="TestUser", player_uuid=uid)
    decoded = encode_then_decode(pkt, LoginStart)
    assert decoded.username == "TestUser"
    assert decoded.player_uuid == uid


def test_encryption_response_roundtrip():
    pkt = EncryptionResponse(
        shared_secret=b"\x01" * 16,
        verify_token=b"\x02" * 16,
    )
    decoded = encode_then_decode(pkt, EncryptionResponse)
    assert decoded.shared_secret == b"\x01" * 16
    assert decoded.verify_token == b"\x02" * 16


def test_login_plugin_response_no_data():
    pkt = LoginPluginResponse(message_id=42, data=None)
    decoded = encode_then_decode(pkt, LoginPluginResponse)
    assert decoded.message_id == 42
    assert decoded.data is None


def test_login_plugin_response_with_data():
    pkt = LoginPluginResponse(message_id=7, data=b"hello")
    decoded = encode_then_decode(pkt, LoginPluginResponse)
    assert decoded.message_id == 7
    assert decoded.data == b"hello"


def test_login_acknowledged():
    pkt = LoginAcknowledged()
    raw = pkt.to_bytes()
    assert len(raw) > 0  # just ensures it doesn't crash


# ── Login clientbound ─────────────────────────────────────────────────────────

def test_login_disconnect_decode():
    reason = '{"text":"Banned!"}'
    buf = PacketBuffer()
    buf.write_string(reason)
    buf.seek(0)
    pkt = LoginDisconnect.decode(buf)
    assert pkt.reason == reason


def test_set_compression_decode():
    buf = PacketBuffer()
    buf.write_varint(256)
    buf.seek(0)
    pkt = SetCompression.decode(buf)
    assert pkt.threshold == 256


def test_login_success_decode():
    uid = uuid.uuid4()
    buf = PacketBuffer()
    buf.write_uuid(uid)
    buf.write_string("CoolPlayer")
    buf.write_varint(0)    # no properties
    buf.write_bool(False)  # strict_error_handling
    buf.seek(0)
    pkt = LoginSuccess.decode(buf)
    assert pkt.player_uuid == uid
    assert pkt.username == "CoolPlayer"
    assert pkt.properties == []


# ── Status ────────────────────────────────────────────────────────────────────

def test_ping_request_roundtrip():
    pkt = PingRequest(payload=1234567890)
    decoded = encode_then_decode(pkt, PingRequest)
    assert decoded.payload == 1234567890


def test_ping_response_decode():
    buf = PacketBuffer()
    buf.write_long(999)
    buf.seek(0)
    pkt = PingResponse.decode(buf)
    assert pkt.payload == 999


def test_status_request():
    pkt = StatusRequest()
    raw = pkt.to_bytes()
    assert len(raw) > 0


# ── Play serverbound ──────────────────────────────────────────────────────────

def test_confirm_teleportation_roundtrip():
    pkt = ConfirmTeleportation(teleport_id=99)
    decoded = encode_then_decode(pkt, ConfirmTeleportation)
    assert decoded.teleport_id == 99


def test_keep_alive_sb_roundtrip():
    pkt = KeepAliveSB(keep_alive_id=-123456789)
    decoded = encode_then_decode(pkt, KeepAliveSB)
    assert decoded.keep_alive_id == -123456789


def test_move_player_pos_rot_roundtrip():
    pkt = MovePlayerPosRot(x=1.5, y=64.0, z=-200.75, yaw=90.0, pitch=-10.0, on_ground=True)
    decoded = encode_then_decode(pkt, MovePlayerPosRot)
    assert decoded.x == pytest.approx(1.5)
    assert decoded.y == pytest.approx(64.0)
    assert decoded.z == pytest.approx(-200.75)
    assert decoded.on_ground is True


def test_client_information_roundtrip():
    pkt = ClientInformation(
        locale="de_de",
        view_distance=12,
        chat_mode=0,
        chat_colors=True,
        displayed_skin_parts=0x7F,
        main_hand=1,
        enable_text_filtering=False,
        allow_listing=True,
    )
    decoded = encode_then_decode(pkt, ClientInformation)
    assert decoded.locale == "de_de"
    assert decoded.view_distance == 12
    assert decoded.main_hand == 1


def test_swing_arm_roundtrip():
    pkt = SwingArm(hand=1)
    decoded = encode_then_decode(pkt, SwingArm)
    assert decoded.hand == 1


# ── Play clientbound ──────────────────────────────────────────────────────────

def test_keep_alive_decode():
    buf = PacketBuffer()
    buf.write_long(12345678)
    buf.seek(0)
    pkt = KeepAlive.decode(buf)
    assert pkt.keep_alive_id == 12345678


def test_set_health_decode():
    buf = PacketBuffer()
    buf.write_float(16.0)
    buf.write_varint(18)
    buf.write_float(4.5)
    buf.seek(0)
    pkt = SetHealth.decode(buf)
    assert pkt.health == pytest.approx(16.0)
    assert pkt.food == 18
    assert pkt.food_saturation == pytest.approx(4.5)


def test_time_update_decode():
    buf = PacketBuffer()
    buf.write_long(100_000)
    buf.write_long(6000)
    buf.seek(0)
    pkt = TimeUpdate.decode(buf)
    assert pkt.world_age == 100_000
    assert pkt.time_of_day == 6000


def test_system_chat_decode():
    buf = PacketBuffer()
    buf.write_string('{"text":"Welcome!"}')
    buf.write_bool(False)
    buf.seek(0)
    pkt = SystemChatMessage.decode(buf)
    assert "Welcome" in pkt.content
    assert pkt.overlay is False


def test_unload_chunk_decode():
    buf = PacketBuffer()
    buf.write_int(-5)   # chunk_z
    buf.write_int(10)   # chunk_x
    buf.seek(0)
    pkt = UnloadChunk.decode(buf)
    assert pkt.chunk_z == -5
    assert pkt.chunk_x == 10
