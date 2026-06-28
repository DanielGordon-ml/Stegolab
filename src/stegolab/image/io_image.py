"""PNG/BMP image I/O and resizing for steganography methods (spec §9.1, §9.4)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from ..core.errors import OutputExists, UnsupportedFileType

_LOSSLESS_EXT = {".png", ".bmp"}
_RESAMPLE = Image.Resampling.LANCZOS


def load_image_rgb(path) -> np.ndarray:
    img = Image.open(path)
    if (img.format or "").upper() not in {"PNG", "BMP"}:
        raise UnsupportedFileType(
            f"unsupported cover/stego image format {img.format!r}; use PNG or BMP"
        )
    return np.asarray(img.convert("RGB"), dtype=np.uint8).copy()


def save_image(path, arr: np.ndarray, *, overwrite: bool = False) -> None:
    p = Path(path)
    if p.suffix.lower() not in _LOSSLESS_EXT:
        raise UnsupportedFileType(
            f"refusing to write lossy/unknown format {p.suffix!r}; use .png or .bmp"
        )
    if p.exists() and not overwrite:
        raise OutputExists(f"output exists: {p} (pass overwrite to replace)")
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(arr, dtype=np.uint8)).save(p)


def resize_to(arr: np.ndarray, size_wh: tuple[int, int], mode: str) -> np.ndarray:
    w, h = size_wh
    if mode == "reject":
        if arr.shape[1] != w or arr.shape[0] != h:
            raise UnsupportedFileType(
                f"hidden image {arr.shape[1]}x{arr.shape[0]} != cover {w}x{h} and resize_mode=reject"
            )
        return arr
    img = Image.fromarray(arr)
    if mode in ("fit", "stretch"):
        out = img.resize((w, h), _RESAMPLE)
    elif mode == "center-crop":
        out = _center_crop(img, w, h)
    else:
        raise UnsupportedFileType(f"unknown resize_mode {mode!r}")
    return np.asarray(out, dtype=np.uint8).copy()


def _center_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), _RESAMPLE)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    return resized.crop((left, top, left + w, top + h))
