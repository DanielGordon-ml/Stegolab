from stegolab.core import types as t


def test_constants():
    assert t.MAGIC == b"STEGOLAB"
    assert len(t.MAGIC) == 8
    assert t.FRAME_VERSION == 1
    assert t.FIXED_PREFIX_LEN == 11
    assert t.FIXED_HEADER_FIELDS == 40
    assert t.DEFAULT_MIME == "application/octet-stream"


def test_enum_values():
    assert int(t.PayloadType.TEXT) == 0
    assert int(t.PayloadType.IMAGE) == 1
    assert int(t.PayloadType.BYTES) == 2
    assert int(t.Compression.NONE) == 0
    assert int(t.Compression.ZLIB) == 1
    assert int(t.Encryption.NONE) == 0
    assert int(t.RecoveryClass.EXACT) == 0
    assert int(t.RecoveryClass.NEAR_EXACT) == 1


def test_frame_fields_dataclass():
    f = t.FrameFields(
        payload_type=t.PayloadType.TEXT,
        compression=t.Compression.NONE,
        encryption=t.Encryption.NONE,
        recovery_class=t.RecoveryClass.EXACT,
        original_filename="secret.txt",
        mime_type="text/plain",
        sha256=b"\x00" * 32,
        payload_bytes=b"hello",
    )
    assert f.salt is None
    assert f.nonce is None
    assert f.payload_bytes == b"hello"


def test_capacity_report_dataclass():
    r = t.CapacityReport(
        total_bits=800, total_bytes=100, overhead_bytes=79,
        usable_bytes=21, is_estimate=True, assumptions="nominal",
    )
    assert r.usable_bytes == 21
    assert r.is_estimate is True
