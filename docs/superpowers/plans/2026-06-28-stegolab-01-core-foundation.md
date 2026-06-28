# StegoLab Core Foundation Implementation Plan (Plan 01 of 08)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `stegolab.core` package — the shared payload frame codec, payload encode/decode (compression + integrity), error taxonomy, key-seeded deterministic PRNG, capacity math, and safe file I/O — that every steganography method in later plans consumes.

**Architecture:** A dependency-light Python library under `src/stegolab/core/`. The heart is a self-describing binary frame (§8 of the spec): `encode_frame`/`parse_frame` produce and consume a big-endian wire format with a two-stage read (fixed prefix → header → payload). `payload_codec` wraps raw user bytes into a frame (compress, hash over the original bytes) and reverses it (decompress, verify SHA-256). All failures raise typed exceptions that map to CLI exit codes. No method-specific embedding logic lives here.

**Tech Stack:** Python 3.11+, NumPy (deterministic PRNG), pytest. Standard library `struct`, `hashlib`, `zlib`, `mimetypes`, `pathlib`. No PyTorch/Pillow needed in this plan.

## Global Constraints

Copied verbatim from `stegolab_engineering_spec.md`. Every task implicitly inherits these.

- **Python 3.11 or newer** (§18.1).
- **All multi-byte integers are big-endian / network order; strings are UTF-8** (§8.3).
- **Frame magic = `STEGOLAB` (8 ASCII bytes); frame version = `1`** (§8.2).
- **`sha256` is computed over the original decoded payload bytes (before compression/encryption)** (§8.3).
- **`frame_overhead_bytes = 11 (fixed prefix) + header_len`; the no-payload `capacity` estimate uses empty filename + MIME `application/octet-stream` → `79` bytes** (§8.3).
- **Compression in MVP: `none` and `zlib` only. `auto` = `zlib` for text-like/uncompressed payloads, `none` for already-compressed (PNG/JPEG/high-entropy) payloads. Compression happens before any encryption** (§8.5).
- **Frame parsing must fail closed on malformed headers, unsupported versions, invalid lengths, or checksum mismatch** (§8.4).
- **Deterministic PRNG: `seed = SHA-256(utf8(key))`, fed into NumPy `Generator(PCG64(...))` driving a Fisher–Yates permutation** (§8.6).
- **No absolute paths stored in the frame; no `pickle`/`eval`/untrusted deserialization** (§8.4).
- **File safety: never overwrite without an explicit overwrite flag; sanitize filenames to a basename; never write outside the requested output directory; avoid path traversal** (§20.2).
- **Secret handling: never print payload contents or include secret payloads in exception messages by default** (§20.3).
- **Error→exit-code mapping is fixed** (§15 / §10.8): `InvalidArguments`=2, `CapacityExceeded`=3, `NoPayloadFound`/`CorruptedPayload`/`IntegrityCheckFailed`/`WrongKey`=4, `UnsupportedFileType`/`UnsupportedMethod`=5, `MissingOptionalDependency`=6, `OutputExists`=7, generic=1.

## File Structure

- `pyproject.toml` — package metadata, Python floor, deps, pytest config.
- `src/stegolab/__init__.py` — package marker, version string.
- `src/stegolab/core/__init__.py` — re-exports the public core API.
- `src/stegolab/core/errors.py` — exception hierarchy with `exit_code` attributes.
- `src/stegolab/core/types.py` — enums (`PayloadType`, `Compression`, `Encryption`, `RecoveryClass`), `FrameFields`, `ParsedFrame`, `CapacityReport`, constants (`MAGIC`, `FRAME_VERSION`).
- `src/stegolab/core/frame.py` — `encode_frame`, `parse_frame`, staged-length helpers.
- `src/stegolab/core/payload_codec.py` — `encode_payload`, `decode_payload`, compression selection.
- `src/stegolab/core/keys.py` — `derive_seed`, `permutation`.
- `src/stegolab/core/capacity.py` — `frame_overhead_bytes`, `nominal_overhead`, `build_capacity_report`.
- `src/stegolab/core/io.py` — `detect_mime`, `sanitize_filename`, `read_bytes`, `write_bytes`, `safe_output_path`.
- `tests/core/test_*.py` — one test module per source module.

---

### Task 1: Project scaffolding + error/exit-code taxonomy

**Files:**
- Create: `pyproject.toml`
- Create: `src/stegolab/__init__.py`
- Create: `src/stegolab/core/__init__.py`
- Create: `src/stegolab/core/errors.py`
- Test: `tests/core/test_errors.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `StegoLabError(Exception)` with class attribute `exit_code: int`, and subclasses `InvalidArguments(2)`, `CapacityExceeded(3)`, `NoPayloadFound(4)`, `CorruptedPayload(4)`, `IntegrityCheckFailed(4)`, `WrongKey(4)`, `UnsupportedFileType(5)`, `UnsupportedMethod(5)`, `MissingOptionalDependency(6)`, `OutputExists(7)`. Every later task raises these.

- [ ] **Step 1: Create the package scaffolding**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "stegolab"
version = "0.1.0"
description = "Educational steganography codebase for graduate cybersecurity instruction"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `src/stegolab/__init__.py`:

```python
"""StegoLab: educational steganography codebase."""

__version__ = "0.1.0"
```

Create `src/stegolab/core/__init__.py` (empty for now; populated as modules land):

```python
"""Core: frame format, payload codec, errors, keys, capacity, and I/O."""
```

- [ ] **Step 2: Write the failing test**

Create `tests/core/test_errors.py`:

```python
import pytest

from stegolab.core import errors


