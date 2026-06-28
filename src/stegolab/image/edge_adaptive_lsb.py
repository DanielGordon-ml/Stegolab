"""image-edge-adaptive-lsb: embed in highest-activity (textured) regions first (spec §9.3).

Determinism: the activity map is computed only from bit planes >= bits_per_channel,
which b-bit LSB embedding never modifies, so sender and receiver derive the identical
slot order from cover and stego respectively.
"""

from __future__ import annotations

import numpy as np

from ..core import capacity as cap, frame as frame_mod, io as core_io, payload_codec
from ..core.bitstream import bytes_to_bits
from ..core.types import CapacityReport
from . import io_image, lsb


def activity_map(arr: np.ndarray, bpc: int) -> np.ndarray:
    masked = (arr.astype(np.int32) >> bpc) << bpc  # zero the low bpc bits per channel
    gray = masked.mean(axis=2)                      # HxW
    gy, gx = np.gradient(gray)
    return np.sqrt(gx * gx + gy * gy)


def slot_order(arr: np.ndarray, bpc: int) -> np.ndarray:
    act = activity_map(arr, bpc)                     # HxW
    slot_act = np.repeat(act.reshape(-1), 3)         # one activity per (pixel,channel) slot
    return np.argsort(-slot_act, kind="stable")      # descending activity, stable tie-break


def _eligible_slot_count(arr: np.ndarray, bpc: int) -> int:
    """Number of high-activity channel-slots (the embedding budget).

    Pixels with activity >= the median floor are eligible; each contributes its 3 channels.
    The floor is reproducible from bit planes >= bpc, so it is identical on cover and stego.
    """
    act = activity_map(arr, bpc)
    floor = np.percentile(act, 50.0)                 # documented floor: median activity
    return int(np.count_nonzero(act >= floor)) * 3


def capacity(*, cover: str, params: dict) -> CapacityReport:
    bpc = lsb._validate_bpc(params)
    arr = io_image.load_image_rgb(cover)
    eligible_bits = _eligible_slot_count(arr, bpc) * bpc
    return cap.build_capacity_report(
        eligible_bits, cap.nominal_overhead(), is_estimate=True,
        assumptions=(
            f"image-edge-adaptive-lsb bits_per_channel={bpc}; usable = highest-activity slots "
            f"above the median floor. Larger payloads raise CapacityExceeded (use a bigger cover "
            f"or image-lsb). MVP uses activity=gradient and the median floor (threshold_mode auto)."
        ),
    )


def hide(*, cover: str, payload: str, out: str, overwrite: bool, params: dict) -> dict:
    bpc = lsb._validate_bpc(params)
    framed = lsb.build_framed_payload(payload, params.get("compress", "auto"))
    arr = io_image.load_image_rgb(cover)
    flat = arr.reshape(-1).copy()
    eligible = _eligible_slot_count(arr, bpc)
    order = slot_order(arr, bpc)[:eligible]            # embed only in high-activity slots
    lsb.embed_bits_in_order(flat, order, bytes_to_bits(framed), bpc)  # CapacityExceeded fires at the floor
    io_image.save_image(out, flat.reshape(arr.shape), overwrite=overwrite)
    return {"method": "image-edge-adaptive-lsb", "out": out, "bytes": len(framed),
            "params": {"bits_per_channel": bpc}}


def extract(*, stego: str, out: str, overwrite: bool, params: dict) -> dict:
    bpc = lsb._validate_bpc(params)
    arr = io_image.load_image_rgb(stego)
    flat = arr.reshape(-1)
    order = slot_order(arr, bpc)
    parsed = frame_mod.parse_frame(lsb.recover_frame(flat, order, bpc))
    original = payload_codec.decode_payload(parsed)
    core_io.write_bytes(out, original, overwrite=overwrite)
    return {"method": "image-edge-adaptive-lsb", "out": out, "bytes": len(original),
            "original_filename": parsed.original_filename, "mime_type": parsed.mime_type, "integrity": "ok"}
