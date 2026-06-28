# StegoLab Zero-Width Text + CLI `analyze` Implementation Plan (Plan 03 of 08)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `text-zero-width` steganography method (hide text/bytes inside ordinary-looking UTF-8 cover text using invisible Unicode characters), wire it into the existing `stegolab` CLI, and add the `analyze` subcommand with text comparison metrics.

**Architecture:** Builds on `stegolab.core` (Plan 01) and reuses the uniform method-interface contract and CLI `METHODS` registry from Plan 02. `text/zero_width.py` frames the payload (same `core` frame + `bitstream`), maps bit-pairs to a configured alphabet of true zero-width characters, and distributes them across word-boundary slots in document order — so extraction is position-independent (collect the alphabet characters in document order, decode, validate the frame checksum). A new `eval/text_metrics.py` provides codepoint/zero-width/diff/normalization metrics, surfaced by a new `analyze` CLI command.

**Tech Stack:** Python 3.11+, NumPy, Typer, pytest. Reuses `stegolab.core` and the Plan 02 CLI.

## Global Constraints

Copied verbatim from `stegolab_engineering_spec.md` and the prior plans. Every task inherits these.

- **Python 3.11+; reuse `stegolab.core`** — framing, compression, hashing, capacity overhead, and bit conversion come from `core` (`encode_payload`, `decode_payload`, `parse_frame`, `bytes_to_bits`, `bits_to_bytes`, `frame_overhead_bytes`, `nominal_overhead`, `build_capacity_report`, `io.{read_bytes,write_bytes,detect_mime,sanitize_filename}`, `errors`, `types`). Do NOT reimplement them.
- **Uniform method interface** (from Plan 02): each method module exposes `capacity(*, cover, params) -> CapacityReport`, `hide(*, cover, payload, out, overwrite, params) -> dict`, `extract(*, stego, out, overwrite, params) -> dict`. The CLI `METHODS` registry dispatches by method id.
- **Bit order is MSB-first**, consistent with `core.bitstream` and the within-symbol bit packing.
- **Default alphabet** (`text-zero-width`, 2 bits/symbol, true zero-width characters only): `00`→`U+200C` (ZWNJ), `01`→`U+200D` (ZWJ), `10`→`U+200B` (ZWSP), `11`→`U+FEFF` (ZWNBSP/BOM). A `minimal` alphabet uses 1 bit/symbol: `0`→`U+200C`, `1`→`U+200D`. Alphabet size must be a power of two (spec §9.5).
- **Capacity formula:** `capacity_bits = eligible_slots × bits_per_symbol × max_density`; `capacity_bytes = floor(capacity_bits/8) − frame_overhead_bytes` (spec §9.5). Eligible slots = word-boundary positions (after each space). `max_density` default `4` (up to 4 invisible chars per gap).
- **Exactness:** extraction recovers the exact payload bytes and validates the frame checksum (`IntegrityCheckFailed` on mismatch). Visible text is preserved exactly except for the inserted invisible characters (spec §9.5).
- **Fragility (accurate):** standard Unicode NFC/NFKC normalization does NOT remove these default zero-width characters (they have no decomposition); what breaks the payload is *explicit stripping* of the code points (or platform-specific filters). The teaching demonstration and the `normalization` metric reflect this honestly — survival under NFC/NFKC is reported as-is, and the breaking attack is a strip.
- **Cover validation:** cover must be valid UTF-8 and must not already contain the chosen alphabet's characters (else `InvalidArguments`).
- **File safety / exit codes:** unchanged from prior plans (`OutputExists`=7 via `core.io.write_bytes`; `CapacityExceeded`=3; `InvalidArguments`=2; `IntegrityCheckFailed`/`CorruptedPayload`/`NoPayloadFound`=4; `UnsupportedMethod`=5). `analyze` uses the §10.9 `--json` envelope.

## File Structure