def test_base_error_default_exit_code():
    assert errors.StegoLabError().exit_code == 1


@pytest.mark.parametrize(
    "exc_cls, code",
    [
        (errors.InvalidArguments, 2),
        (errors.CapacityExceeded, 3),
        (errors.NoPayloadFound, 4),
        (errors.CorruptedPayload, 4),
        (errors.IntegrityCheckFailed, 4),
        (errors.WrongKey, 4),
        (errors.UnsupportedFileType, 5),
        (errors.UnsupportedMethod, 5),
        (errors.MissingOptionalDependency, 6),
        (errors.OutputExists, 7),
    ],
)
def test_exit_codes(exc_cls, code):
    assert exc_cls.exit_code == code
    assert issubclass(exc_cls, errors.StegoLabError)
    assert issubclass(exc_cls, Exception)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/core/test_errors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.core.errors'`.

- [ ] **Step 4: Write minimal implementation**

Create `src/stegolab/core/errors.py`:

```python
"""Exception hierarchy. Each error carries the CLI exit code from spec §15/§10.8."""


class StegoLabError(Exception):
    """Base for all StegoLab errors. Generic runtime failure."""

    exit_code: int = 1


class InvalidArguments(StegoLabError):
    exit_code = 2


class CapacityExceeded(StegoLabError):
    exit_code = 3


class NoPayloadFound(StegoLabError):
    exit_code = 4


class CorruptedPayload(StegoLabError):
    exit_code = 4


class IntegrityCheckFailed(StegoLabError):
    exit_code = 4


class WrongKey(StegoLabError):
    exit_code = 4


class UnsupportedFileType(StegoLabError):
    exit_code = 5


class UnsupportedMethod(StegoLabError):
    exit_code = 5


class MissingOptionalDependency(StegoLabError):
    exit_code = 6


class OutputExists(StegoLabError):
    exit_code = 7
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/core/test_errors.py -v`
Expected: PASS (11 passed).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/stegolab/__init__.py src/stegolab/core/__init__.py src/stegolab/core/errors.py tests/core/test_errors.py
git commit -m "feat(core): scaffold package and error/exit-code taxonomy"
```

---

### Task 2: Core types and enums

**Files:**
- Create: `src/stegolab/core/types.py`
- Test: `tests/core/test_types.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - Constants `MAGIC = b"STEGOLAB"`, `FRAME_VERSION = 1`, `FIXED_PREFIX_LEN = 11`, `FIXED_HEADER_FIELDS = 40`, `DEFAULT_MIME = "application/octet-stream"`.
  - `IntEnum`s `PayloadType{TEXT=0,IMAGE=1,BYTES=2}`, `Compression{NONE=0,ZLIB=1,ZSTD=2}`, `Encryption{NONE=0,AES_256_GCM=1,CHACHA20_POLY1305=2}`, `RecoveryClass{EXACT=0,NEAR_EXACT=1}`.
  - `@dataclass FrameFields(payload_type, compression, encryption, recovery_class, original_filename: str, mime_type: str, sha256: bytes, payload_bytes: bytes, salt: bytes|None=None, nonce: bytes|None=None)`.
  - `@dataclass ParsedFrame` with the same fields plus `version: int` and `payload_len: int`.
  - `@dataclass CapacityReport(total_bits: int, total_bytes: int, overhead_bytes: int, usable_bytes: int, is_estimate: bool, assumptions: str)`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_types.py`:

```python
from stegolab.core import types as t


def test_constants():
    assert t.MAGIC == b"STEGOLAB"
    assert len(t.MAGIC) == 8
    assert t.FRAME_VERSION == 1
    assert t.FIXED_PREFIX_LEN == 11
    assert t.FIXED_HEADER_FIELDS == 40
    assert t.DEFAULT_MIME == "application/octet-stream"


def test_enum_values():
    assert int(t.PayloadType.TEXT) == 0
    assert int(t.PayloadType.IMAGE) == 1
    assert int(t.PayloadType.BYTES) == 2
    assert int(t.Compression.NONE) == 0
    assert int(t.Compression.ZLIB) == 1
    assert int(t.Encryption.NONE) == 0
    assert int(t.RecoveryClass.EXACT) == 0
    assert int(t.RecoveryClass.NEAR_EXACT) == 1


def test_frame_fields_dataclass():
    f = t.FrameFields(
        payload_type=t.PayloadType.TEXT,
        compression=t.Compression.NONE,
        encryption=t.Encryption.NONE,
        recovery_class=t.RecoveryClass.EXACT,
        original_filename="secret.txt",
        mime_type="text/plain",
        sha256=b"\x00" * 32,
        payload_bytes=b"hello",
    )
    assert f.salt is None
    assert f.nonce is None
    assert f.payload_bytes == b"hello"


def test_capacity_report_dataclass():
    r = t.CapacityReport(
        total_bits=800, total_bytes=100, overhead_bytes=79,
        usable_bytes=21, is_estimate=True, assumptions="nominal",
    )
    assert r.usable_bytes == 21
    assert r.is_estimate is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.core.types'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/core/types.py`:

