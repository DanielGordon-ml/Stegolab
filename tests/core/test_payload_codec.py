import hashlib

import pytest

from stegolab.core import errors, frame, payload_codec
from stegolab.core import types as t


def test_encode_decode_round_trip_text():
    raw = b"attack at dawn" * 50
    framed = payload_codec.encode_payload(
        raw=raw, payload_type=t.PayloadType.TEXT,
        original_filename="orders.txt", mime_type="text/plain", compression="zlib",
    )
    parsed = frame.parse_frame(framed)
    assert parsed.compression == t.Compression.ZLIB
    assert payload_codec.decode_payload(parsed) == raw


def test_sha256_is_over_original_bytes():
    raw = b"hello world"
    framed = payload_codec.encode_payload(
        raw=raw, payload_type=t.PayloadType.TEXT,
        original_filename="h.txt", mime_type="text/plain", compression="zlib",
    )
    parsed = frame.parse_frame(framed)
    assert parsed.sha256 == hashlib.sha256(raw).digest()


def test_corrupted_payload_fails_integrity():
    raw = b"important bytes"
    framed = bytearray(payload_codec.encode_payload(
        raw=raw, payload_type=t.PayloadType.BYTES,
        original_filename="x.bin", mime_type="application/octet-stream", compression="none",
    ))
    framed[-1] ^= 0xFF  # flip a payload byte
    parsed = frame.parse_frame(bytes(framed))
    with pytest.raises(errors.IntegrityCheckFailed):
        payload_codec.decode_payload(parsed)


def test_select_compression_auto_skips_already_compressed():
    assert payload_codec.select_compression("auto", "image/png", b"\x89PNG....") == t.Compression.NONE


def test_select_compression_auto_compresses_text():
    assert payload_codec.select_compression("auto", "text/plain", b"aaaa" * 100) == t.Compression.ZLIB


def test_select_compression_none_and_zlib_explicit():
    assert payload_codec.select_compression("none", "text/plain", b"x") == t.Compression.NONE
    assert payload_codec.select_compression("zlib", "text/plain", b"x") == t.Compression.ZLIB


def test_zstd_not_supported_in_mvp():
    with pytest.raises(errors.UnsupportedFileType):
        payload_codec.select_compression("zstd", "text/plain", b"x")


def test_none_compression_round_trip():
    raw = b"\x00\x01\x02\x03payload"
    framed = payload_codec.encode_payload(
        raw=raw, payload_type=t.PayloadType.BYTES,
        original_filename="d.bin", mime_type="application/octet-stream", compression="none",
    )
    parsed = frame.parse_frame(framed)
    assert parsed.compression == t.Compression.NONE
    assert payload_codec.decode_payload(parsed) == raw
