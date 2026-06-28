"""Enums, dataclasses, and constants for the frame format (spec §8)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

MAGIC = b"STEGOLAB"
FRAME_VERSION = 1
FIXED_PREFIX_LEN = 11          # magic(8) + version(1) + header_len(2)
FIXED_HEADER_FIELDS = 40       # payload_type1+comp1+enc1+rec1+sha256 32+payload_len4
DEFAULT_MIME = "application/octet-stream"


class PayloadType(IntEnum):
    TEXT = 0
    IMAGE = 1
    BYTES = 2


class Compression(IntEnum):
    NONE = 0
    ZLIB = 1
    ZSTD = 2  # Phase 3; reserved


class Encryption(IntEnum):
    NONE = 0
    AES_256_GCM = 1        # Phase 3; reserved
    CHACHA20_POLY1305 = 2  # Phase 3; reserved


class RecoveryClass(IntEnum):
    EXACT = 0
    NEAR_EXACT = 1


@dataclass
class FrameFields:
    payload_type: PayloadType
    compression: Compression
    encryption: Encryption
    recovery_class: RecoveryClass
    original_filename: str
    mime_type: str
    sha256: bytes
    payload_bytes: bytes
    salt: bytes | None = None
    nonce: bytes | None = None


@dataclass
class ParsedFrame:
    version: int
    payload_type: PayloadType
    compression: Compression
    encryption: Encryption
    recovery_class: RecoveryClass
    original_filename: str
    mime_type: str
    sha256: bytes
    payload_len: int
    payload_bytes: bytes
    salt: bytes | None = None
    nonce: bytes | None = None


@dataclass
class CapacityReport:
    total_bits: int
    total_bytes: int
    overhead_bytes: int
    usable_bytes: int
    is_estimate: bool
    assumptions: str
