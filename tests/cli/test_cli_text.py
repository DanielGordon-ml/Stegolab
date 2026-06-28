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
