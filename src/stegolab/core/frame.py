"""Binary frame wire format (spec §8.3). All integers big-endian, strings UTF-8.

Layout:
  Fixed prefix (11 bytes): magic(8) "STEGOLAB" | version(1) | header_len(2)
  Header block (header_len bytes):
    payload_type(1) compression(1) encryption(1) recovery_class(1)
    sha256(32) payload_len(4)
    filename_len(2) filename(...) mime_len(2) mime(...)
    [if encryption != 0] salt_len(1) salt(...) nonce_len(1) nonce(...)
  Payload: payload_bytes(payload_len)
"""

from __future__ import annotations

import struct

from .errors import CorruptedPayload, NoPayloadFound
from .types import (
    FIXED_PREFIX_LEN,
    FRAME_VERSION,
    MAGIC,
    Compression,
    Encryption,
    FrameFields,
    ParsedFrame,
    PayloadType,
    RecoveryClass,
)

# Offset of payload_len within the header block: 4 enum bytes + 32 sha256 bytes.
_PAYLOAD_LEN_OFFSET = 36


def encode_frame(fields: FrameFields) -> bytes:
    if len(fields.sha256) != 32:
        raise ValueError("sha256 must be exactly 32 bytes")
    fn = fields.original_filename.encode("utf-8")
    mt = fields.mime_type.encode("utf-8")
    if len(fn) > 0xFFFF or len(mt) > 0xFFFF:
        raise ValueError("filename/mime too long for a uint16 length prefix")

    header = bytearray()
    header += struct.pack(
        "!BBBB",
        int(fields.payload_type),
        int(fields.compression),
        int(fields.encryption),
        int(fields.recovery_class),
    )
    header += fields.sha256
    header += struct.pack("!I", len(fields.payload_bytes))
    header += struct.pack("!H", len(fn)) + fn
    header += struct.pack("!H", len(mt)) + mt
    if int(fields.encryption) != 0:
        salt = fields.salt or b""
        nonce = fields.nonce or b""
        if len(salt) > 0xFF or len(nonce) > 0xFF:
            raise ValueError("salt/nonce too long for a uint8 length prefix")
        header += struct.pack("!B", len(salt)) + salt
        header += struct.pack("!B", len(nonce)) + nonce

    if len(header) > 0xFFFF:
        raise ValueError("header too long for a uint16 header_len")

    out = bytearray()
    out += MAGIC
    out += struct.pack("!B", FRAME_VERSION)
    out += struct.pack("!H", len(header))
    out += header
    out += fields.payload_bytes
    return bytes(out)


def header_len_from_prefix(prefix: bytes) -> int:
    if len(prefix) < FIXED_PREFIX_LEN:
        raise CorruptedPayload("frame prefix too short")
    if prefix[0:8] != MAGIC:
        raise NoPayloadFound("no StegoLab frame magic")
    return struct.unpack("!H", prefix[9:11])[0]


def payload_len_from_header(header: bytes) -> int:
    if len(header) < _PAYLOAD_LEN_OFFSET + 4:
        raise CorruptedPayload("header too short for payload_len")
    return struct.unpack("!I", header[_PAYLOAD_LEN_OFFSET:_PAYLOAD_LEN_OFFSET + 4])[0]


def frame_total_len(header_len: int, payload_len: int) -> int:
    return FIXED_PREFIX_LEN + header_len + payload_len


class _Cursor:
    """Bounded reader over the header block; any over-read fails closed."""

    def __init__(self, buf: bytes):
        self.buf = buf
        self.pos = 0

    def take(self, n: int) -> bytes:
        end = self.pos + n
        if end > len(self.buf):
            raise CorruptedPayload("frame header truncated")
        chunk = self.buf[self.pos:end]
        self.pos = end
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("!H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("!I", self.take(4))[0]


def parse_frame(data: bytes) -> ParsedFrame:
    header_len = header_len_from_prefix(data[:FIXED_PREFIX_LEN])  # magic + length checks
    version = data[8]
    if version != FRAME_VERSION:
        raise CorruptedPayload(f"unsupported frame version: {version}")

    header_start = FIXED_PREFIX_LEN
    header_end = header_start + header_len
    if len(data) < header_end:
        raise CorruptedPayload("frame header truncated")
    header = data[header_start:header_end]

    c = _Cursor(header)
    try:
        payload_type = PayloadType(c.u8())
        compression = Compression(c.u8())
        encryption = Encryption(c.u8())
        recovery_class = RecoveryClass(c.u8())
    except ValueError as exc:  # unknown enum value
        raise CorruptedPayload("invalid enum in frame header") from exc
    sha256 = c.take(32)
    payload_len = c.u32()
    filename = c.take(c.u16()).decode("utf-8", errors="strict")
    mime_type = c.take(c.u16()).decode("utf-8", errors="strict")
    salt = nonce = None
    if int(encryption) != 0:
        salt = c.take(c.u8())
        nonce = c.take(c.u8())

    payload_start = header_end
    payload_end = payload_start + payload_len
    if len(data) < payload_end:
        raise CorruptedPayload("frame payload truncated")
    payload_bytes = data[payload_start:payload_end]

    return ParsedFrame(
        version=version,
        payload_type=payload_type,
        compression=compression,
        encryption=encryption,
        recovery_class=recovery_class,
        original_filename=filename,
        mime_type=mime_type,
        sha256=sha256,
        payload_len=payload_len,
        payload_bytes=payload_bytes,
        salt=salt,
        nonce=nonce,
    )