- `src/stegolab/text/__init__.py` (NEW) — text package marker.
- `src/stegolab/text/zero_width.py` (NEW) — the `text-zero-width` method.
- `src/stegolab/eval/__init__.py` (NEW) — eval package marker.
- `src/stegolab/eval/text_metrics.py` (NEW) — text comparison metrics.
- `src/stegolab/cli.py` — register `text-zero-width` in `METHODS`; add text options to `hide`/`extract`/`capacity`; add the `analyze` command.
- `tests/text/test_zero_width.py`, `tests/eval/test_text_metrics.py`, `tests/cli/test_cli_text.py`, `tests/cli/test_cli_analyze.py`.

---

### Task 1: `text/zero_width.py` — the `text-zero-width` method

**Files:**
- Create: `src/stegolab/text/__init__.py`
- Create: `src/stegolab/text/zero_width.py`
- Test: `tests/text/test_zero_width.py`

**Interfaces:**
- Consumes: `core.{bitstream, payload_codec, frame, capacity, io}`, `core.errors.{CapacityExceeded, InvalidArguments}`, `core.types.{PayloadType, CapacityReport}`.
- Produces: module-level `DEFAULT_ALPHABET` (imported by metrics/tests); `capacity`/`hide`/`extract` per the uniform contract for `text-zero-width`; internal helpers `alphabet_for(params)`, `bits_per_symbol(alphabet)`, `eligible_slots(cover_text)` (used internally by capacity/hide/extract).

- [ ] **Step 1: Write the failing test**

Create `tests/text/test_zero_width.py`:

```python
import pytest

from stegolab.core import errors
from stegolab.text import zero_width as zw

COVER = " ".join(f"word{i}" for i in range(600))  # 599 word-boundary slots


def _write(tmp_path, name, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def _cover(tmp_path, text=COVER):
    return _write(tmp_path, "cover.txt", text.encode("utf-8"))


def test_text_round_trip(tmp_path):
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "secret.txt", b"meet at midnight")
    out, rec = tmp_path / "stego.txt", tmp_path / "rec.txt"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    summary = zw.extract(stego=str(out), out=str(rec), overwrite=False, params={})
    assert rec.read_bytes() == b"meet at midnight"
    assert summary["integrity"] == "ok"


def test_visible_text_preserved(tmp_path):
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "s.txt", b"hi")
    out = tmp_path / "stego.txt"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    stego = out.read_bytes().decode("utf-8")
    stripped = "".join(ch for ch in stego if ch not in zw.DEFAULT_ALPHABET)
    assert stripped == COVER  # only invisible chars were added


def test_bytes_payload_round_trip(tmp_path):
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "blob.bin", bytes(range(40)))
    out, rec = tmp_path / "stego.txt", tmp_path / "rec.bin"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    zw.extract(stego=str(out), out=str(rec), overwrite=False, params={})
    assert rec.read_bytes() == bytes(range(40))


def test_capacity_report(tmp_path):
    cover = _cover(tmp_path)
    rep = zw.capacity(cover=str(cover), params={})
    assert rep.total_bits == 599 * 2 * 4  # slots × bits_per_symbol × max_density
    assert rep.usable_bytes == rep.total_bytes - rep.overhead_bytes


def test_capacity_exceeded_non_destructive(tmp_path):
    cover = _cover(tmp_path, "one two three")  # 2 slots only
    payload = _write(tmp_path, "big.txt", b"x" * 500)
    out = tmp_path / "stego.txt"
    with pytest.raises(errors.CapacityExceeded):
        zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    assert not out.exists()


def test_cover_with_alphabet_chars_rejected(tmp_path):
    bad = _write(tmp_path, "bad.txt", ("hello\u200cworld " * 50).encode("utf-8"))
    payload = _write(tmp_path, "s.txt", b"hi")
    out = tmp_path / "stego.txt"
    with pytest.raises(errors.InvalidArguments):
        zw.hide(cover=str(bad), payload=str(payload), out=str(out), overwrite=False, params={})


def test_strip_zero_width_breaks_extraction(tmp_path):
    # The honest fragility demo: stripping the invisible chars destroys the payload.
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "s.txt", b"top secret")
    out, rec = tmp_path / "stego.txt", tmp_path / "rec.txt"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    stego = out.read_bytes().decode("utf-8")
    stripped = "".join(ch for ch in stego if ch not in zw.DEFAULT_ALPHABET)
    attacked = tmp_path / "attacked.txt"
    attacked.write_bytes(stripped.encode("utf-8"))
    with pytest.raises((errors.NoPayloadFound, errors.CorruptedPayload, errors.IntegrityCheckFailed)):
        zw.extract(stego=str(attacked), out=str(rec), overwrite=False, params={})


def test_minimal_alphabet_round_trip(tmp_path):
    cover = _cover(tmp_path)
    payload = _write(tmp_path, "s.txt", b"abc")
    out, rec = tmp_path / "stego.txt", tmp_path / "rec.txt"
    zw.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"alphabet": "minimal"})
    zw.extract(stego=str(out), out=str(rec), overwrite=False, params={"alphabet": "minimal"})
    assert rec.read_bytes() == b"abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/text/test_zero_width.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.text'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/text/__init__.py`:

```python
"""Text steganography methods."""
```

Create `src/stegolab/text/zero_width.py`:

```python
"""text-zero-width: hide a framed payload in invisible Unicode characters (spec §9.5).

Bits → symbols (one alphabet char per `bits_per_symbol` bits, MSB-first) → distributed
across word-boundary slots as contiguous blocks (so document order == symbol order).
Extraction is position-independent: collect the alphabet's characters in document order,
decode, and validate the frame checksum. Visible text is preserved exactly.
"""

from __future__ import annotations

import numpy as np

from ..core import bitstream, capacity as cap, frame as frame_mod, io as core_io, payload_codec
from ..core.errors import CapacityExceeded, InvalidArguments
from ..core.types import CapacityReport, PayloadType

DEFAULT_ALPHABET = ["\u200c", "\u200d", "\u200b", "\ufeff"]  # 00,01,10,11
MINIMAL_ALPHABET = ["\u200c", "\u200d"]                       # 0,1


def alphabet_for(params: dict) -> list[str]:
    name = params.get("alphabet") or "default"
    if name == "default":
        return DEFAULT_ALPHABET
    if name == "minimal":
        return MINIMAL_ALPHABET
    raise InvalidArguments(f"unknown alphabet: {name}")


def bits_per_symbol(alphabet: list[str]) -> int:
    n = len(alphabet)
    bps = n.bit_length() - 1
    if (1 << bps) != n or bps < 1:
        raise InvalidArguments("alphabet size must be a power of two >= 2")
    return bps


def eligible_slots(cover_text: str) -> list[int]:
    """Insertion positions: the index just after each space (word boundary)."""
    return [i + 1 for i, ch in enumerate(cover_text) if ch == " "]


def _read_text(path) -> str:
    try:
        return core_io.read_bytes(path).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidArguments("cover/stego text is not valid UTF-8") from exc


def _payload_type_for_mime(mime: str) -> PayloadType:
    if mime.startswith("text/"):
        return PayloadType.TEXT
    if mime.startswith("image/"):
        return PayloadType.IMAGE
    return PayloadType.BYTES


def _frame_file(payload_path: str, compress: str) -> bytes:
    raw = core_io.read_bytes(payload_path)
    mime = core_io.detect_mime(payload_path)
    return payload_codec.encode_payload(
        raw=raw, payload_type=_payload_type_for_mime(mime),
        original_filename=core_io.sanitize_filename(str(payload_path)),
        mime_type=mime, compression=compress,
    )


def _max_density(params: dict) -> int:
    d = int(params.get("max_density", 4))
    if d < 1:
        raise InvalidArguments("max_density must be >= 1")
    return d


def capacity(*, cover: str, params: dict) -> CapacityReport:
    alphabet = alphabet_for(params)
    bps = bits_per_symbol(alphabet)
    density = _max_density(params)
    slots = eligible_slots(_read_text(cover))
    total_bits = len(slots) * bps * density
    return cap.build_capacity_report(
        total_bits, cap.nominal_overhead(), is_estimate=True,
        assumptions=f"text-zero-width bits_per_symbol={bps}, max_density={density}; eligible slots = word boundaries",
    )


def hide(*, cover: str, payload: str, out: str, overwrite: bool, params: dict) -> dict:
    alphabet = alphabet_for(params)
    bps = bits_per_symbol(alphabet)
    density = _max_density(params)
    cover_text = _read_text(cover)
    if any(ch in cover_text for ch in alphabet):
        raise InvalidArguments("cover already contains alphabet characters; choose another cover or alphabet")

    framed = _frame_file(payload, params.get("compress", "auto"))
    bits = bitstream.bytes_to_bits(framed)
    pad = (-len(bits)) % bps
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    groups = bits.reshape(-1, bps)
    weights = (1 << np.arange(bps - 1, -1, -1)).astype(np.int64)
    idxs = (groups * weights).sum(axis=1)
    chars = [alphabet[i] for i in idxs]

    slots = eligible_slots(cover_text)
    if len(chars) > len(slots) * density:
        raise CapacityExceeded(
            f"payload needs {len(chars)} symbols but cover holds {len(slots) * density}"
        )
    stego = _insert_blocks(cover_text, slots, chars)
    core_io.write_bytes(out, stego.encode("utf-8"), overwrite=overwrite)
    return {"method": "text-zero-width", "out": out, "symbols": len(chars), "bytes": len(framed),
            "params": {"alphabet": params.get("alphabet") or "default", "max_density": density}}


def _insert_blocks(cover_text: str, slots: list[int], chars: list[str]) -> str:
    """Distribute chars as contiguous blocks across slots (even split), preserving order."""
    s = len(slots)
    n = len(chars)
    base, rem = divmod(n, s)
    counts = [base + (1 if j < rem else 0) for j in range(s)]
    pieces = []
    prev = 0
    k = 0
    for pos, c in zip(slots, counts):
        pieces.append(cover_text[prev:pos])
        if c:
            pieces.append("".join(chars[k:k + c]))
            k += c
        prev = pos
    pieces.append(cover_text[prev:])
    return "".join(pieces)


def extract(*, stego: str, out: str, overwrite: bool, params: dict) -> dict:
    alphabet = alphabet_for(params)
    bps = bits_per_symbol(alphabet)
    stego_text = _read_text(stego)
    index_of = {ch: i for i, ch in enumerate(alphabet)}
    syms = np.array([index_of[ch] for ch in stego_text if ch in index_of], dtype=np.int64)
    if syms.size:
        shifts = np.arange(bps - 1, -1, -1)
        bits = ((syms[:, None] >> shifts) & 1).astype(np.uint8).reshape(-1)
    else:
        bits = np.zeros(0, dtype=np.uint8)
    usable = (bits.size // 8) * 8
    parsed = frame_mod.parse_frame(bitstream.bits_to_bytes(bits[:usable]))
    original = payload_codec.decode_payload(parsed)
    core_io.write_bytes(out, original, overwrite=overwrite)
    return {"method": "text-zero-width", "out": out, "bytes": len(original),
            "original_filename": parsed.original_filename, "mime_type": parsed.mime_type, "integrity": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/text/test_zero_width.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/text/__init__.py src/stegolab/text/zero_width.py tests/text/test_zero_width.py
git commit -m "feat(text): text-zero-width invisible-Unicode method"
```

