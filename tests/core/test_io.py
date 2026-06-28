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