```python
"""Enums, dataclasses, and constants for the frame format (spec §8)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

MAGIC = b"STEGOLAB"
FRAME_VERSION = 1
FIXED_PREFIX_LEN = 11          # magic(8) + version(1) + header_len(2)
FIXED_HEADER_FIELDS = 40       # payload_type1+comp1+enc1+rec1+sha256 32+payload_len4
DEFAULT_MIME = "application/octet-stream"


class PayloadType(IntEnum):
    TEXT = 0
    IMAGE = 1
    BYTES = 2


class Compression(IntEnum):
    NONE = 0
    ZLIB = 1
    ZSTD = 2  # Phase 3; reserved


class Encryption(IntEnum):
    NONE = 0
    AES_256_GCM = 1        # Phase 3; reserved
    CHACHA20_POLY1305 = 2  # Phase 3; reserved


class RecoveryClass(IntEnum):
    EXACT = 0
    NEAR_EXACT = 1


@dataclass
class FrameFields:
    payload_type: PayloadType
    compression: Compression
    encryption: Encryption
    recovery_class: RecoveryClass
    original_filename: str
    mime_type: str
    sha256: bytes
    payload_bytes: bytes
    salt: bytes | None = None
    nonce: bytes | None = None


@dataclass
class ParsedFrame:
    version: int
    payload_type: PayloadType
    compression: Compression
    encryption: Encryption
    recovery_class: RecoveryClass
    original_filename: str
    mime_type: str
    sha256: bytes
    payload_len: int
    payload_bytes: bytes
    salt: bytes | None = None
    nonce: bytes | None = None


@dataclass
class CapacityReport:
    total_bits: int
    total_bytes: int
    overhead_bytes: int
    usable_bytes: int
    is_estimate: bool
    assumptions: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_types.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/core/types.py tests/core/test_types.py
git commit -m "feat(core): add enums, dataclasses, and frame constants"
```

---

### Task 3: Binary frame codec (encode/parse + staged-length helpers)

**Files:**
- Create: `src/stegolab/core/frame.py`
- Test: `tests/core/test_frame.py`

**Interfaces:**
- Consumes: `types` (enums, dataclasses, constants), `errors.{NoPayloadFound, CorruptedPayload}`.
- Produces:
  - `encode_frame(fields: FrameFields) -> bytes`.
  - `parse_frame(data: bytes) -> ParsedFrame` — validates structure, fails closed.
  - `header_len_from_prefix(prefix: bytes) -> int` — reads bytes `[9:11]`; raises `CorruptedPayload` if `len(prefix) < 11`; raises `NoPayloadFound` on bad magic.
  - `payload_len_from_header(header: bytes) -> int` — reads `payload_len` at header offset 36.
  - `frame_total_len(header_len: int, payload_len: int) -> int`.
  - These staged helpers let bit-level extractors (image LSB, zero-width) read exactly enough bits without buffering the whole stream. **Note:** `parse_frame` validates only structure; SHA-256 checksum validation happens in Task 4 (`payload_codec.decode_payload`) after decompression, because `sha256` covers the *original* bytes, not the framed `payload_bytes`.

- [ ] **Step 1: Write the failing round-trip test**

Create `tests/core/test_frame.py`:

```python
import struct

import pytest

from stegolab.core import errors, frame
from stegolab.core import types as t


def _fields(payload=b"the secret payload", filename="secret.txt", mime="text/plain"):
    return t.FrameFields(
        payload_type=t.PayloadType.TEXT,
        compression=t.Compression.ZLIB,
        encryption=t.Encryption.NONE,
        recovery_class=t.RecoveryClass.EXACT,
        original_filename=filename,
        mime_type=mime,
        sha256=b"\xab" * 32,
        payload_bytes=payload,
    )


def test_round_trip_preserves_all_fields():
    data = frame.encode_frame(_fields())
    parsed = frame.parse_frame(data)
    assert parsed.version == 1
    assert parsed.payload_type == t.PayloadType.TEXT
    assert parsed.compression == t.Compression.ZLIB
    assert parsed.encryption == t.Encryption.NONE
    assert parsed.recovery_class == t.RecoveryClass.EXACT
    assert parsed.original_filename == "secret.txt"
    assert parsed.mime_type == "text/plain"
    assert parsed.sha256 == b"\xab" * 32
    assert parsed.payload_len == len(b"the secret payload")
    assert parsed.payload_bytes == b"the secret payload"


def test_layout_starts_with_magic_and_version():
    data = frame.encode_frame(_fields())
    assert data[0:8] == b"STEGOLAB"
    assert data[8] == 1


def test_unicode_filename_round_trips():
    parsed = frame.parse_frame(frame.encode_frame(_fields(filename="résumé.txt")))
    assert parsed.original_filename == "résumé.txt"


def test_staged_length_helpers():
    data = frame.encode_frame(_fields())
    header_len = frame.header_len_from_prefix(data[:t.FIXED_PREFIX_LEN])
    header = data[t.FIXED_PREFIX_LEN:t.FIXED_PREFIX_LEN + header_len]
    payload_len = frame.payload_len_from_header(header)
    assert payload_len == len(b"the secret payload")
    assert frame.frame_total_len(header_len, payload_len) == len(data)


def test_bad_magic_raises_no_payload_found():
    data = bytearray(frame.encode_frame(_fields()))
    data[0:8] = b"XXXXXXXX"
    with pytest.raises(errors.NoPayloadFound):
        frame.parse_frame(bytes(data))


def test_unsupported_version_raises_corrupted():
    data = bytearray(frame.encode_frame(_fields()))
    data[8] = 99
    with pytest.raises(errors.CorruptedPayload):
        frame.parse_frame(bytes(data))


def test_truncated_header_raises_corrupted():
    data = frame.encode_frame(_fields())
    with pytest.raises(errors.CorruptedPayload):
        frame.parse_frame(data[:t.FIXED_PREFIX_LEN + 5])


def test_truncated_payload_raises_corrupted():
    data = frame.encode_frame(_fields())
    with pytest.raises(errors.CorruptedPayload):
        frame.parse_frame(data[:-3])


def test_too_short_for_prefix_raises_corrupted():
    with pytest.raises(errors.CorruptedPayload):
        frame.parse_frame(b"STEG")


def test_extra_trailing_bytes_are_ignored():
    # Bit-stream extractors may hand over more bytes than the frame needs.
    data = frame.encode_frame(_fields()) + b"\x00\x00\x99"
    parsed = frame.parse_frame(data)
    assert parsed.payload_bytes == b"the secret payload"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_frame.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.core.frame'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/core/frame.py`:

