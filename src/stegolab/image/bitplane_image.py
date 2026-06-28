"""image-bitplane: visual image-in-image demo (spec §9.4). NOT byte-exact.

Stores the top `hidden_msb_bits` of a (resized) hidden image in the low
`cover_lsb_bits` of the cover. The recovered image is cover-sized and approximate.
"""

from __future__ import annotations

import numpy as np

from ..core import capacity as cap
from ..core.errors import InvalidArguments
from ..core.types import CapacityReport
from . import io_image


def _bits(params: dict) -> tuple[int, int]:
    msb = int(params.get("hidden_msb_bits", 4))
    lsbn = int(params.get("cover_lsb_bits", 4))
    if not 1 <= msb <= 8 or not 1 <= lsbn <= 8 or msb > lsbn:
        raise InvalidArguments("require 1<=hidden_msb_bits<=cover_lsb_bits<=8")
    return msb, lsbn


def capacity(*, cover: str, params: dict) -> CapacityReport:
    msb, lsbn = _bits(params)
    arr = io_image.load_image_rgb(cover)
    total_bits = int(arr.size) * lsbn
    return cap.build_capacity_report(
        total_bits, 0, is_estimate=False,
        assumptions=f"image-bitplane stores {msb} MSBs of the hidden image in {lsbn} cover LSBs; visual only",
    )


def hide(*, cover: str, payload: str, out: str, overwrite: bool, params: dict) -> dict:
    msb, lsbn = _bits(params)
    resize_mode = params.get("resize_mode", "fit")
    cover_arr = io_image.load_image_rgb(cover)
    h, w = cover_arr.shape[0], cover_arr.shape[1]
    hidden = io_image.resize_to(io_image.load_image_rgb(payload), (w, h), resize_mode)
    top_bits = (hidden >> (8 - msb)).astype(np.uint8)        # values 0..2^msb-1
    stored = (top_bits << (lsbn - msb)).astype(np.uint8)      # left-align inside the lsbn field
    keep = (cover_arr >> lsbn) << lsbn
    stego = (keep | stored).astype(np.uint8)
    io_image.save_image(out, stego, overwrite=overwrite)
    return {"method": "image-bitplane", "out": out, "params": {"hidden_msb_bits": msb, "cover_lsb_bits": lsbn}}


def extract(*, stego: str, out: str, overwrite: bool, params: dict) -> dict:
    msb, lsbn = _bits(params)
    arr = io_image.load_image_rgb(stego)
    low = (arr & np.uint8((1 << lsbn) - 1)).astype(np.uint8)
    top_bits = (low >> (lsbn - msb)).astype(np.uint8)
    recovered = (top_bits << (8 - msb)).astype(np.uint8)      # place recovered MSBs high, low bits 0
    io_image.save_image(out, recovered, overwrite=overwrite)
    return {"method": "image-bitplane", "out": out, "exact": False,
            "note": "visual reconstruction; hidden image bytes are not preserved"}
