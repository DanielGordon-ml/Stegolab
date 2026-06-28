"""image-randomized-lsb: key-seeded permutation of embedding slots (spec §9.2)."""

from __future__ import annotations

import numpy as np

from ..core import capacity as cap, frame as frame_mod, keys, payload_codec
from ..core.errors import InvalidArguments
from ..core.types import CapacityReport
from . import io_image, lsb


def _order(n_slots: int, params: dict) -> np.ndarray:
    key = params.get("key")
    if key:
        return keys.permutation(n_slots, str(key))
    if params.get("allow_unkeyed"):
        return np.arange(n_slots)
    raise InvalidArguments("image-randomized-lsb requires --key (or --allow-unkeyed)")


def capacity(*, cover: str, params: dict) -> CapacityReport:
    bpc = lsb._validate_bpc(params)
    arr = io_image.load_image_rgb(cover)
    return cap.build_capacity_report(
        int(arr.size) * bpc, cap.nominal_overhead(), is_estimate=True,
        assumptions=f"image-randomized-lsb bits_per_channel={bpc}; keyed order does not change capacity",
    )


def hide(*, cover: str, payload: str, out: str, overwrite: bool, params: dict) -> dict:
    bpc = lsb._validate_bpc(params)
    framed = lsb.build_framed_payload(payload, params.get("compress", "auto"))
    arr = io_image.load_image_rgb(cover)
    flat = arr.reshape(-1).copy()
    order = _order(flat.size, params)
    lsb.embed_bits_in_order(flat, order, lsb.bitstream.bytes_to_bits(framed), bpc)
    io_image.save_image(out, flat.reshape(arr.shape), overwrite=overwrite)
    return {"method": "image-randomized-lsb", "out": out, "bytes": len(framed),
            "params": {"bits_per_channel": bpc, "keyed": bool(params.get("key"))}}


def extract(*, stego: str, out: str, overwrite: bool, params: dict) -> dict:
    bpc = lsb._validate_bpc(params)
    arr = io_image.load_image_rgb(stego)
    flat = arr.reshape(-1)
    order = _order(flat.size, params)
    parsed = frame_mod.parse_frame(lsb.recover_frame(flat, order, bpc))
    original = payload_codec.decode_payload(parsed)
    from ..core import io as core_io
    core_io.write_bytes(out, original, overwrite=overwrite)
    return {"method": "image-randomized-lsb", "out": out, "bytes": len(original),
            "original_filename": parsed.original_filename, "mime_type": parsed.mime_type, "integrity": "ok"}