```python
"""Binary frame wire format (spec §8.3). All integers big-endian, strings UTF-8.

Layout:
  Fixed prefix (11 bytes): magic(8) "STEGOLAB" | version(1) | header_len(2)
  Header block (header_len bytes):
    payload_type(1) compression(1) encryption(1) recovery_class(1)
    sha256(32) payload_len(4)
    filename_len(2) filename(...) mime_len(2) mime(...)
    [if encryption != 0] salt_len(1) salt(...) nonce_len(1) nonce(...)
  Payload: payload_bytes(payload_len)
"""

from __future__ import annotations

import struct

from .errors import CorruptedPayload, NoPayloadFound
from .types import (
    FIXED_PREFIX_LEN,
    FRAME_VERSION,
    MAGIC,
    Compression,
    Encryption,
    FrameFields,
    ParsedFrame,
    PayloadType,
    RecoveryClass,
)

# Offset of payload_len within the header block: 4 enum bytes + 32 sha256 bytes.
_PAYLOAD_LEN_OFFSET = 36


def encode_frame(fields: FrameFields) -> bytes:
    if len(fields.sha256) != 32:
        raise ValueError("sha256 must be exactly 32 bytes")
    fn = fields.original_filename.encode("utf-8")
    mt = fields.mime_type.encode("utf-8")
    if len(fn) > 0xFFFF or len(mt) > 0xFFFF:
        raise ValueError("filename/mime too long for a uint16 length prefix")

    header = bytearray()
    header += struct.pack(
        "!BBBB",
        int(fields.payload_type),
        int(fields.compression),
        int(fields.encryption),
        int(fields.recovery_class),
    )
    header += fields.sha256
    header += struct.pack("!I", len(fields.payload_bytes))
    header += struct.pack("!H", len(fn)) + fn
    header += struct.pack("!H", len(mt)) + mt
    if int(fields.encryption) != 0:
        salt = fields.salt or b""
        nonce = fields.nonce or b""
        if len(salt) > 0xFF or len(nonce) > 0xFF:
            raise ValueError("salt/nonce too long for a uint8 length prefix")
        header += struct.pack("!B", len(salt)) + salt
        header += struct.pack("!B", len(nonce)) + nonce

    if len(header) > 0xFFFF:
        raise ValueError("header too long for a uint16 header_len")

    out = bytearray()
    out += MAGIC
    out += struct.pack("!B", FRAME_VERSION)
    out += struct.pack("!H", len(header))
    out += header
    out += fields.payload_bytes
    return bytes(out)


def header_len_from_prefix(prefix: bytes) -> int:
    if len(prefix) < FIXED_PREFIX_LEN:
        raise CorruptedPayload("frame prefix too short")
    if prefix[0:8] != MAGIC:
        raise NoPayloadFound("no StegoLab frame magic")
    return struct.unpack("!H", prefix[9:11])[0]


def payload_len_from_header(header: bytes) -> int:
    if len(header) < _PAYLOAD_LEN_OFFSET + 4:
        raise CorruptedPayload("header too short for payload_len")
    return struct.unpack("!I", header[_PAYLOAD_LEN_OFFSET:_PAYLOAD_LEN_OFFSET + 4])[0]


def frame_total_len(header_len: int, payload_len: int) -> int:
    return FIXED_PREFIX_LEN + header_len + payload_len


class _Cursor:
    """Bounded reader over the header block; any over-read fails closed."""

    def __init__(self, buf: bytes):
        self.buf = buf
        self.pos = 0

    def take(self, n: int) -> bytes:
        end = self.pos + n
        if end > len(self.buf):
            raise CorruptedPayload("frame header truncated")
        chunk = self.buf[self.pos:end]
        self.pos = end
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("!H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("!I", self.take(4))[0]


def parse_frame(data: bytes) -> ParsedFrame:
    header_len = header_len_from_prefix(data[:FIXED_PREFIX_LEN])  # magic + length checks
    version = data[8]
    if version != FRAME_VERSION:
        raise CorruptedPayload(f"unsupported frame version: {version}")

    header_start = FIXED_PREFIX_LEN
    header_end = header_start + header_len
    if len(data) < header_end:
        raise CorruptedPayload("frame header truncated")
    header = data[header_start:header_end]

    c = _Cursor(header)
    try:
        payload_type = PayloadType(c.u8())
        compression = Compression(c.u8())
        encryption = Encryption(c.u8())
        recovery_class = RecoveryClass(c.u8())
    except ValueError as exc:  # unknown enum value
        raise CorruptedPayload("invalid enum in frame header") from exc
    sha256 = c.take(32)
    payload_len = c.u32()
    filename = c.take(c.u16()).decode("utf-8", errors="strict")
    mime_type = c.take(c.u16()).decode("utf-8", errors="strict")
    salt = nonce = None
    if int(encryption) != 0:
        salt = c.take(c.u8())
        nonce = c.take(c.u8())

    payload_start = header_end
    payload_end = payload_start + payload_len
    if len(data) < payload_end:
        raise CorruptedPayload("frame payload truncated")
    payload_bytes = data[payload_start:payload_end]

    return ParsedFrame(
        version=version,
        payload_type=payload_type,
        compression=compression,
        encryption=encryption,
        recovery_class=recovery_class,
        original_filename=filename,
        mime_type=mime_type,
        sha256=sha256,
        payload_len=payload_len,
        payload_bytes=payload_bytes,
        salt=salt,
        nonce=nonce,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_frame.py -v`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/core/frame.py tests/core/test_frame.py
