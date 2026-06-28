"""stegolab CLI: hide / extract / capacity for the image methods (spec §10)."""

from __future__ import annotations

import dataclasses
import json as _json

import typer

from .core.errors import StegoLabError, UnsupportedMethod
from .eval import text_metrics
from .image import bitplane_image, edge_adaptive_lsb, lsb, randomized_lsb
from .text import zero_width

app = typer.Typer(add_completion=False, help="StegoLab: educational steganography CLI.")

METHODS = {
    "image-lsb": lsb,
    "image-randomized-lsb": randomized_lsb,
    "image-edge-adaptive-lsb": edge_adaptive_lsb,
    "image-bitplane": bitplane_image,
    "text-zero-width": zero_width,
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
    slot_policy: str = typer.Option("word-boundary", "--slot-policy"),
    max_density: int = typer.Option(4, "--max-density"),
    alphabet: str = typer.Option("default", "--alphabet"),
    compress: str = typer.Option("auto", "--compress"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    json_out: bool = typer.Option(False, "--json"),
):
    try:
        mod = _resolve(method)
        result = mod.hide(cover=cover, payload=payload, out=out, overwrite=overwrite,
                          params=_params(bits_per_channel=bits_per_channel, channels=channels, key=key,
                                         allow_unkeyed=allow_unkeyed, activity=activity,
                                         threshold_mode=threshold_mode, hidden_msb_bits=hidden_msb_bits,
                                         cover_lsb_bits=cover_lsb_bits, resize_mode=resize_mode, slot_policy=slot_policy, max_density=max_density, alphabet=alphabet, compress=compress))
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
    alphabet: str = typer.Option("default", "--alphabet"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    json_out: bool = typer.Option(False, "--json"),
):
    try:
        mod = _resolve(method)
        result = mod.extract(stego=stego, out=out, overwrite=overwrite,
                            params=_params(bits_per_channel=bits_per_channel, key=key,
                                           allow_unkeyed=allow_unkeyed, hidden_msb_bits=hidden_msb_bits,
                                           cover_lsb_bits=cover_lsb_bits, alphabet=alphabet))
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
    alphabet: str = typer.Option("default", "--alphabet"),
    max_density: int = typer.Option(4, "--max-density"),
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
            compress=compress, resize_mode=resize_mode, alphabet=alphabet, max_density=max_density))
        _emit("capacity", method, result, json_out)
    except StegoLabError as exc:
        _fail("capacity", method, exc, json_out)


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
