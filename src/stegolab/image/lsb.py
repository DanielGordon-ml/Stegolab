"""Shared LSB-family embed/extract engine + the sequential `image-lsb` method.

All three LSB methods (sequential, randomized, edge-adaptive) reuse
embed_bits_in_order / read_bits_in_order and differ only in the slot `order`.
A "slot" is one channel sample in the flattened HxWx3 array; each slot carries
`bits_per_channel` LSBs.
"""

from __future__ import annotations

import numpy as np

from ..core import bitstream, capacity as cap, frame as frame_mod, io as core_io, payload_codec
from ..core.errors import CapacityExceeded
from ..core.types import CapacityReport, PayloadType
from . import io_image


def payload_type_for_mime(mime: str) -> PayloadType:
    if mime.startswith("text/"):
        return PayloadType.TEXT
    if mime.startswith("image/"):
        return PayloadType.IMAGE
    return PayloadType.BYTES


def build_framed_payload(payload_path: str, compress: str) -> bytes:
    raw = core_io.read_bytes(payload_path)
    mime = core_io.detect_mime(payload_path)
    return payload_codec.encode_payload(
        raw=raw,
        payload_type=payload_type_for_mime(mime),
        original_filename=core_io.sanitize_filename(str(payload_path)),
        mime_type=mime,
        compression=compress,
    )


def embed_bits_in_order(flat: np.ndarray, order: np.ndarray, frame_bits: np.ndarray, bpc: int) -> None:
    n_slots = (frame_bits.size + bpc - 1) // bpc
    if n_slots > order.size:
        raise CapacityExceeded(
            f"payload needs {n_slots} slots but cover provides {order.size}"
        )
    padded = np.zeros(n_slots * bpc, dtype=np.uint8)
    padded[: frame_bits.size] = frame_bits
    weights = (1 << np.arange(bpc - 1, -1, -1)).astype(np.uint16)
    slot_vals = (padded.reshape(n_slots, bpc) * weights).sum(axis=1).astype(np.uint8)
    keep_mask = np.uint8(0xFF ^ ((1 << bpc) - 1))
    sel = order[:n_slots]
    flat[sel] = (flat[sel] & keep_mask) | slot_vals


def read_bits_in_order(flat: np.ndarray, order: np.ndarray, bpc: int) -> np.ndarray:
    low_mask = np.uint8((1 << bpc) - 1)
    vals = (flat[order] & low_mask).astype(np.uint8)
    shifts = np.arange(bpc - 1, -1, -1, dtype=np.uint8)
    return ((vals[:, None] >> shifts) & 1).astype(np.uint8).reshape(-1)


def recover_frame(flat: np.ndarray, order: np.ndarray, bpc: int) -> bytes:
    bits = read_bits_in_order(flat, order, bpc)
    usable = (bits.size // 8) * 8
    return bitstream.bits_to_bytes(bits[:usable])


# --- image-lsb (sequential order) ---

def _validate_bpc(params: dict) -> int:
    bpc = int(params.get("bits_per_channel", 1))
    if not 1 <= bpc <= 4:
        from ..core.errors import InvalidArguments
        raise InvalidArguments("bits_per_channel must be in 1..4")
    return bpc


def capacity(*, cover: str, params: dict) -> CapacityReport:
    bpc = _validate_bpc(params)
    arr = io_image.load_image_rgb(cover)
    total_bits = int(arr.size) * bpc
    return cap.build_capacity_report(
        total_bits, cap.nominal_overhead(), is_estimate=True,
        assumptions=f"image-lsb bits_per_channel={bpc}; nominal frame overhead (filename/mime add to it)",
    )


def hide(*, cover: str, payload: str, out: str, overwrite: bool, params: dict) -> dict:
    bpc = _validate_bpc(params)
    framed = build_framed_payload(payload, params.get("compress", "auto"))
    arr = io_image.load_image_rgb(cover)
    flat = arr.reshape(-1).copy()
    order = np.arange(flat.size)
    frame_bits = bitstream.bytes_to_bits(framed)
    embed_bits_in_order(flat, order, frame_bits, bpc)  # raises CapacityExceeded before any write
    io_image.save_image(out, flat.reshape(arr.shape), overwrite=overwrite)
    return {"method": "image-lsb", "out": out, "bytes": len(framed), "params": {"bits_per_channel": bpc}}


def extract(*, stego: str, out: str, overwrite: bool, params: dict) -> dict:
    bpc = _validate_bpc(params)
    arr = io_image.load_image_rgb(stego)
    flat = arr.reshape(-1)
    order = np.arange(flat.size)
    parsed = frame_mod.parse_frame(recover_frame(flat, order, bpc))
    original = payload_codec.decode_payload(parsed)
    core_io.write_bytes(out, original, overwrite=overwrite)
    return {
        "method": "image-lsb", "out": out, "bytes": len(original),
        "original_filename": parsed.original_filename, "mime_type": parsed.mime_type,
        "integrity": "ok",
    }