git commit -m "feat(core): binary frame codec with fail-closed parsing"
```

---

### Task 4: Payload codec (compression + SHA-256 integrity)

**Files:**
- Create: `src/stegolab/core/payload_codec.py`
- Test: `tests/core/test_payload_codec.py`

**Interfaces:**
- Consumes: `frame.{encode_frame, parse_frame}`, `types.*`, `errors.{IntegrityCheckFailed, UnsupportedFileType}`.
- Produces:
  - `select_compression(mode: str, mime_type: str, raw: bytes) -> Compression` — resolves `"auto"|"none"|"zlib"` (`"zstd"` raises `UnsupportedFileType` in MVP). `auto` → `NONE` when MIME is already-compressed (`image/png`, `image/jpeg`, `application/zip`, `application/gzip`) **or** the raw bytes are high-entropy (compression ratio ≥ 0.95 on a zlib trial), else `ZLIB`.
  - `encode_payload(*, raw: bytes, payload_type: PayloadType, original_filename: str, mime_type: str, compression: str = "auto", encryption: Encryption = Encryption.NONE, recovery_class: RecoveryClass = RecoveryClass.EXACT) -> bytes` — hashes `raw`, compresses, builds the frame.
  - `decode_payload(parsed: ParsedFrame) -> bytes` — decompresses `payload_bytes`, verifies `sha256(original) == parsed.sha256` (else `IntegrityCheckFailed`), returns original bytes.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_payload_codec.py`:

```python
import hashlib

import pytest

from stegolab.core import errors, frame, payload_codec
from stegolab.core import types as t


def test_encode_decode_round_trip_text():
    raw = b"attack at dawn" * 50
    framed = payload_codec.encode_payload(
        raw=raw, payload_type=t.PayloadType.TEXT,
        original_filename="orders.txt", mime_type="text/plain", compression="zlib",
    )
    parsed = frame.parse_frame(framed)
    assert parsed.compression == t.Compression.ZLIB
    assert payload_codec.decode_payload(parsed) == raw


def test_sha256_is_over_original_bytes():
    raw = b"hello world"
    framed = payload_codec.encode_payload(
        raw=raw, payload_type=t.PayloadType.TEXT,
        original_filename="h.txt", mime_type="text/plain", compression="zlib",
    )
    parsed = frame.parse_frame(framed)
    assert parsed.sha256 == hashlib.sha256(raw).digest()


def test_corrupted_payload_fails_integrity():
    raw = b"important bytes"
    framed = bytearray(payload_codec.encode_payload(
        raw=raw, payload_type=t.PayloadType.BYTES,
        original_filename="x.bin", mime_type="application/octet-stream", compression="none",
    ))
    framed[-1] ^= 0xFF  # flip a payload byte
    parsed = frame.parse_frame(bytes(framed))
    with pytest.raises(errors.IntegrityCheckFailed):
        payload_codec.decode_payload(parsed)


def test_select_compression_auto_skips_already_compressed():
    assert payload_codec.select_compression("auto", "image/png", b"\x89PNG....") == t.Compression.NONE


def test_select_compression_auto_compresses_text():
    assert payload_codec.select_compression("auto", "text/plain", b"aaaa" * 100) == t.Compression.ZLIB


def test_select_compression_none_and_zlib_explicit():
    assert payload_codec.select_compression("none", "text/plain", b"x") == t.Compression.NONE
    assert payload_codec.select_compression("zlib", "text/plain", b"x") == t.Compression.ZLIB


def test_zstd_not_supported_in_mvp():
    with pytest.raises(errors.UnsupportedFileType):
        payload_codec.select_compression("zstd", "text/plain", b"x")


def test_none_compression_round_trip():
    raw = b"\x00\x01\x02\x03payload"
    framed = payload_codec.encode_payload(
        raw=raw, payload_type=t.PayloadType.BYTES,
        original_filename="d.bin", mime_type="application/octet-stream", compression="none",
    )
    parsed = frame.parse_frame(framed)
    assert parsed.compression == t.Compression.NONE
    assert payload_codec.decode_payload(parsed) == raw
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_payload_codec.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.core.payload_codec'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/core/payload_codec.py`:

