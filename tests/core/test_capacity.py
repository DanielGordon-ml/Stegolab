from stegolab.core import capacity
from stegolab.core import types as t


def test_nominal_overhead_is_79():
    # 11 prefix + 40 fixed header + 2 + len("") + 2 + len("application/octet-stream"=24)
    assert capacity.nominal_overhead() == 79


def test_frame_overhead_scales_with_filename_and_mime():
    base = capacity.frame_overhead_bytes("", "")
    assert base == t.FIXED_PREFIX_LEN + t.FIXED_HEADER_FIELDS + 2 + 0 + 2 + 0
    assert capacity.frame_overhead_bytes("ab.txt", "text/plain") == base + len("ab.txt") + len("text/plain")


def test_frame_overhead_adds_salt_and_nonce_when_encrypted():
    plain = capacity.frame_overhead_bytes("f", "m", encryption=t.Encryption.NONE)
    enc = capacity.frame_overhead_bytes(
        "f", "m", encryption=t.Encryption.AES_256_GCM, salt_len=16, nonce_len=12,
    )
    assert enc == plain + (1 + 16) + (1 + 12)


def test_build_capacity_report_subtracts_overhead():
    r = capacity.build_capacity_report(8000, 79, is_estimate=True, assumptions="nominal")
    assert r.total_bytes == 1000
    assert r.usable_bytes == 1000 - 79
    assert r.is_estimate is True


def test_usable_bytes_never_negative():
    r = capacity.build_capacity_report(80, 79, is_estimate=False, assumptions="x")
    assert r.total_bytes == 10
    assert r.usable_bytes == 0
