import numpy as np
import pytest
from PIL import Image

from stegolab.image import bitplane_image as bp, io_image


def _png(path, arr):
    Image.fromarray(arr.astype(np.uint8)).save(path)
    return path


def test_recovered_image_is_viewable_and_cover_sized(tmp_path):
    rng = np.random.default_rng(4)
    cover = _png(tmp_path / "cover.png", rng.integers(0, 256, (32, 32, 3)))
    hidden = _png(tmp_path / "hidden.png", rng.integers(0, 256, (16, 16, 3)))
    out, rec = tmp_path / "stego.png", tmp_path / "rec.png"
    bp.hide(cover=str(cover), payload=str(hidden), out=str(out), overwrite=False,
            params={"hidden_msb_bits": 4, "cover_lsb_bits": 4, "resize_mode": "stretch"})
    bp.extract(stego=str(out), out=str(rec), overwrite=False,
               params={"hidden_msb_bits": 4, "cover_lsb_bits": 4})
    recovered = io_image.load_image_rgb(rec)
    assert recovered.shape == (32, 32, 3)  # cover-sized


def test_recovered_top_bits_match_hidden(tmp_path):
    rng = np.random.default_rng(5)
    cover = _png(tmp_path / "cover.png", rng.integers(0, 256, (16, 16, 3)))
    hidden_arr = rng.integers(0, 256, (16, 16, 3)).astype(np.uint8)
    hidden = _png(tmp_path / "hidden.png", hidden_arr)
    out, rec = tmp_path / "stego.png", tmp_path / "rec.png"
    bp.hide(cover=str(cover), payload=str(hidden), out=str(out), overwrite=False,
            params={"hidden_msb_bits": 4, "cover_lsb_bits": 4, "resize_mode": "reject"})
    bp.extract(stego=str(out), out=str(rec), overwrite=False,
               params={"hidden_msb_bits": 4, "cover_lsb_bits": 4})
    recovered = io_image.load_image_rgb(rec)
    # top 4 bits of hidden must survive exactly
    assert np.array_equal(recovered >> 4, hidden_arr >> 4)


def test_stego_low_bits_only_changed(tmp_path):
    rng = np.random.default_rng(6)
    cover_arr = rng.integers(0, 256, (16, 16, 3)).astype(np.uint8)
    cover = _png(tmp_path / "cover.png", cover_arr)
    hidden = _png(tmp_path / "hidden.png", rng.integers(0, 256, (16, 16, 3)))
    out = tmp_path / "stego.png"
    bp.hide(cover=str(cover), payload=str(hidden), out=str(out), overwrite=False,
            params={"hidden_msb_bits": 4, "cover_lsb_bits": 4, "resize_mode": "reject"})
    stego = io_image.load_image_rgb(out)
    assert np.array_equal(stego >> 4, cover_arr >> 4)  # high 4 bits of cover preserved
