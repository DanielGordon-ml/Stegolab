import struct

import pytest

from stegolab.core import errors, frame
from stegolab.core import types as t


def _fields(payload=b"the secret payload", filename="secret.txt", mime="text/plain"):
    return t.FrameFields(
        payload_type=t.PayloadType.TEXT,
        compression=t.Compression.ZLIB,
        encryption=t.Encryption.NONE,
        recovery_class=t.RecoveryClass.EXACT,
        original_filename=filename,
        mime_type=mime,
        sha256=b"\xab" * 32,
        payload_bytes=payload,
    )


def test_round_trip_preserves_all_fields():
    data = frame.encode_frame(_fields())
    parsed = frame.parse_frame(data)
    assert parsed.version == 1
    assert parsed.payload_type == t.PayloadType.TEXT
    assert parsed.compression == t.Compression.ZLIB
    assert parsed.encryption == t.Encryption.NONE
    assert parsed.recovery_class == t.RecoveryClass.EXACT
    assert parsed.original_filename == "secret.txt"
    assert parsed.mime_type == "text/plain"
    assert parsed.sha256 == b"\xab" * 32
    assert parsed.payload_len == len(b"the secret payload")
    assert parsed.payload_bytes == b"the secret payload"


def test_layout_starts_with_magic_and_version():
    data = frame.encode_frame(_fields())
    assert data[0:8] == b"STEGOLAB"
    assert data[8] == 1


def test_unicode_filename_round_trips():
    parsed = frame.parse_frame(frame.encode_frame(_fields(filename="résumé.txt")))
    assert parsed.original_filename == "résumé.txt"


def test_staged_length_helpers():
    data = frame.encode_frame(_fields())
    header_len = frame.header_len_from_prefix(data[:t.FIXED_PREFIX_LEN])
    header = data[t.FIXED_PREFIX_LEN:t.FIXED_PREFIX_LEN + header_len]
    payload_len = frame.payload_len_from_header(header)
    assert payload_len == len(b"the secret payload")
    assert frame.frame_total_len(header_len, payload_len) == len(data)


def test_bad_magic_raises_no_payload_found():
    data = bytearray(frame.encode_frame(_fields()))
    data[0:8] = b"XXXXXXXX"
    with pytest.raises(errors.NoPayloadFound):
        frame.parse_frame(bytes(data))


def test_unsupported_version_raises_corrupted():
    data = bytearray(frame.encode_frame(_fields()))
    data[8] = 99
    with pytest.raises(errors.CorruptedPayload):
        frame.parse_frame(bytes(data))


def test_truncated_header_raises_corrupted():
    data = frame.encode_frame(_fields())
    with pytest.raises(errors.CorruptedPayload):
        frame.parse_frame(data[:t.FIXED_PREFIX_LEN + 5])


def test_truncated_payload_raises_corrupted():
    data = frame.encode_frame(_fields())
    with pytest.raises(errors.CorruptedPayload):
        frame.parse_frame(data[:-3])


def test_too_short_for_prefix_raises_corrupted():
    with pytest.raises(errors.CorruptedPayload):
        frame.parse_frame(b"STEG")


def test_extra_trailing_bytes_are_ignored():
    # Bit-stream extractors may hand over more bytes than the frame needs.
    data = frame.encode_frame(_fields()) + b"\x00\x00\x99"
    parsed = frame.parse_frame(data)
    assert parsed.payload_bytes == b"the secret payload"
