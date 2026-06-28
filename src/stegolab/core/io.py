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
