import json

import numpy as np
from PIL import Image
from typer.testing import CliRunner

from stegolab.cli import app

runner = CliRunner()


def _cover(tmp_path, w=64, h=64, seed=7):
    rng = np.random.default_rng(seed)
    p = tmp_path / "cover.png"
    Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8)).save(p)
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