```python
"""Wrap raw payload bytes into a frame and back (spec §8.3–8.5).

Order on encode: hash(original) -> compress -> frame.
Order on decode: parse frame -> decompress -> verify hash(original).
"""

from __future__ import annotations

import hashlib
import zlib

from .errors import IntegrityCheckFailed, UnsupportedFileType
from .frame import encode_frame
from .types import (
    Compression,
    Encryption,
    FrameFields,
    ParsedFrame,
    PayloadType,
    RecoveryClass,
)

_ALREADY_COMPRESSED_MIME = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "application/zip",
    "application/gzip",
    "application/x-7z-compressed",
}


def select_compression(mode: str, mime_type: str, raw: bytes) -> Compression:
    mode = (mode or "auto").lower()
    if mode == "none":
        return Compression.NONE
    if mode == "zlib":
        return Compression.ZLIB
    if mode == "zstd":
        raise UnsupportedFileType("zstd compression is not available in the MVP")
    if mode != "auto":
        raise UnsupportedFileType(f"unknown compression mode: {mode}")
    # auto
    if mime_type.lower() in _ALREADY_COMPRESSED_MIME:
        return Compression.NONE
    if not raw:
        return Compression.NONE
    trial = zlib.compress(raw, level=6)
    if len(trial) >= len(raw) * 0.95:  # high-entropy: compression not worth it
        return Compression.NONE
    return Compression.ZLIB


def _compress(comp: Compression, raw: bytes) -> bytes:
    if comp == Compression.NONE:
        return raw
    if comp == Compression.ZLIB:
        return zlib.compress(raw, level=6)
    raise UnsupportedFileType(f"compression {comp!r} not supported in MVP")


def _decompress(comp: Compression, data: bytes) -> bytes:
    if comp == Compression.NONE:
        return data
    if comp == Compression.ZLIB:
        try:
            return zlib.decompress(data)
        except zlib.error as exc:
            raise IntegrityCheckFailed("payload failed to decompress") from exc
    raise UnsupportedFileType(f"compression {comp!r} not supported in MVP")


def encode_payload(
    *,
    raw: bytes,
    payload_type: PayloadType,
    original_filename: str,
    mime_type: str,
    compression: str = "auto",
    encryption: Encryption = Encryption.NONE,
    recovery_class: RecoveryClass = RecoveryClass.EXACT,
) -> bytes:
    comp = select_compression(compression, mime_type, raw)
    sha256 = hashlib.sha256(raw).digest()
    payload_bytes = _compress(comp, raw)
    fields = FrameFields(
        payload_type=payload_type,
        compression=comp,
        encryption=encryption,
        recovery_class=recovery_class,
        original_filename=original_filename,
        mime_type=mime_type,
        sha256=sha256,
        payload_bytes=payload_bytes,
    )
    return encode_frame(fields)


def decode_payload(parsed: ParsedFrame) -> bytes:
    original = _decompress(parsed.compression, parsed.payload_bytes)
    if hashlib.sha256(original).digest() != parsed.sha256:
        raise IntegrityCheckFailed("payload checksum mismatch")
    return original
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_payload_codec.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/core/payload_codec.py tests/core/test_payload_codec.py
git commit -m "feat(core): payload codec with zlib compression and sha256 integrity"
```

---

### Task 5: Key derivation and deterministic permutation

**Files:**
- Create: `src/stegolab/core/keys.py`
- Test: `tests/core/test_keys.py`

**Interfaces:**
- Consumes: NumPy, `hashlib`.
- Produces:
  - `derive_seed(key: str) -> int` — first 8 bytes of `SHA-256(utf8(key))` as a big-endian unsigned int.
  - `permutation(n: int, key: str) -> numpy.ndarray` — a deterministic, key-seeded Fisher–Yates permutation of `range(n)` using `numpy.random.Generator(numpy.random.PCG64(derive_seed(key)))`. Same `(n, key)` always yields the same array; different keys yield different orders.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_keys.py`:

```python
import hashlib

import numpy as np

from stegolab.core import keys


def test_derive_seed_is_deterministic_and_matches_sha256():
    expected = int.from_bytes(hashlib.sha256(b"course-demo").digest()[:8], "big")
    assert keys.derive_seed("course-demo") == expected
    assert keys.derive_seed("course-demo") == keys.derive_seed("course-demo")


def test_permutation_is_a_valid_permutation():
    perm = keys.permutation(1000, "k")
    assert sorted(perm.tolist()) == list(range(1000))


def test_permutation_is_deterministic_for_same_key():
    a = keys.permutation(500, "same-key")
    b = keys.permutation(500, "same-key")
    assert np.array_equal(a, b)


def test_different_keys_give_different_orders():
    a = keys.permutation(500, "key-a")
    b = keys.permutation(500, "key-b")
    assert not np.array_equal(a, b)


def test_permutation_zero_length():
    assert keys.permutation(0, "k").tolist() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_keys.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.core.keys'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/core/keys.py`:

```python
"""Key derivation and deterministic permutation (spec §8.6).

seed = SHA-256(utf8(key))[:8] (big-endian) -> NumPy PCG64 -> Fisher-Yates shuffle.
Pinned to PCG64 so the permutation is reproducible across platforms.
"""

from __future__ import annotations

import hashlib

import numpy as np


def derive_seed(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def permutation(n: int, key: str) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(derive_seed(key)))
    perm = np.arange(n)
    rng.shuffle(perm)  # in-place Fisher-Yates
    return perm
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_keys.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/core/keys.py tests/core/test_keys.py
git commit -m "feat(core): key-seeded deterministic permutation (PCG64 Fisher-Yates)"
```

---

### Task 6: Capacity overhead math

**Files:**
- Create: `src/stegolab/core/capacity.py`
- Test: `tests/core/test_capacity.py`

**Interfaces:**
- Consumes: `types.{FIXED_PREFIX_LEN, FIXED_HEADER_FIELDS, DEFAULT_MIME, Encryption, CapacityReport}`, `errors.CapacityExceeded`.
- Produces:
  - `frame_overhead_bytes(original_filename: str, mime_type: str, encryption: Encryption = Encryption.NONE, salt_len: int = 0, nonce_len: int = 0) -> int` — `11 + header_len`.
  - `nominal_overhead() -> int` — overhead for empty filename + `DEFAULT_MIME`, unencrypted = `79`.
  - `build_capacity_report(total_capacity_bits: int, overhead_bytes: int, *, is_estimate: bool, assumptions: str) -> CapacityReport` — computes `total_bytes` and `usable_bytes = max(0, total_bytes - overhead_bytes)`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_capacity.py`:

```python
from stegolab.core import capacity
from stegolab.core import types as t


