"""Wrap raw payload bytes into a frame and back (spec §8.3–8.5).

Order on encode: hash(original) -> compress -> frame.
Order on decode: parse frame -> decompress -> verify hash(original).
"""

from __future__ import annotations

import hashlib
import zlib

from .errors import IntegrityCheckFailed, UnsupportedFileType, UnsupportedMethod
from .frame import encode_frame
from .types import (
    Compression,
    Encryption,
    FrameFields,
    ParsedFrame,
    PayloadType,
    RecoveryClass,
)

_ALREADY_COMPRESSED_MIME = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "application/zip",
    "application/gzip",
    "application/x-7z-compressed",
}


def select_compression(mode: str, mime_type: str, raw: bytes) -> Compression:
    mode = (mode or "auto").lower()
    if mode == "none":
        return Compression.NONE
    if mode == "zlib":
        return Compression.ZLIB
    if mode == "zstd":
        raise UnsupportedFileType("zstd compression is not available in the MVP")
    if mode != "auto":
        raise UnsupportedFileType(f"unknown compression mode: {mode}")
    # auto
    if mime_type.lower() in _ALREADY_COMPRESSED_MIME:
        return Compression.NONE
    if not raw:
        return Compression.NONE
    trial = zlib.compress(raw, level=6)
    if len(trial) >= len(raw) * 0.95:  # high-entropy: compression not worth it
        return Compression.NONE
    return Compression.ZLIB


def _compress(comp: Compression, raw: bytes) -> bytes:
    if comp == Compression.NONE:
        return raw
    if comp == Compression.ZLIB:
        return zlib.compress(raw, level=6)
    raise UnsupportedFileType(f"compression {comp!r} not supported in MVP")


def _decompress(comp: Compression, data: bytes) -> bytes:
    if comp == Compression.NONE:
        return data
    if comp == Compression.ZLIB:
        try:
            return zlib.decompress(data)
        except zlib.error as exc:
            raise IntegrityCheckFailed("payload failed to decompress") from exc
    raise UnsupportedFileType(f"compression {comp!r} not supported in MVP")


def encode_payload(
    *,
    raw: bytes,
    payload_type: PayloadType,
    original_filename: str,
    mime_type: str,
    compression: str = "auto",
    encryption: Encryption = Encryption.NONE,
    recovery_class: RecoveryClass = RecoveryClass.EXACT,
) -> bytes:
    if encryption != Encryption.NONE:
        raise UnsupportedMethod("encryption is not implemented in the MVP")
    comp = select_compression(compression, mime_type, raw)
    sha256 = hashlib.sha256(raw).digest()
    payload_bytes = _compress(comp, raw)
    fields = FrameFields(
        payload_type=payload_type,
        compression=comp,
        encryption=encryption,
        recovery_class=recovery_class,
        original_filename=original_filename,
        mime_type=mime_type,
        sha256=sha256,
        payload_bytes=payload_bytes,
    )
    return encode_frame(fields)


def decode_payload(parsed: ParsedFrame) -> bytes:
    original = _decompress(parsed.compression, parsed.payload_bytes)
    if hashlib.sha256(original).digest() != parsed.sha256:
        raise IntegrityCheckFailed("payload checksum mismatch")
    return original