---

### Task 2: CLI integration for `text-zero-width`

**Files:**
- Modify: `src/stegolab/cli.py`
- Test: `tests/cli/test_cli_text.py`

**Interfaces:**
- Consumes: `text.zero_width`.
- Produces: `text-zero-width` registered in `METHODS`; `hide` gains `--slot-policy`, `--max-density`, `--alphabet`; `extract` gains `--alphabet`; `capacity` gains `--alphabet`, `--max-density` (note: `capacity` already forwards `--compress` etc. from Plan 02). All forwarded via the existing `_params(...)` filter.

- [ ] **Step 1: Write the failing test**

Create `tests/cli/test_cli_text.py`:

```python
import json

from typer.testing import CliRunner

from stegolab.cli import app

runner = CliRunner()
COVER_TEXT = " ".join(f"word{i}" for i in range(600))


def _cover(tmp_path):
    p = tmp_path / "cover.txt"
    p.write_text(COVER_TEXT, encoding="utf-8")
    return p


def test_text_hide_extract_cli(tmp_path):
    cover = _cover(tmp_path)
    payload = tmp_path / "s.txt"
    payload.write_bytes(b"cli zero-width round trip")
    stego, rec = tmp_path / "stego.txt", tmp_path / "rec.txt"
    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "text-zero-width"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["extract", "--stego", str(stego), "--out", str(rec),
                            "--method", "text-zero-width"])
    assert r.exit_code == 0, r.output
    assert rec.read_bytes() == b"cli zero-width round trip"


def test_text_capacity_json(tmp_path):
    cover = _cover(tmp_path)
    r = runner.invoke(app, ["capacity", "--cover", str(cover), "--method", "text-zero-width", "--json"])
    assert r.exit_code == 0
    out = json.loads(r.output)
    assert out["ok"] is True
    assert out["result"]["total_bits"] == 599 * 2 * 4


def test_text_alphabet_option(tmp_path):
    cover = _cover(tmp_path)
    payload = tmp_path / "s.txt"
    payload.write_bytes(b"minimal")
    stego, rec = tmp_path / "stego.txt", tmp_path / "rec.txt"
    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "text-zero-width", "--alphabet", "minimal"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["extract", "--stego", str(stego), "--out", str(rec),
                            "--method", "text-zero-width", "--alphabet", "minimal"])
    assert r.exit_code == 0, r.output
    assert rec.read_bytes() == b"minimal"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_cli_text.py -v`
