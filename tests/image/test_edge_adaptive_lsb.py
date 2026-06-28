import numpy as np
import pytest
from PIL import Image

from stegolab.core import errors
from stegolab.image import edge_adaptive_lsb as eal


def _textured_cover(tmp_path, w=64, h=64, seed=2):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(tmp_path / "c.png")
    return tmp_path / "c.png"


def _payload(tmp_path, data=b"edge adaptive secret"):
    (tmp_path / "p.txt").write_bytes(data)
    return tmp_path / "p.txt"


@pytest.mark.parametrize("bpc", [1, 2, 4])
def test_round_trip_each_bpc(tmp_path, bpc):
    cover, payload = _textured_cover(tmp_path), _payload(tmp_path, bytes(range(120)))
    out, rec = tmp_path / "s.png", tmp_path / "r.bin"
    eal.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"bits_per_channel": bpc})
    eal.extract(stego=str(out), out=str(rec), overwrite=False, params={"bits_per_channel": bpc})
    assert rec.read_bytes() == bytes(range(120))


def test_order_identical_on_cover_and_stego(tmp_path):
    # The determinism guarantee: embedding (low bpc bits) must not change the order.
    from stegolab.image import io_image
    cover, payload = _textured_cover(tmp_path), _payload(tmp_path)
    out = tmp_path / "s.png"
    eal.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"bits_per_channel": 1})
    c = io_image.load_image_rgb(cover).reshape(-1)
    s = io_image.load_image_rgb(out).reshape(-1)
    oc = eal.slot_order(io_image.load_image_rgb(cover), 1)
    os = eal.slot_order(io_image.load_image_rgb(out), 1)
    assert np.array_equal(oc, os)


def test_activity_unaffected_by_lsb_change():
    rng = np.random.default_rng(3)
    arr = rng.integers(0, 256, (16, 16, 3), dtype=np.uint8)
    a1 = eal.activity_map(arr, 1)
    flipped = arr.copy()
    flipped[..., :] ^= 1  # flip LSBs only
    a2 = eal.activity_map(flipped, 1)
    assert np.allclose(a1, a2)


def test_capacity_floor_enforced_before_full_image(tmp_path):
    # A payload that exceeds the above-floor budget must raise, even if it would
    # fit the whole image — capacity() and hide() must agree on the floor.
    cover = _textured_cover(tmp_path, 32, 32)
    rep = eal.capacity(cover=str(cover), params={"bits_per_channel": 1})
    blob = np.random.default_rng(11).integers(0, 256, rep.usable_bytes + 50, dtype=np.uint8).tobytes()
    payload = _payload(tmp_path, blob)
    out = tmp_path / "s.png"
    with pytest.raises(errors.CapacityExceeded):
        eal.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"bits_per_channel": 1})
    assert not out.exists()
