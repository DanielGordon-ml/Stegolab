import numpy as np
import pytest
from PIL import Image

from stegolab.core import errors
from stegolab.image import io_image


def _make_png(path, w=8, h=6):
    arr = (np.arange(h * w * 3, dtype=np.uint8) % 251).reshape(h, w, 3)
    Image.fromarray(arr, "RGB").save(path)
    return arr


def test_load_png_rgb(tmp_path):
    p = tmp_path / "c.png"
    arr = _make_png(p)
    loaded = io_image.load_image_rgb(p)
    assert loaded.shape == (6, 8, 3)
    assert loaded.dtype == np.uint8
    assert np.array_equal(loaded, arr)


def test_load_drops_alpha(tmp_path):
    p = tmp_path / "a.png"
    Image.fromarray(np.zeros((4, 4, 4), dtype=np.uint8), "RGBA").save(p)
    assert io_image.load_image_rgb(p).shape == (4, 4, 3)


def test_load_rejects_jpeg(tmp_path):
    p = tmp_path / "c.jpg"
    Image.fromarray(np.zeros((4, 4, 3), dtype=np.uint8), "RGB").save(p)
    with pytest.raises(errors.UnsupportedFileType):
        io_image.load_image_rgb(p)


def test_save_round_trip(tmp_path):
    arr = (np.arange(4 * 5 * 3, dtype=np.uint8) % 251).reshape(4, 5, 3)
    out = tmp_path / "o.png"
    io_image.save_image(out, arr)
    assert np.array_equal(io_image.load_image_rgb(out), arr)


def test_save_rejects_lossy_extension(tmp_path):
    with pytest.raises(errors.UnsupportedFileType):
        io_image.save_image(tmp_path / "o.jpg", np.zeros((2, 2, 3), np.uint8))


def test_save_no_overwrite(tmp_path):
    out = tmp_path / "o.png"
    io_image.save_image(out, np.zeros((2, 2, 3), np.uint8))
    with pytest.raises(errors.OutputExists):
        io_image.save_image(out, np.zeros((2, 2, 3), np.uint8))
    io_image.save_image(out, np.ones((2, 2, 3), np.uint8), overwrite=True)


def test_resize_reject_mismatch():
    a = np.zeros((4, 4, 3), np.uint8)
    with pytest.raises(errors.UnsupportedFileType):
        io_image.resize_to(a, (8, 8), "reject")


def test_resize_stretch_changes_shape():
    a = np.zeros((4, 4, 3), np.uint8)
    out = io_image.resize_to(a, (8, 6), "stretch")  # (W=8,H=6)
    assert out.shape == (6, 8, 3)