Expected: FAIL — `UnsupportedMethod`/unknown method `text-zero-width` (exit 5) on the hide call.

- [ ] **Step 3: Modify the CLI**

In `src/stegolab/cli.py`:

1. Add the import alongside the image imports:

```python
from .text import zero_width
```

2. Add the entry to the `METHODS` registry:

```python
    "text-zero-width": zero_width,
```

3. Add `--slot-policy`, `--max-density`, `--alphabet` options to the `hide` command signature (after the existing text-free options, before `compress`):

```python
    slot_policy: str = typer.Option("word-boundary", "--slot-policy"),
    max_density: int = typer.Option(4, "--max-density"),
    alphabet: str = typer.Option("default", "--alphabet"),
```

and add them to `hide`'s `_params(...)` call:

```python
                                         slot_policy=slot_policy, max_density=max_density, alphabet=alphabet,
```

4. Add `--alphabet` to the `extract` command signature and its `_params(...)` call:

```python
    alphabet: str = typer.Option("default", "--alphabet"),
```
```python
                                           alphabet=alphabet,
```

5. Add `--alphabet` and `--max-density` to the `capacity` command signature and its `_params(...)` call:

```python
    alphabet: str = typer.Option("default", "--alphabet"),
    max_density: int = typer.Option(4, "--max-density"),
```
```python
            alphabet=alphabet, max_density=max_density,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/cli/test_cli_text.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite (regression check)**

Run: `python -m pytest -q`
Expected: PASS — 90 (Plan 02) + 8 (Task 1) + 3 (Task 2) = **101 passed**.

- [ ] **Step 6: Commit**

```bash
git add src/stegolab/cli.py tests/cli/test_cli_text.py
git commit -m "feat(cli): register text-zero-width and its text options"
```

---

### Task 3: `eval/text_metrics.py` — text comparison metrics

**Files:**
- Create: `src/stegolab/eval/__init__.py`
- Create: `src/stegolab/eval/text_metrics.py`
- Test: `tests/eval/test_text_metrics.py`

**Interfaces:**
- Consumes: `unicodedata`, `text.zero_width.DEFAULT_ALPHABET`.
- Produces:
  - `zero_width_count(text, alphabet=DEFAULT_ALPHABET) -> int`.
  - `visible_text(text, alphabet=DEFAULT_ALPHABET) -> str` (text with alphabet chars removed) and `visible_equal(cover, stego, alphabet) -> bool`.
  - `unicode_category_summary(text) -> dict[str,int]`.
  - `normalization_survival(stego, alphabet=DEFAULT_ALPHABET) -> dict` — for `NFC` and `NFKC`, the zero-width count before/after and a `survives` bool (honest: these survive).
  - `analyze_text(cover, stego, metrics: list[str]) -> dict` — dispatch by metric name (`zero-width-count`, `visible-diff`, `codepoints`, `normalization`).

- [ ] **Step 1: Write the failing test**

Create `tests/eval/test_text_metrics.py`:

```python
from stegolab.eval import text_metrics as tm
from stegolab.text.zero_width import DEFAULT_ALPHABET