def test_nominal_overhead_is_79():
    # 11 prefix + 40 fixed header + 2 + len("") + 2 + len("application/octet-stream"=24)
    assert capacity.nominal_overhead() == 79


def test_frame_overhead_scales_with_filename_and_mime():
    base = capacity.frame_overhead_bytes("", "")
    assert base == t.FIXED_PREFIX_LEN + t.FIXED_HEADER_FIELDS + 2 + 0 + 2 + 0
    assert capacity.frame_overhead_bytes("ab.txt", "text/plain") == base + len("ab.txt") + len("text/plain")


def test_frame_overhead_adds_salt_and_nonce_when_encrypted():
    plain = capacity.frame_overhead_bytes("f", "m", encryption=t.Encryption.NONE)
    enc = capacity.frame_overhead_bytes(
        "f", "m", encryption=t.Encryption.AES_256_GCM, salt_len=16, nonce_len=12,
    )
    assert enc == plain + (1 + 16) + (1 + 12)


def test_build_capacity_report_subtracts_overhead():
    r = capacity.build_capacity_report(8000, 79, is_estimate=True, assumptions="nominal")
    assert r.total_bytes == 1000
    assert r.usable_bytes == 1000 - 79
    assert r.is_estimate is True


def test_usable_bytes_never_negative():
    r = capacity.build_capacity_report(80, 79, is_estimate=False, assumptions="x")
    assert r.total_bytes == 10
    assert r.usable_bytes == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_capacity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.core.capacity'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/core/capacity.py`:

```python
"""Frame overhead and capacity reports (spec §8.3, §13)."""

from __future__ import annotations

from .types import (
    DEFAULT_MIME,
    FIXED_HEADER_FIELDS,
    FIXED_PREFIX_LEN,
    CapacityReport,
    Encryption,
)


def frame_overhead_bytes(
    original_filename: str,
    mime_type: str,
    encryption: Encryption = Encryption.NONE,
    salt_len: int = 0,
    nonce_len: int = 0,
) -> int:
    header_len = (
        FIXED_HEADER_FIELDS
        + 2 + len(original_filename.encode("utf-8"))
        + 2 + len(mime_type.encode("utf-8"))
    )
    if int(encryption) != 0:
        header_len += (1 + salt_len) + (1 + nonce_len)
    return FIXED_PREFIX_LEN + header_len


def nominal_overhead() -> int:
    return frame_overhead_bytes("", DEFAULT_MIME)


def build_capacity_report(
    total_capacity_bits: int,
    overhead_bytes: int,
    *,
    is_estimate: bool,
    assumptions: str,
) -> CapacityReport:
    total_bytes = total_capacity_bits // 8
    usable_bytes = max(0, total_bytes - overhead_bytes)
    return CapacityReport(
        total_bits=total_capacity_bits,
        total_bytes=total_bytes,
        overhead_bytes=overhead_bytes,
        usable_bytes=usable_bytes,
        is_estimate=is_estimate,
        assumptions=assumptions,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_capacity.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/core/capacity.py tests/core/test_capacity.py
git commit -m "feat(core): frame overhead math and capacity reports"
```

---

### Task 7: Safe file I/O (MIME, filename sanitization, overwrite + traversal guards)

**Files:**
- Create: `src/stegolab/core/io.py`
- Modify: `src/stegolab/core/__init__.py` (re-export the public core API)
- Test: `tests/core/test_io.py`

**Interfaces:**
- Consumes: `mimetypes`, `pathlib`, `errors.{OutputExists, InvalidArguments}`.
- Produces:
  - `detect_mime(path) -> str` — `mimetypes.guess_type`, falling back to `application/octet-stream`.
  - `sanitize_filename(name: str) -> str` — basename only; strips `/`, `\`, NUL; maps `""`/`.`/`..` to `payload.bin`.
  - `read_bytes(path) -> bytes`.
  - `write_bytes(path, data: bytes, *, overwrite: bool = False) -> None` — raises `OutputExists` if the path exists and `overwrite` is False.
  - `safe_output_path(out_dir, filename: str) -> pathlib.Path` — joins a sanitized basename under `out_dir`; raises `InvalidArguments` if the resolved path escapes `out_dir`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_io.py`:

```python
import pytest

from stegolab.core import errors
from stegolab.core import io as cio


def test_sanitize_strips_paths():
    assert cio.sanitize_filename("/etc/passwd") == "passwd"
    assert cio.sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert cio.sanitize_filename("plain.txt") == "plain.txt"


def test_sanitize_maps_dangerous_basenames():
    assert cio.sanitize_filename("") == "payload.bin"
    assert cio.sanitize_filename("..") == "payload.bin"
    assert cio.sanitize_filename(".") == "payload.bin"


def test_detect_mime_text_and_fallback(tmp_path):
    assert cio.detect_mime(tmp_path / "a.txt") == "text/plain"
    assert cio.detect_mime(tmp_path / "a.unknownext") == "application/octet-stream"


def test_read_write_round_trip(tmp_path):
    p = tmp_path / "out.bin"
    cio.write_bytes(p, b"\x00\x01data")
    assert cio.read_bytes(p) == b"\x00\x01data"


def test_write_refuses_overwrite_by_default(tmp_path):
    p = tmp_path / "out.bin"
    cio.write_bytes(p, b"first")
    with pytest.raises(errors.OutputExists):
        cio.write_bytes(p, b"second")
    cio.write_bytes(p, b"second", overwrite=True)
    assert cio.read_bytes(p) == b"second"


def test_safe_output_path_stays_in_dir(tmp_path):
    out = cio.safe_output_path(tmp_path, "recovered.png")
    assert out.parent == tmp_path.resolve()
    assert out.name == "recovered.png"


def test_safe_output_path_blocks_traversal(tmp_path):
    # Even a malicious frame filename cannot escape the output directory.
    out = cio.safe_output_path(tmp_path, "../../escape.txt")
    assert out.parent == tmp_path.resolve()
    assert out.name == "escape.txt"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_io.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.core.io'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/core/io.py`:

```python
"""Safe file I/O: MIME detection, filename sanitization, overwrite/traversal guards (spec §20.2)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from .errors import InvalidArguments, OutputExists

_DEFAULT_MIME = "application/octet-stream"


def detect_mime(path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or _DEFAULT_MIME


def sanitize_filename(name: str) -> str:
    name = (name or "").replace("\\", "/").replace("\x00", "")
    base = name.rsplit("/", 1)[-1]
    if base in ("", ".", ".."):
        return "payload.bin"
    return base


def read_bytes(path) -> bytes:
    return Path(path).read_bytes()


def write_bytes(path, data: bytes, *, overwrite: bool = False) -> None:
    p = Path(path)
    if p.exists() and not overwrite:
        raise OutputExists(f"output exists: {p} (pass overwrite to replace)")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def safe_output_path(out_dir, filename: str) -> Path:
    base = sanitize_filename(filename)
    root = Path(out_dir).resolve()
    out = (root / base).resolve()
    if out != root and root not in out.parents:
        raise InvalidArguments("resolved output path escapes the output directory")
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_io.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Re-export the public core API**

Replace `src/stegolab/core/__init__.py` with:

```python
"""Core: frame format, payload codec, errors, keys, capacity, and I/O."""

from . import capacity, errors, frame, io, keys, payload_codec, types
from .capacity import build_capacity_report, frame_overhead_bytes, nominal_overhead
from .frame import encode_frame, frame_total_len, header_len_from_prefix, parse_frame, payload_len_from_header
from .keys import derive_seed, permutation
from .payload_codec import decode_payload, encode_payload, select_compression
from .types import (
    CapacityReport,
    Compression,
    Encryption,
    FrameFields,
    ParsedFrame,
    PayloadType,
    RecoveryClass,
)

__all__ = [
    "capacity", "errors", "frame", "io", "keys", "payload_codec", "types",
    "build_capacity_report", "frame_overhead_bytes", "nominal_overhead",
    "encode_frame", "frame_total_len", "header_len_from_prefix", "parse_frame", "payload_len_from_header",
    "derive_seed", "permutation",
    "decode_payload", "encode_payload", "select_compression",
    "CapacityReport", "Compression", "Encryption", "FrameFields", "ParsedFrame",
    "PayloadType", "RecoveryClass",
]
```

- [ ] **Step 6: Run the full core test suite**

Run: `pytest tests/core -v`
Expected: PASS (all tasks 1–7 green; ~40 tests).

- [ ] **Step 7: Commit**

```bash
git add src/stegolab/core/io.py src/stegolab/core/__init__.py tests/core/test_io.py
git commit -m "feat(core): safe file I/O and public core API exports"
```

---

## Self-Review

**1. Spec coverage (Plan 01 scope = M1: core frame, I/O, error model, capacity, keys/PRNG):**
- §8.2/§8.3 frame fields + wire format → Task 3 (`frame.py`), Task 2 (types). ✓
- §8.3 `frame_overhead_bytes` + nominal 79 → Task 6. ✓
- §8.4 fail-closed parsing (bad magic/version/length) → Task 3 tests. ✓
- §8.5 compression none/zlib + auto policy → Task 4. ✓
- §8.3 sha256 over original bytes → Task 4 (`test_sha256_is_over_original_bytes`). ✓
- §8.6 KDF + deterministic PCG64 permutation → Task 5. ✓
- §15 error→exit-code taxonomy → Task 1. ✓
- §20.2 filename sanitization, overwrite guard, no traversal → Task 7. ✓
- Deferred to later plans by design: encryption bodies (§8.7, Phase 3), CSPRNG keystream for generative methods (§8.6, Plan 04 `lm_common`), per-method capacity-bit formulas (Plans 02–05). The `Encryption`/`salt`/`nonce` frame fields are reserved and tested here so the wire format is forward-compatible.

**2. Placeholder scan:** No `TBD`/`TODO`/"handle edge cases"/"add validation" — every step has concrete test + implementation code. ✓

**3. Type consistency:** `encode_frame(fields: FrameFields)` (Task 3) consumes `FrameFields` (Task 2); `parse_frame -> ParsedFrame` (Task 3) is consumed by `decode_payload(parsed: ParsedFrame)` (Task 4); `frame_overhead_bytes`/`nominal_overhead` (Task 6) use `FIXED_PREFIX_LEN`/`FIXED_HEADER_FIELDS`/`DEFAULT_MIME` (Task 2); `select_compression` return type `Compression` matches `parsed.compression` usage. `_PAYLOAD_LEN_OFFSET = 36` in Task 3 equals 4 enum bytes + 32 sha256 bytes, consistent with the encode order. ✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-28-stegolab-01-core-foundation.md`. This is Plan 01 of the 8-plan MVP roadmap (the dependency root). Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach? (And note: this repo is not yet a git repository — the per-task `git commit` steps assume one. I can `git init` first, or we can drop the commit steps.)
