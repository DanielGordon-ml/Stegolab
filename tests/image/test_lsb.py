import numpy as np
import pytest
from PIL import Image

from stegolab.core import errors
from stegolab.image import io_image, lsb


def _cover(tmp_path, w=64, h=64, seed=0):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    p = tmp_path / "cover.png"
    Image.fromarray(arr).save(p)
    return p


def _payload(tmp_path, data=b"the meeting is at noon", name="secret.txt"):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_text_round_trip(tmp_path):
    cover = _cover(tmp_path)
    payload = _payload(tmp_path, b"the meeting is at noon under the old oak")
    out = tmp_path / "stego.png"
    rec = tmp_path / "rec.txt"
    lsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"bits_per_channel": 1})
    summary = lsb.extract(stego=str(out), out=str(rec), overwrite=False, params={"bits_per_channel": 1})
    assert rec.read_bytes() == b"the meeting is at noon under the old oak"
    assert summary["integrity"] == "ok"


def test_image_payload_round_trip(tmp_path):
    cover = _cover(tmp_path, 80, 80)
    icon = tmp_path / "icon.png"
    Image.fromarray(np.full((6, 6, 3), 99, np.uint8)).save(icon)
    out = tmp_path / "stego.png"
    rec = tmp_path / "rec.png"
    lsb.hide(cover=str(cover), payload=str(icon), out=str(out), overwrite=False, params={})
    lsb.extract(stego=str(out), out=str(rec), overwrite=False, params={})
    assert rec.read_bytes() == icon.read_bytes()


def test_multi_bit_round_trip(tmp_path):
    cover = _cover(tmp_path, 32, 32)
    payload = _payload(tmp_path, bytes(range(200)))
    out = tmp_path / "stego.png"
    rec = tmp_path / "rec.bin"
    lsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"bits_per_channel": 4})
    lsb.extract(stego=str(out), out=str(rec), overwrite=False, params={"bits_per_channel": 4})
    assert rec.read_bytes() == bytes(range(200))


def test_capacity_exceeded_before_write(tmp_path):
    cover = _cover(tmp_path, 8, 8)  # 8*8*3 = 192 bits -> 24 bytes minus overhead -> negative usable
    payload = _payload(tmp_path, b"x" * 500)
    out = tmp_path / "stego.png"
    with pytest.raises(errors.CapacityExceeded):
        lsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    assert not out.exists()  # non-destructive


def test_capacity_report(tmp_path):
    cover = _cover(tmp_path, 100, 100)
    rep = lsb.capacity(cover=str(cover), params={"bits_per_channel": 1})
    assert rep.total_bits == 100 * 100 * 3
    assert rep.usable_bytes == rep.total_bytes - rep.overhead_bytes


def test_stego_visually_close_to_cover(tmp_path):
    cover = _cover(tmp_path, 64, 64)
    payload = _payload(tmp_path, b"hi")
    out = tmp_path / "stego.png"
    lsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"bits_per_channel": 1})
    c = io_image.load_image_rgb(cover).astype(int)
    s = io_image.load_image_rgb(out).astype(int)
    assert np.abs(c - s).max() <= 1  # single-LSB changes are at most ±1