ZW = DEFAULT_ALPHABET[0]


def test_zero_width_count():
    assert tm.zero_width_count(f"a{ZW}b{ZW}{ZW}c") == 3
    assert tm.zero_width_count("plain text") == 0


def test_visible_text_and_equal():
    cover = "hello world"
    stego = f"hello{ZW} world{ZW}{ZW}"
    assert tm.visible_text(stego) == cover
    assert tm.visible_equal(cover, stego) is True
    assert tm.visible_equal(cover, "hello there") is False


def test_unicode_category_summary():
    summary = tm.unicode_category_summary(f"A1 {ZW}")
    assert summary.get("Lu", 0) == 1   # 'A'
    assert summary.get("Nd", 0) == 1   # '1'
    assert summary.get("Cf", 0) >= 1   # ZWNJ is a format char


def test_normalization_survival_reports_survival():
    stego = f"word{ZW}word{ZW}"
    result = tm.normalization_survival(stego)
    assert result["NFKC"]["before"] == 2
    # honest: NFKC does NOT strip default zero-width chars
    assert result["NFKC"]["after"] == 2
    assert result["NFKC"]["survives"] is True


def test_analyze_text_dispatch():
    cover = "alpha beta gamma"
    stego = f"alpha{ZW} beta{ZW} gamma"
    report = tm.analyze_text(cover, stego, ["zero-width-count", "visible-diff", "normalization"])
    assert report["zero-width-count"] == 2
    assert report["visible-diff"]["visible_equal"] is True
    assert report["normalization"]["NFC"]["survives"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/eval/test_text_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.eval'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/eval/__init__.py`:

```python
"""Evaluation: comparison metrics, steganalysis, attacks, and reports."""
```

Create `src/stegolab/eval/text_metrics.py`:

```python
"""Text cover/stego comparison metrics (spec §13.2)."""

from __future__ import annotations

import unicodedata
from collections import Counter

from ..text.zero_width import DEFAULT_ALPHABET


def zero_width_count(text: str, alphabet: list[str] = DEFAULT_ALPHABET) -> int:
    alset = set(alphabet)
    return sum(1 for ch in text if ch in alset)


def visible_text(text: str, alphabet: list[str] = DEFAULT_ALPHABET) -> str:
    alset = set(alphabet)
    return "".join(ch for ch in text if ch not in alset)


def visible_equal(cover: str, stego: str, alphabet: list[str] = DEFAULT_ALPHABET) -> bool:
    return visible_text(cover, alphabet) == visible_text(stego, alphabet)


def unicode_category_summary(text: str) -> dict:
    return dict(Counter(unicodedata.category(ch) for ch in text))


def normalization_survival(stego: str, alphabet: list[str] = DEFAULT_ALPHABET) -> dict:
    before = zero_width_count(stego, alphabet)
    out = {}
    for form in ("NFC", "NFKC"):
        after = zero_width_count(unicodedata.normalize(form, stego), alphabet)
        out[form] = {"before": before, "after": after, "survives": after == before}
    return out


def analyze_text(cover: str, stego: str, metrics: list[str], alphabet: list[str] = DEFAULT_ALPHABET) -> dict:
    report: dict = {}
    for metric in metrics:
        if metric == "zero-width-count":
            report[metric] = zero_width_count(stego, alphabet)
        elif metric == "visible-diff":
            report[metric] = {"visible_equal": visible_equal(cover, stego, alphabet)}
        elif metric == "codepoints":
            report[metric] = unicode_category_summary(stego)
        elif metric == "normalization":
            report[metric] = normalization_survival(stego, alphabet)
        else:
            report[metric] = {"error": f"unknown or unsupported metric in this phase: {metric}"}
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/eval/test_text_metrics.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/eval/__init__.py src/stegolab/eval/text_metrics.py tests/eval/test_text_metrics.py
git commit -m "feat(eval): text comparison metrics (codepoints, zero-width, normalization)"
```

---

### Task 4: `analyze` CLI command

**Files:**
- Modify: `src/stegolab/cli.py`
- Test: `tests/cli/test_cli_analyze.py`

**Interfaces:**
- Consumes: `eval.text_metrics`, `text.zero_width`.
- Produces: an `analyze` command — `--cover`, `--stego`, `--method`, `--metrics` (comma list, default `zero-width-count,visible-diff,codepoints,normalization`), `--json`. For text methods it runs `text_metrics.analyze_text`. For image methods it raises `UnsupportedMethod("image analysis metrics are added in a later phase")` (exit 5) — image metrics are Plan 06.

- [ ] **Step 1: Write the failing test**

Create `tests/cli/test_cli_analyze.py`:

```python
import json

from typer.testing import CliRunner

from stegolab.cli import app

runner = CliRunner()
COVER_TEXT = " ".join(f"word{i}" for i in range(600))


def _prep(tmp_path):
    cover = tmp_path / "cover.txt"
    cover.write_text(COVER_TEXT, encoding="utf-8")
    payload = tmp_path / "s.txt"
    payload.write_bytes(b"analyze me")
    stego = tmp_path / "stego.txt"
    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "text-zero-width"])
    assert r.exit_code == 0, r.output
    return cover, stego


def test_analyze_text_json(tmp_path):
    cover, stego = _prep(tmp_path)
    r = runner.invoke(app, ["analyze", "--cover", str(cover), "--stego", str(stego),
                            "--method", "text-zero-width",
                            "--metrics", "zero-width-count,visible-diff,normalization", "--json"])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["ok"] is True
    assert out["command"] == "analyze"
    assert out["result"]["zero-width-count"] > 0
    assert out["result"]["visible-diff"]["visible_equal"] is True
    assert out["result"]["normalization"]["NFKC"]["survives"] is True


def test_analyze_image_method_is_deferred(tmp_path):
    cover, stego = _prep(tmp_path)
    r = runner.invoke(app, ["analyze", "--cover", str(cover), "--stego", str(stego),
                            "--method", "image-lsb"])
    assert r.exit_code == 5  # UnsupportedMethod: image metrics are a later phase


def test_analyze_non_utf8_cover_exit_2(tmp_path):
    cover = tmp_path / "cover.bin"
    cover.write_bytes(b"\xff\xfe not valid utf-8")
    stego = tmp_path / "stego.txt"
    stego.write_text("hello world", encoding="utf-8")
    r = runner.invoke(app, ["analyze", "--cover", str(cover), "--stego", str(stego),
                            "--method", "text-zero-width"])
    assert r.exit_code == 2  # InvalidArguments from non-UTF-8 input, surfaced via the envelope
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_cli_analyze.py -v`
Expected: FAIL — no `analyze` command (Typer usage error / exit 2).

- [ ] **Step 3: Modify the CLI**

In `src/stegolab/cli.py`:

1. Add imports:

```python
from .eval import text_metrics
```

2. Define the set of text methods and add the `analyze` command (place after the `capacity` command, before `main`):

```python
_TEXT_METHODS = {"text-zero-width"}


@app.command()
def analyze(
    cover: str = typer.Option(..., "--cover"),
    stego: str = typer.Option(..., "--stego"),
    method: str = typer.Option(..., "--method"),
    metrics: str = typer.Option("zero-width-count,visible-diff,codepoints,normalization", "--metrics"),
    json_out: bool = typer.Option(False, "--json"),
):
    try:
        _resolve(method)  # validates the method id (UnsupportedMethod -> exit 5)
        if method not in _TEXT_METHODS:
            raise UnsupportedMethod("image analysis metrics are added in a later phase")
        from .text.zero_width import _read_text  # wraps non-UTF-8 as InvalidArguments (exit 2)
        cover_text = _read_text(cover)
        stego_text = _read_text(stego)
        result = text_metrics.analyze_text(cover_text, stego_text, [m for m in metrics.split(",") if m])
        _emit("analyze", method, result, json_out)
    except StegoLabError as exc:
        _fail("analyze", method, exc, json_out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/cli/test_cli_analyze.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the FULL suite**

Run: `python -m pytest -q`
Expected: PASS — 101 (after Task 2) + 5 (Task 3) + 3 (Task 4) = **109 passed**.

- [ ] **Step 6: Commit**

```bash
git add src/stegolab/cli.py tests/cli/test_cli_analyze.py
git commit -m "feat(cli): analyze command with text metrics"
```

---

## Self-Review

**1. Spec coverage (Plan 03 scope = M5 text-zero-width + part of M5/M10 analyze):**
- `text-zero-width` (§9.5): Task 1 — default + minimal alphabets, word-boundary slots, capacity formula, exact round-trip (text & bytes), visible-text preservation, cover validation, and the honest strip-fragility demo. ✓
- CLI `hide`/`extract`/`capacity` for text (§10.2–10.4): Task 2 — registered + text options, full-suite regression. ✓
- `analyze` (§10.5) + text metrics (§13.2): Tasks 3–4 — zero-width count, visible diff, codepoint/category summary, normalization survival (reported honestly), `--json` envelope. ✓
- Frame/integrity/compression reused from `core`; extraction validates checksum. ✓
- Deferred by design: keyed slot selection for zero-width (extraction is position-independent, so a key adds no security here — `--slot-policy` accepted, `word-boundary` only; `key` not used by this method); image `analyze` metrics (PSNR/SSIM/chi2/rs) and the `attack` command → Plan 06; `text-unicode-whitespace` → later. The honest NFC/NFKC-doesn't-strip caveat is documented in both the method and the metric.

**2. Placeholder scan:** No `TBD`/`TODO`/vague steps — complete code and real assertions throughout.

**3. Type consistency:** `text.zero_width` implements the uniform `capacity(*, cover, params)` / `hide(*, cover, payload, out, overwrite, params)` / `extract(*, stego, out, overwrite, params)` contract used by the CLI `METHODS` registry (Plan 02). `eval.text_metrics.analyze_text(cover, stego, metrics)` is called by the `analyze` command. `DEFAULT_ALPHABET` is defined in `text.zero_width` and imported by `eval.text_metrics`. `core` symbols used all exist (Plans 01–02). The `_emit`/`_fail`/`_resolve`/`_params` CLI helpers are reused unchanged.

> **Note for reviewers:** `text/zero_width.py` re-defines a small `_payload_type_for_mime` + `_frame_file` (mirroring `image/lsb.py`'s `payload_type_for_mime`/`build_framed_payload`). This duplication is deliberate to avoid a text→image package dependency; consolidating both into `core` is a reasonable follow-up but out of scope here. Flagged so it isn't mistaken for accidental drift.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-28-stegolab-03-zerowidth-text-and-analyze.md`. This is Plan 03 of 08; it adds the first text method and the `analyze` command. Two execution options:

**1. Subagent-Driven (recommended)** — fresh implementer per task, review between tasks.

**2. Inline Execution** — batch execution with checkpoints.
