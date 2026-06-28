import pytest

from stegolab.core import errors
from stegolab.text import zero_width as zw

COVER = " ".join(f"word{i}" for i in range(600))  # 599 word-boundary slots


def _write(tmp_path, name, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def _cover(tmp_path, text=COVER):
    return _write(tmp_path, "cover.txt", text.encode("utf-8"))


def test_text_round_trip(tmp_path):
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "secret.txt", b"meet at midnight")
    out, rec = tmp_path / "stego.txt", tmp_path / "rec.txt"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    summary = zw.extract(stego=str(out), out=str(rec), overwrite=False, params={})
    assert rec.read_bytes() == b"meet at midnight"
    assert summary["integrity"] == "ok"


def test_visible_text_preserved(tmp_path):
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "s.txt", b"hi")
    out = tmp_path / "stego.txt"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    stego = out.read_bytes().decode("utf-8")
    stripped = "".join(ch for ch in stego if ch not in zw.DEFAULT_ALPHABET)
    assert stripped == COVER  # only invisible chars were added


def test_bytes_payload_round_trip(tmp_path):
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "blob.bin", bytes(range(40)))
    out, rec = tmp_path / "stego.txt", tmp_path / "rec.bin"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    zw.extract(stego=str(out), out=str(rec), overwrite=False, params={})
    assert rec.read_bytes() == bytes(range(40))


def test_capacity_report(tmp_path):
    cover = _cover(tmp_path)
    rep = zw.capacity(cover=str(cover), params={})
    assert rep.total_bits == 599 * 2 * 4  # slots × bits_per_symbol × max_density
    assert rep.usable_bytes == rep.total_bytes - rep.overhead_bytes


def test_capacity_exceeded_non_destructive(tmp_path):
    cover = _cover(tmp_path, "one two three")  # 2 slots only
    payload = _write(tmp_path, "big.txt", b"x" * 500)
    out = tmp_path / "stego.txt"
    with pytest.raises(errors.CapacityExceeded):
        zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    assert not out.exists()


def test_cover_with_alphabet_chars_rejected(tmp_path):
    bad = _write(tmp_path, "bad.txt", ("hello‌world " * 50).encode("utf-8"))
    payload = _write(tmp_path, "s.txt", b"hi")
    out = tmp_path / "stego.txt"
    with pytest.raises(errors.InvalidArguments):
        zw.hide(cover=str(bad), payload=str(payload), out=str(out), overwrite=False, params={})


def test_strip_zero_width_breaks_extraction(tmp_path):
    # The honest fragility demo: stripping the invisible chars destroys the payload.
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "s.txt", b"top secret")
    out, rec = tmp_path / "stego.txt", tmp_path / "rec.txt"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    stego = out.read_bytes().decode("utf-8")
    stripped = "".join(ch for ch in stego if ch not in zw.DEFAULT_ALPHABET)
    attacked = tmp_path / "attacked.txt"
    attacked.write_bytes(stripped.encode("utf-8"))
    with pytest.raises((errors.NoPayloadFound, errors.CorruptedPayload, errors.IntegrityCheckFailed)):
        zw.extract(stego=str(attacked), out=str(rec), overwrite=False, params={})


def test_minimal_alphabet_round_trip(tmp_path):
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "s.txt", b"abc")
    out, rec = tmp_path / "stego.txt", tmp_path / "rec.txt"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"alphabet": "minimal"})
    zw.extract(stego=str(out), out=str(rec), overwrite=False, params={"alphabet": "minimal"})
    assert rec.read_bytes() == b"abc"
