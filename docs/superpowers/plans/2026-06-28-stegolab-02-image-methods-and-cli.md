# StegoLab Image Methods + Minimal CLI Implementation Plan (Plan 02 of 08)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the four MVP image steganography methods (`image-lsb`, `image-randomized-lsb`, `image-edge-adaptive-lsb`, `image-bitplane`) and a minimal `stegolab` CLI exposing `hide`, `extract`, and `capacity` for them — the first end-to-end working hide/extract.

**Architecture:** Builds entirely on the `stegolab.core` package from Plan 01 (frame codec, payload codec, capacity, keys, errors, types, io). A new `core/bitstream.py` converts framed bytes ↔ a NumPy bit array. The three LSB-family methods share one embed/extract-in-order engine in `image/lsb.py` and differ only in the *slot ordering*: sequential (`image-lsb`), key-seeded permutation (`image-randomized-lsb`, via `core.keys.permutation`), and activity-descending (`image-edge-adaptive-lsb`). `image-bitplane` is a separate visual image-in-image demo. A Typer CLI dispatches by method id and maps `StegoLabError`→exit codes.

**Tech Stack:** Python 3.11+, NumPy, Pillow (image I/O), Typer (CLI), pytest. Reuses `stegolab.core`.

## Global Constraints

Copied verbatim from `stegolab_engineering_spec.md` and Plan 01. Every task inherits these.

- **Python 3.11+; all frame integers big-endian; strings UTF-8** (Plan 01).
- **Reuse `stegolab.core`** — do NOT reimplement framing, compression, hashing, capacity overhead, the PRNG, or file safety. Public API: `core.encode_payload`, `core.decode_payload`, `core.parse_frame`, `core.frame.header_len_from_prefix`, `core.permutation`, `core.frame_overhead_bytes`, `core.nominal_overhead`, `core.build_capacity_report`, `core.io.{read_bytes,write_bytes,detect_mime,sanitize_filename,safe_output_path}`, and the enums/dataclasses in `core.types`.
- **Bit order is MSB-first** (`np.unpackbits`/`np.packbits` default), used consistently for both bytes↔bits and within a multi-bit slot.
- **`image-lsb` capacity:** `capacity_bits = width × height × 3 × bits_per_channel`; `capacity_bytes = floor(capacity_bits/8) − frame_overhead_bytes` (spec §9.1).
- **`bits_per_channel` range `1`–`4`**; RGB only (ignore alpha by default); reject lossy output formats (only `.png`/`.bmp` may be written).
- **`image-randomized-lsb` requires a key unless `--allow-unkeyed`**; key→order via `core.permutation(n_slots, key)` (`seed=SHA-256(key)[:8]`, PCG64). Same key+params reproduce the same order; wrong key fails integrity (spec §9.2, §8.6).
- **`image-edge-adaptive-lsb` determinism:** the activity map MUST be computed only from bit planes ≥ `bits_per_channel` (mask off the low `bits_per_channel` bits before scoring), so the receiver recomputes the identical slot order from the stego image (spec §9.3).
- **`image-bitplane` is visual reconstruction only** — not byte-exact; recovered image is cover-sized (spec §9.4).
- **Extraction integrity:** every LSB-family extract validates the frame checksum via `core.decode_payload`; a checksum mismatch raises `IntegrityCheckFailed` (spec §20.4). Frame parsing already ignores trailing bytes, so "read all slot bits → bytes → parse_frame" is safe.
- **CLI:** command `stegolab`; subcommands `hide`/`extract`/`capacity`; flags `--method`, `--bits-per-channel`, `--channels`, `--key`, `--allow-unkeyed`, `--activity`, `--threshold-mode`, `--hidden-msb-bits`, `--cover-lsb-bits`, `--resize-mode`, `--compress`, `--overwrite`, `--json`. Catch `StegoLabError` → exit with its `exit_code`; `--json` uses the §10.9 envelope `{ok, command, method, result, error}`.
- **File safety:** never overwrite without `--overwrite` (raise `OutputExists`); sanitize payload filenames; never write outside the requested output path (Plan 01 `core.io`).

## Method Interface Contract (uniform across all method modules)

Every method module (`image/lsb.py`, `image/randomized_lsb.py`, `image/edge_adaptive_lsb.py`, `image/bitplane_image.py`) exposes exactly these three functions so the CLI can dispatch generically:

```python
def capacity(*, cover: str, params: dict) -> core.types.CapacityReport: ...
def hide(*, cover: str, payload: str, out: str, overwrite: bool, params: dict) -> dict: ...
def extract(*, stego: str, out: str, overwrite: bool, params: dict) -> dict: ...
```

- `params` carries method-specific options (`bits_per_channel`, `key`, `allow_unkeyed`, `activity`, `threshold_mode`, `hidden_msb_bits`, `cover_lsb_bits`, `resize_mode`, `compress`); a method reads only the keys it needs and ignores the rest.
- `hide`/`extract` return a JSON-serializable summary dict: at minimum `{"method", "out", "bytes", "params"}`; `extract` also includes `{"original_filename", "mime_type", "integrity": "ok"}`.
- For `image-bitplane`, `payload` is the hidden-image path; `bitplane` does not use the frame.

## File Structure

- `pyproject.toml` — add `pillow` and `typer` deps; add `[project.scripts] stegolab`.
- `src/stegolab/core/bitstream.py` (NEW) — `bytes_to_bits`, `bits_to_bytes`.
- `src/stegolab/core/__init__.py` — re-export `bitstream`, `bytes_to_bits`, `bits_to_bytes`.
- `src/stegolab/image/__init__.py` (NEW) — package marker + method registry.
- `src/stegolab/image/io_image.py` (NEW) — `load_image_rgb`, `save_image`, `resize_to`.
- `src/stegolab/image/lsb.py` (NEW) — `embed_bits_in_order`, `read_bits_in_order`, `payload_type_for_mime`, and `capacity`/`hide`/`extract` for `image-lsb`.
- `src/stegolab/image/randomized_lsb.py` (NEW) — `capacity`/`hide`/`extract` for `image-randomized-lsb`.
- `src/stegolab/image/edge_adaptive_lsb.py` (NEW) — `activity_map`, `slot_order`, and `capacity`/`hide`/`extract`.
- `src/stegolab/image/bitplane_image.py` (NEW) — `capacity`/`hide`/`extract` for `image-bitplane`.
- `src/stegolab/cli.py` (NEW) — Typer app with `hide`/`extract`/`capacity`.
- `tests/core/test_bitstream.py`, `tests/image/test_io_image.py`, `tests/image/test_lsb.py`, `tests/image/test_randomized_lsb.py`, `tests/image/test_edge_adaptive_lsb.py`, `tests/image/test_bitplane.py`, `tests/cli/test_cli_image.py`.

---

### Task 1: `core/bitstream.py` — bytes ↔ bit array

**Files:**
- Create: `src/stegolab/core/bitstream.py`
- Modify: `src/stegolab/core/__init__.py` (add re-exports)
- Test: `tests/core/test_bitstream.py`

**Interfaces:**
- Consumes: NumPy.
- Produces: `bytes_to_bits(data: bytes) -> np.ndarray` (uint8 array of 0/1, MSB-first, length `8*len(data)`); `bits_to_bytes(bits: np.ndarray) -> bytes` (length must be a multiple of 8, else `ValueError`). Round-trip identity. Used by every LSB method.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_bitstream.py`:

```python
import numpy as np
import pytest

from stegolab.core import bitstream


def test_round_trip_identity():
    data = bytes(range(256))
    bits = bitstream.bytes_to_bits(data)
    assert bits.dtype == np.uint8
    assert bits.shape == (256 * 8,)
    assert set(np.unique(bits).tolist()) <= {0, 1}
    assert bitstream.bits_to_bytes(bits) == data


def test_msb_first_layout():
    # 0x80 = 1000_0000 -> first bit is 1, rest 0
    bits = bitstream.bytes_to_bits(b"\x80")
    assert bits.tolist() == [1, 0, 0, 0, 0, 0, 0, 0]
    # 0x01 = 0000_0001 -> last bit is 1
    assert bitstream.bytes_to_bits(b"\x01").tolist() == [0, 0, 0, 0, 0, 0, 0, 1]


def test_empty():
    assert bitstream.bytes_to_bits(b"").shape == (0,)
    assert bitstream.bits_to_bytes(np.zeros(0, dtype=np.uint8)) == b""


def test_non_multiple_of_8_raises():
    with pytest.raises(ValueError):
        bitstream.bits_to_bytes(np.array([1, 0, 1], dtype=np.uint8))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_bitstream.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.core.bitstream'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/core/bitstream.py`:

```python
"""Convert framed bytes to/from an MSB-first bit array (NumPy uint8 of 0/1)."""

from __future__ import annotations

import numpy as np


def bytes_to_bits(data: bytes) -> np.ndarray:
    if not data:
        return np.zeros(0, dtype=np.uint8)
    arr = np.frombuffer(data, dtype=np.uint8)
    return np.unpackbits(arr)  # MSB-first, shape (8*len,)


def bits_to_bytes(bits: np.ndarray) -> bytes:
    bits = np.asarray(bits, dtype=np.uint8)
    if bits.size % 8 != 0:
        raise ValueError("bit array length must be a multiple of 8")
    if bits.size == 0:
        return b""
    return np.packbits(bits).tobytes()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_bitstream.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Re-export from core**

In `src/stegolab/core/__init__.py`, add `bitstream` to the submodule import line and add the two functions. Specifically change the submodule import to include `bitstream`:

```python
from . import bitstream, capacity, errors, frame, io, keys, payload_codec, types
```

and add after the existing `from .capacity import ...` line:

```python
from .bitstream import bits_to_bytes, bytes_to_bits
```

and add `"bitstream"`, `"bits_to_bytes"`, `"bytes_to_bits"` to `__all__`.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (56 passed: 52 from Plan 01 + 4 new). Confirm no import error from the updated `__init__`.

- [ ] **Step 7: Commit**

```bash
git add src/stegolab/core/bitstream.py src/stegolab/core/__init__.py tests/core/test_bitstream.py
git commit -m "feat(core): bytes<->bits bitstream helper"
```

---

### Task 2: `image/io_image.py` — PNG/BMP load/save + resize

**Files:**
- Modify: `pyproject.toml` (add `pillow`)
- Create: `src/stegolab/image/__init__.py`
- Create: `src/stegolab/image/io_image.py`
- Test: `tests/image/test_io_image.py`

**Interfaces:**
- Consumes: Pillow, NumPy, `core.errors.{UnsupportedFileType, OutputExists}`.
- Produces:
  - `load_image_rgb(path) -> np.ndarray` — opens PNG/BMP, converts to RGB (drops alpha), returns a writable `HxWx3` uint8 array. Rejects other formats (e.g. JPEG cover) with `UnsupportedFileType`.
  - `save_image(path, arr, *, overwrite=False) -> None` — writes a lossless image; only `.png`/`.bmp` extensions allowed (else `UnsupportedFileType`); raises `OutputExists` if the path exists and `overwrite` is False.
  - `resize_to(arr, size_wh, mode) -> np.ndarray` — `mode` in `{"reject","fit","stretch","center-crop"}`; `reject` raises `UnsupportedFileType` if `arr` shape ≠ target; others return an `HxWx3` array of the target size.

- [ ] **Step 1: Add Pillow dependency**

In `pyproject.toml`, change the `dependencies` array to:

```toml
dependencies = [
    "numpy>=1.26",
    "pillow>=10.0",
]
```

- [ ] **Step 2: Write the failing test**

Create `tests/image/test_io_image.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/image/test_io_image.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.image'`.

- [ ] **Step 4: Write minimal implementation**

Create `src/stegolab/image/__init__.py`:

```python
"""Image steganography methods (LSB family + bit-plane)."""
```

Create `src/stegolab/image/io_image.py`:

```python
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
    Image.fromarray(np.asarray(arr, dtype=np.uint8), "RGB").save(p)


def resize_to(arr: np.ndarray, size_wh: tuple[int, int], mode: str) -> np.ndarray:
    w, h = size_wh
    if mode == "reject":
        if arr.shape[1] != w or arr.shape[0] != h:
            raise UnsupportedFileType(
                f"hidden image {arr.shape[1]}x{arr.shape[0]} != cover {w}x{h} and resize_mode=reject"
            )
        return arr
    img = Image.fromarray(arr, "RGB")
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/image/test_io_image.py -v`
Expected: PASS (8 passed).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/stegolab/image/__init__.py src/stegolab/image/io_image.py tests/image/test_io_image.py
git commit -m "feat(image): PNG/BMP image I/O and resize helpers"
```

---

### Task 3: `image/lsb.py` — shared embed/extract engine + `image-lsb`

**Files:**
- Create: `src/stegolab/image/lsb.py`
- Test: `tests/image/test_lsb.py`

**Interfaces:**
- Consumes: `core.{bitstream, payload_codec, frame, capacity, io}`, `core.errors.{CapacityExceeded}`, `core.types.{PayloadType, CapacityReport}`, `image.io_image`.
- Produces (used by Tasks 4 & 5):
  - `payload_type_for_mime(mime: str) -> PayloadType` — `text/*`→TEXT, `image/*`→IMAGE, else BYTES.
  - `embed_bits_in_order(flat: np.ndarray, order: np.ndarray, frame_bits: np.ndarray, bpc: int) -> None` — in place; raises `CapacityExceeded` if `ceil(len(frame_bits)/bpc) > len(order)`.
  - `read_bits_in_order(flat: np.ndarray, order: np.ndarray, bpc: int) -> np.ndarray` — reads `bpc` LSBs per slot in `order`, returns MSB-first bit array of length `len(order)*bpc`.
  - `recover_frame(flat, order, bpc) -> bytes` — reads all slot bits, truncates to a byte multiple.
  - `build_framed_payload(payload_path, compress) -> bytes` — read+frame a payload file.
  - `capacity`/`hide`/`extract` per the Method Interface Contract for `image-lsb` (order = `np.arange(n_slots)`).

- [ ] **Step 1: Write the failing test**

Create `tests/image/test_lsb.py`:

```python
import numpy as np
import pytest
from PIL import Image

from stegolab.core import errors
from stegolab.image import io_image, lsb


def _cover(tmp_path, w=64, h=64, seed=0):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    p = tmp_path / "cover.png"
    Image.fromarray(arr, "RGB").save(p)
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
    Image.fromarray(np.full((6, 6, 3), 99, np.uint8), "RGB").save(icon)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/image/test_lsb.py -v`
Expected: FAIL — `ImportError: cannot import name 'lsb'` (module missing).

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/image/lsb.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/image/test_lsb.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/image/lsb.py tests/image/test_lsb.py
git commit -m "feat(image): LSB embed/extract engine and image-lsb method"
```

---

### Task 4: `image/randomized_lsb.py` — keyed-permutation LSB

**Files:**
- Create: `src/stegolab/image/randomized_lsb.py`
- Test: `tests/image/test_randomized_lsb.py`

**Interfaces:**
- Consumes: `image.lsb` (engine), `core.keys.permutation`, `core.{frame, payload_codec, capacity, io, bitstream}`, `core.errors.{InvalidArguments, IntegrityCheckFailed, CorruptedPayload, NoPayloadFound}`.
- Produces: `capacity`/`hide`/`extract` for `image-randomized-lsb`. Order = `core.permutation(n_slots, key)`. Requires `params["key"]` unless `params["allow_unkeyed"]` is True (then order = sequential, with the same result as `image-lsb`).

- [ ] **Step 1: Write the failing test**

Create `tests/image/test_randomized_lsb.py`:

```python
import numpy as np
import pytest
from PIL import Image

from stegolab.core import errors
from stegolab.image import randomized_lsb as rlsb


def _cover(tmp_path, w=64, h=64, seed=1):
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8), "RGB").save(tmp_path / "c.png")
    return tmp_path / "c.png"


def _payload(tmp_path, data=b"keyed secret payload here"):
    (tmp_path / "p.txt").write_bytes(data)
    return tmp_path / "p.txt"


def test_same_key_round_trip(tmp_path):
    cover, payload = _cover(tmp_path), _payload(tmp_path)
    out, rec = tmp_path / "s.png", tmp_path / "r.txt"
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"key": "course-demo"})
    rlsb.extract(stego=str(out), out=str(rec), overwrite=False, params={"key": "course-demo"})
    assert rec.read_bytes() == b"keyed secret payload here"


def test_wrong_key_fails(tmp_path):
    cover, payload = _cover(tmp_path), _payload(tmp_path)
    out, rec = tmp_path / "s.png", tmp_path / "r.txt"
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"key": "right"})
    with pytest.raises((errors.IntegrityCheckFailed, errors.CorruptedPayload, errors.NoPayloadFound)):
        rlsb.extract(stego=str(out), out=str(rec), overwrite=False, params={"key": "wrong"})


def test_deterministic_output(tmp_path):
    cover, payload = _cover(tmp_path), _payload(tmp_path)
    o1, o2 = tmp_path / "s1.png", tmp_path / "s2.png"
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(o1), overwrite=False, params={"key": "k"})
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(o2), overwrite=False, params={"key": "k"})
    assert o1.read_bytes() == o2.read_bytes()


def test_requires_key_unless_allow_unkeyed(tmp_path):
    cover, payload = _cover(tmp_path), _payload(tmp_path)
    out = tmp_path / "s.png"
    with pytest.raises(errors.InvalidArguments):
        rlsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    # allow_unkeyed succeeds
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"allow_unkeyed": True})
    assert out.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/image/test_randomized_lsb.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/image/randomized_lsb.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/image/test_randomized_lsb.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/image/randomized_lsb.py tests/image/test_randomized_lsb.py
git commit -m "feat(image): keyed-permutation image-randomized-lsb"
```

---

### Task 5: `image/edge_adaptive_lsb.py` — activity-ordered LSB

**Files:**
- Create: `src/stegolab/image/edge_adaptive_lsb.py`
- Test: `tests/image/test_edge_adaptive_lsb.py`

**Interfaces:**
- Consumes: `image.lsb` (engine), `core.{frame, payload_codec, capacity, io, bitstream}`.
- Produces:
  - `activity_map(arr: np.ndarray, bpc: int) -> np.ndarray` — `HxW` float gradient magnitude computed from bit planes ≥ `bpc` (low `bpc` bits masked off), so it is identical for cover and single-/multi-LSB stego.
  - `slot_order(arr: np.ndarray, bpc: int) -> np.ndarray` — slot indices sorted by descending pixel activity (stable; ties broken by slot index). Identical on cover and stego.
  - `capacity`/`hide`/`extract` for `image-edge-adaptive-lsb`. Embedding fills the activity-descending prefix; extraction recomputes the identical order.

- [ ] **Step 1: Write the failing test**

Create `tests/image/test_edge_adaptive_lsb.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/image/test_edge_adaptive_lsb.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/image/edge_adaptive_lsb.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/image/test_edge_adaptive_lsb.py -v`
Expected: PASS (6 passed: 3 parametrized + 3).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/image/edge_adaptive_lsb.py tests/image/test_edge_adaptive_lsb.py
git commit -m "feat(image): edge-adaptive LSB with deterministic activity ordering"
```

---

### Task 6: `image/bitplane_image.py` — image-in-image visual demo

**Files:**
- Create: `src/stegolab/image/bitplane_image.py`
- Test: `tests/image/test_bitplane.py`

**Interfaces:**
- Consumes: `image.io_image`, `core.capacity`.
- Produces: `capacity`/`hide`/`extract` for `image-bitplane`. `hide` takes the hidden image as `payload`; the hidden image is resized to the cover size per `resize_mode`; the top `hidden_msb_bits` of the hidden image are stored in the low `cover_lsb_bits` of the cover. `extract` reconstructs a cover-sized approximate image. Not byte-exact (visual reconstruction).

- [ ] **Step 1: Write the failing test**

Create `tests/image/test_bitplane.py`:

```python
import numpy as np
import pytest
from PIL import Image

from stegolab.image import bitplane_image as bp, io_image


def _png(path, arr):
    Image.fromarray(arr.astype(np.uint8), "RGB").save(path)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/image/test_bitplane.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/image/bitplane_image.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/image/test_bitplane.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/image/bitplane_image.py tests/image/test_bitplane.py
git commit -m "feat(image): image-bitplane visual image-in-image demo"
```

---

### Task 7: `cli.py` — `stegolab` CLI (hide/extract/capacity)

**Files:**
- Modify: `pyproject.toml` (add `typer`, `[project.scripts]`)
- Create: `src/stegolab/cli.py`
- Test: `tests/cli/test_cli_image.py`

**Interfaces:**
- Consumes: Typer, the four image method modules, `core.errors.StegoLabError`.
- Produces: a Typer `app` with `hide`, `extract`, `capacity` commands dispatching by `--method` through a `METHODS` registry `{id: module}`. On `StegoLabError`, print the message (text or `--json` envelope) and exit with `exc.exit_code`. `--json` emits `{"ok", "command", "method", "result", "error"}` (spec §10.9). `main()` is the console-script entry point.

- [ ] **Step 1: Add Typer dependency and console script**

In `pyproject.toml`, add `"typer>=0.12"` to `dependencies`, and add this section:

```toml
[project.scripts]
stegolab = "stegolab.cli:main"
```

- [ ] **Step 2: Write the failing test**

Create `tests/cli/test_cli_image.py`:

```python
import json

import numpy as np
from PIL import Image
from typer.testing import CliRunner

from stegolab.cli import app

runner = CliRunner()


def _cover(tmp_path, w=64, h=64, seed=7):
    rng = np.random.default_rng(seed)
    p = tmp_path / "cover.png"
    Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8), "RGB").save(p)
    return p


def test_hide_then_extract_cli(tmp_path):
    cover = _cover(tmp_path)
    payload = tmp_path / "secret.txt"
    payload.write_bytes(b"cli round trip works")
    stego, rec = tmp_path / "stego.png", tmp_path / "rec.txt"

    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "image-lsb"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["extract", "--stego", str(stego), "--out", str(rec),
                            "--method", "image-lsb"])
    assert r.exit_code == 0, r.output
    assert rec.read_bytes() == b"cli round trip works"


def test_capacity_json(tmp_path):
    cover = _cover(tmp_path, 100, 100)
    r = runner.invoke(app, ["capacity", "--cover", str(cover), "--method", "image-lsb", "--json"])
    assert r.exit_code == 0
    payload = json.loads(r.output)
    assert payload["ok"] is True
    assert payload["command"] == "capacity"
    assert payload["result"]["total_bits"] == 100 * 100 * 3


def test_unknown_method_exit_5(tmp_path):
    cover = _cover(tmp_path)
    r = runner.invoke(app, ["capacity", "--cover", str(cover), "--method", "nope"])
    assert r.exit_code == 5


def test_capacity_exceeded_exit_3(tmp_path):
    cover = _cover(tmp_path, 8, 8)
    payload = tmp_path / "big.txt"
    payload.write_bytes(b"x" * 1000)
    stego = tmp_path / "s.png"
    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "image-lsb"])
    assert r.exit_code == 3
    assert not stego.exists()


def test_overwrite_guard_exit_7(tmp_path):
    cover = _cover(tmp_path)
    payload = tmp_path / "s.txt"
    payload.write_bytes(b"hello")
    stego = tmp_path / "stego.png"
    stego.write_bytes(b"existing")
    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "image-lsb"])
    assert r.exit_code == 7
    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "image-lsb", "--overwrite"])
    assert r.exit_code == 0


def test_randomized_requires_key_exit_2(tmp_path):
    cover = _cover(tmp_path)
    payload = tmp_path / "s.txt"
    payload.write_bytes(b"hello")
    stego = tmp_path / "s.png"
    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "image-randomized-lsb"])
    assert r.exit_code == 2  # InvalidArguments


def test_capacity_accepts_method_options(tmp_path):
    # §10.4: capacity must accept the same method-specific options as hide.
    cover = _cover(tmp_path, 32, 32)
    r = runner.invoke(app, ["capacity", "--cover", str(cover),
                            "--method", "image-randomized-lsb", "--key", "k"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["capacity", "--cover", str(cover),
                            "--method", "image-edge-adaptive-lsb", "--activity", "gradient"])
    assert r.exit_code == 0, r.output
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_cli_image.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.cli'`.

- [ ] **Step 4: Write minimal implementation**

Create `src/stegolab/cli.py`:

```python
"""stegolab CLI: hide / extract / capacity for the image methods (spec §10)."""

from __future__ import annotations

import dataclasses
import json as _json

import typer

from .core.errors import StegoLabError, UnsupportedMethod
from .image import bitplane_image, edge_adaptive_lsb, lsb, randomized_lsb

app = typer.Typer(add_completion=False, help="StegoLab: educational steganography CLI.")

METHODS = {
    "image-lsb": lsb,
    "image-randomized-lsb": randomized_lsb,
    "image-edge-adaptive-lsb": edge_adaptive_lsb,
    "image-bitplane": bitplane_image,
}


def _resolve(method: str):
    if method not in METHODS:
        raise UnsupportedMethod(f"unknown method: {method}")
    return METHODS[method]


def _params(**kw) -> dict:
    return {k: v for k, v in kw.items() if v is not None}


def _emit(command: str, method: str, result, json_out: bool) -> None:
    if isinstance(result, object) and dataclasses.is_dataclass(result):
        result = dataclasses.asdict(result)
    if json_out:
        typer.echo(_json.dumps({"ok": True, "command": command, "method": method, "result": result, "error": None}))
    else:
        typer.echo(f"{command} ok [{method}]: {result}")


def _fail(command: str, method: str, exc: StegoLabError, json_out: bool) -> None:
    if json_out:
        typer.echo(_json.dumps({
            "ok": False, "command": command, "method": method, "result": None,
            "error": {"type": type(exc).__name__, "exit_code": exc.exit_code, "message": str(exc)},
        }))
    else:
        typer.echo(f"error [{type(exc).__name__}]: {exc}", err=True)
    raise typer.Exit(code=exc.exit_code)


@app.command()
def hide(
    payload: str = typer.Option(..., "--payload"),
    cover: str = typer.Option(..., "--cover"),
    out: str = typer.Option(..., "--out"),
    method: str = typer.Option(..., "--method"),
    bits_per_channel: int = typer.Option(1, "--bits-per-channel"),
    channels: str = typer.Option("rgb", "--channels"),
    key: str = typer.Option(None, "--key"),
    allow_unkeyed: bool = typer.Option(False, "--allow-unkeyed"),
    activity: str = typer.Option("gradient", "--activity"),
    threshold_mode: str = typer.Option("auto", "--threshold-mode"),
    hidden_msb_bits: int = typer.Option(4, "--hidden-msb-bits"),
    cover_lsb_bits: int = typer.Option(4, "--cover-lsb-bits"),
    resize_mode: str = typer.Option("fit", "--resize-mode"),
    compress: str = typer.Option("auto", "--compress"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    json_out: bool = typer.Option(False, "--json"),
):
    try:
        mod = _resolve(method)
        result = mod.hide(cover=cover, payload=payload, out=out, overwrite=overwrite,
                          params=_params(bits_per_channel=bits_per_channel, key=key,
                                         allow_unkeyed=allow_unkeyed, activity=activity,
                                         threshold_mode=threshold_mode, hidden_msb_bits=hidden_msb_bits,
                                         cover_lsb_bits=cover_lsb_bits, resize_mode=resize_mode, compress=compress))
        _emit("hide", method, result, json_out)
    except StegoLabError as exc:
        _fail("hide", method, exc, json_out)


@app.command()
def extract(
    stego: str = typer.Option(..., "--stego"),
    out: str = typer.Option(..., "--out"),
    method: str = typer.Option(..., "--method"),
    bits_per_channel: int = typer.Option(1, "--bits-per-channel"),
    key: str = typer.Option(None, "--key"),
    allow_unkeyed: bool = typer.Option(False, "--allow-unkeyed"),
    hidden_msb_bits: int = typer.Option(4, "--hidden-msb-bits"),
    cover_lsb_bits: int = typer.Option(4, "--cover-lsb-bits"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    json_out: bool = typer.Option(False, "--json"),
):
    try:
        mod = _resolve(method)
        result = mod.extract(stego=stego, out=out, overwrite=overwrite,
                            params=_params(bits_per_channel=bits_per_channel, key=key,
                                           allow_unkeyed=allow_unkeyed, hidden_msb_bits=hidden_msb_bits,
                                           cover_lsb_bits=cover_lsb_bits))
        _emit("extract", method, result, json_out)
    except StegoLabError as exc:
        _fail("extract", method, exc, json_out)


@app.command()
def capacity(
    cover: str = typer.Option(..., "--cover"),
    method: str = typer.Option(..., "--method"),
    bits_per_channel: int = typer.Option(1, "--bits-per-channel"),
    channels: str = typer.Option("rgb", "--channels"),
    key: str = typer.Option(None, "--key"),
    allow_unkeyed: bool = typer.Option(False, "--allow-unkeyed"),
    activity: str = typer.Option("gradient", "--activity"),
    threshold_mode: str = typer.Option("auto", "--threshold-mode"),
    hidden_msb_bits: int = typer.Option(4, "--hidden-msb-bits"),
    cover_lsb_bits: int = typer.Option(4, "--cover-lsb-bits"),
    compress: str = typer.Option("auto", "--compress"),
    resize_mode: str = typer.Option("fit", "--resize-mode"),
    json_out: bool = typer.Option(False, "--json"),
):
    # §10.4: capacity accepts the same method-specific options as hide; each method's
    # capacity() reads only the keys it needs and ignores the rest.
    try:
        mod = _resolve(method)
        result = mod.capacity(cover=cover, params=_params(
            bits_per_channel=bits_per_channel, channels=channels, key=key,
            allow_unkeyed=allow_unkeyed, activity=activity, threshold_mode=threshold_mode,
            hidden_msb_bits=hidden_msb_bits, cover_lsb_bits=cover_lsb_bits,
            compress=compress, resize_mode=resize_mode))
        _emit("capacity", method, result, json_out)
    except StegoLabError as exc:
        _fail("capacity", method, exc, json_out)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/cli/test_cli_image.py -v`
Expected: PASS (7 passed). (Typer's `CliRunner` maps `typer.Exit(code=N)` to `result.exit_code`.)

- [ ] **Step 6: Run the FULL suite**

Run: `python -m pytest -q`
Expected: PASS — Plan 01 (52) + Task 1 (4) + Task 2 (8) + Task 3 (6) + Task 4 (4) + Task 5 (6) + Task 6 (3) + Task 7 (7) = **90 passed**.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/stegolab/cli.py tests/cli/test_cli_image.py
git commit -m "feat(cli): stegolab hide/extract/capacity for image methods"
```

---

## Self-Review

**1. Spec coverage (Plan 02 scope = M2–M4 + part of M6):**
- `image-lsb` (§9.1): Task 3 — sequential order, multi-bit, capacity formula `W×H×3×bpc`, capacity-exceeded-before-write. ✓
- `image-randomized-lsb` (§9.2): Task 4 — keyed permutation via `core.permutation`, key-required-unless-`allow_unkeyed`, deterministic, wrong-key fails. ✓
- `image-edge-adaptive-lsb` (§9.3): Task 5 — activity from planes ≥ bpc (determinism test), activity-descending order, round-trip across bpc 1/2/4, and capacity capped at the median floor so `capacity` and `hide` agree (CapacityExceeded-at-floor test). ✓
- `image-bitplane` (§9.4): Task 6 — visual image-in-image, cover-sized recovery, top-bits survive, cover high bits preserved, explicitly non-exact. ✓
- CLI `hide`/`extract`/`capacity` (§10.2–10.4, §10.8 exit codes, §10.9 JSON): Task 7. ✓
- Frame/integrity/compression/keys reused from `core` (Plan 01); extraction validates checksum via `decode_payload`. ✓
- Deferred to later plans by design: `analyze`/`attack`/`demo` subcommands (Plan 06/03), text methods (Plan 03+), BMP cover round-trip beyond load (Phase 2). Accepted-but-ignored in the MVP (flags parsed, defaults honored): `--channels` (RGB-only), and edge-adaptive `--activity` (gradient-only) and `--threshold-mode` (median floor only).

**2. Placeholder scan:** No `TBD`/`TODO`/"handle errors"/vague steps — every code step has complete code and every test step has real assertions. ✓

**3. Type consistency:** All method modules implement the uniform `capacity(*, cover, params)`, `hide(*, cover, payload, out, overwrite, params)`, `extract(*, stego, out, overwrite, params)` contract; the CLI `METHODS` registry dispatches to them identically. `embed_bits_in_order`/`read_bits_in_order`/`recover_frame`/`build_framed_payload`/`payload_type_for_mime`/`_validate_bpc` are defined in `lsb.py` (Task 3) and imported by Tasks 4–5 with matching signatures. `core` symbols used (`encode_payload`, `decode_payload`, `parse_frame`, `permutation`, `build_capacity_report`, `nominal_overhead`, `bytes_to_bits`, `bits_to_bytes`, `io.{read_bytes,write_bytes,detect_mime,sanitize_filename}`) all exist in Plan 01 + Task 1. ✓

> **Note for reviewers:** Tasks 4 and 5 reach into `lsb._validate_bpc` (a leading-underscore helper). This is deliberate intra-package reuse to keep bpc validation DRY; if preferred, promote it to a public `validate_bpc` in a follow-up. Flagged so it isn't mistaken for an accidental private-API leak.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-28-stegolab-02-image-methods-and-cli.md`. This is Plan 02 of 08; it produces the first end-to-end working `stegolab hide/extract/capacity` for images. Two execution options:

**1. Subagent-Driven (recommended)** — fresh implementer per task, review between tasks.

**2. Inline Execution** — batch execution with checkpoints.
