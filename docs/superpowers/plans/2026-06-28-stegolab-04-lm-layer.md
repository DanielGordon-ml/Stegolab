# StegoLab Deterministic LM Layer + Model Fetch Implementation Plan (Plan 04 of 08)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared, deterministic language-model layer (`text/lm_common.py` + `text/lm_transformers.py`) and the bundled-model fetch/verify tooling that the Plan 05 SOTA generative text methods (`text-ans-generative`, `text-mec`) will consume — a reproducible next-token-distribution provider, fixed-precision PMF quantization, a CSPRNG keystream, and a one-time model fetch script.

**Architecture:** The deterministic core in `text/lm_common.py` is **pure NumPy + stdlib** (no torch), so it imports and tests without the heavy ML stack: a `TokenDistribution` value type, `quantize_pmf` (rounds probabilities to a fixed grid so two machines agree bit-for-bit), `top_k_filter`/`top_p_filter`, a `KeyStream` CSPRNG (HMAC-SHA256 counter mode), a `Provider` protocol, and a deterministic `MockProvider` for CI. `text/lm_transformers.py` isolates the torch/transformers adapter (`TransformersProvider`) — tested against a tiny **from-config** GPT-2 (random seeded weights, no download), which on this environment is bit-exact deterministic. `models/fetch_models.py` downloads + checksum-verifies the pinned real model as an install-time step (never at runtime).

**Tech Stack:** Python 3.11+, NumPy, stdlib (`hashlib`, `hmac`). Optional: PyTorch 2.10 (CPU) + Transformers 5.3 for the real-model adapter (present in this env). pytest.

## Global Constraints

Copied from `stegolab_engineering_spec.md` (§7.2, §8.6, §9.7–9.8, §16.3, §18.2, §20.1) and prior plans.

- **Python 3.11+.** Reuse `stegolab.core` where relevant.
- **`text/lm_common.py` must NOT import torch/transformers** — the deterministic methods and the whole core must remain importable without the ML stack (spec §18.4). All torch usage is isolated in `text/lm_transformers.py`, behind import guards.
- **Determinism is the contract** (spec §9.7–9.8, §16.3): the same context + the same provider must yield bit-identical token distributions. `quantize_pmf` snaps probabilities onto a fixed grid (default `precision_bits=16`) deterministically — stabilizing a single provider's output and remaining idempotent. It does NOT by itself reconcile two machines whose float softmax differs near a grid boundary; cross-machine agreement therefore requires the provider to reproduce the float logits bit-identically (eval mode, fixed precision, pinned model/revision).
- **CSPRNG keystream** is the secret-bearing randomness for generative stego: derived from a passphrase via HMAC-SHA256 in counter mode; same key → same stream; different key → different stream (spec §8.6).
- **Mock for CI, real for release** (spec §16.3): CI-grade tests run against `MockProvider` (deterministic, no model, no network). Real-model adapter tests use a tiny **from-config** model (no download); they `pytest.importorskip("torch")`/`("transformers")` so the suite passes where the ML stack is absent.
- **No runtime network** (spec §20.1): `models/fetch_models.py` performs the model download only as an explicit install-time action; it is never invoked by the library at runtime, and is not run by the test suite. Checksum verification is unit-tested with a tiny local fixture.
- **TokenDistribution invariant:** `token_ids` and `probs` are equal-length NumPy arrays; `probs` are non-negative float64 summing to ≈1.0.

## File Structure

- `src/stegolab/text/lm_common.py` (NEW) — `TokenDistribution`, `softmax`, `normalize`, `quantize_pmf`, `top_k_filter`, `top_p_filter`, `KeyStream`, `Provider`, `MockProvider`.
- `src/stegolab/text/lm_transformers.py` (NEW) — `TransformersProvider` (torch-isolated).
- `models/MODEL_CARD.md` (NEW) — pinned model id/revision/checksums + provenance.
- `models/fetch_models.py` (NEW) — `verify_file`, `fetch` (install-time download + verify).
- `pyproject.toml` — add `[project.optional-dependencies] linguistic` extra (torch, transformers, huggingface-hub).
- `tests/text/test_lm_common_pmf.py`, `tests/text/test_lm_keystream.py`, `tests/text/test_lm_mock_provider.py`, `tests/text/test_lm_transformers.py`, `tests/models/test_fetch_verify.py`.

---

### Task 1: `lm_common` — TokenDistribution + PMF utilities (pure NumPy)

**Files:**
- Create: `src/stegolab/text/lm_common.py`
- Test: `tests/text/test_lm_common_pmf.py`

**Interfaces:**
- Consumes: NumPy.
- Produces:
  - `@dataclass TokenDistribution(token_ids: np.ndarray, probs: np.ndarray)` with `__post_init__` validation (equal length, probs≥0, sum≈1 within 1e-6) — raises `ValueError` otherwise.
  - `softmax(logits) -> np.ndarray` (float64, numerically stable).
  - `normalize(probs) -> np.ndarray` (divide by sum; zero-sum → `ValueError`).
  - `quantize_pmf(probs, precision_bits=16) -> np.ndarray` — round to a `1/2**precision_bits` grid as integer counts summing to `2**precision_bits`, fixing the residual on the largest bucket, then divide back to float64. Deterministic and idempotent.
  - `top_k_filter(dist, k) -> TokenDistribution` and `top_p_filter(dist, p) -> TokenDistribution` — keep the top-k / nucleus, renormalize, preserve original `token_ids`.

- [ ] **Step 1: Write the failing test**

Create `tests/text/test_lm_common_pmf.py`:

```python
import numpy as np
import pytest

from stegolab.text import lm_common as lm


def test_token_distribution_validation():
    d = lm.TokenDistribution(np.array([0, 1, 2]), np.array([0.2, 0.5, 0.3]))
    assert len(d.token_ids) == 3
    with pytest.raises(ValueError):
        lm.TokenDistribution(np.array([0, 1]), np.array([1.0]))           # length mismatch
    with pytest.raises(ValueError):
        lm.TokenDistribution(np.array([0, 1]), np.array([0.1, 0.1]))      # sum != 1


def test_softmax_is_stable_and_normalized():
    p = lm.softmax(np.array([1000.0, 1000.0, 1000.0]))  # no overflow
    assert np.allclose(p, [1 / 3, 1 / 3, 1 / 3])
    assert np.isclose(p.sum(), 1.0)


def test_quantize_sums_to_one_and_is_idempotent():
    rng = np.random.default_rng(0)
    p = lm.softmax(rng.standard_normal(50))
    q = lm.quantize_pmf(p, precision_bits=16)
    assert np.isclose(q.sum(), 1.0, atol=1e-9)
    assert np.array_equal(q, lm.quantize_pmf(q, precision_bits=16))  # idempotent


def test_quantize_is_stable_under_subgrid_noise_once_on_grid():
    # Once a pmf is ON the grid, perturbing it by far less than a grid step quantizes
    # back to the same grid point (stability/idempotence) — this is NOT a claim that two
    # arbitrary pmfs near a rounding boundary agree.
    rng = np.random.default_rng(1)
    q = lm.quantize_pmf(lm.softmax(rng.standard_normal(40)), 16)  # snap onto the grid
    noise = rng.standard_normal(40) * (1e-3 / (1 << 16))          # << half a grid step
    assert np.array_equal(q, lm.quantize_pmf(np.clip(q + noise, 0, None), 16))


def test_quantize_stays_non_negative_for_large_near_uniform_vocab():
    # Largest-remainder apportionment keeps every count >= 0 even for a near-uniform pmf
    # over a large vocab (where a naive single-bucket residual dump could go negative).
    rng = np.random.default_rng(2)
    p = lm.normalize(np.ones(400) + rng.standard_normal(400) * 1e-3)
    q = lm.quantize_pmf(p, 16)
    assert np.all(q >= 0)
    assert np.isclose(q.sum(), 1.0, atol=1e-9)


def test_top_k_filter():
    d = lm.TokenDistribution(np.array([10, 11, 12, 13]), np.array([0.1, 0.4, 0.3, 0.2]))
    out = lm.top_k_filter(d, 2)
    assert set(out.token_ids.tolist()) == {11, 12}  # the two largest
    assert np.isclose(out.probs.sum(), 1.0)


def test_top_p_filter():
    d = lm.TokenDistribution(np.array([0, 1, 2, 3]), np.array([0.5, 0.3, 0.15, 0.05]))
    out = lm.top_p_filter(d, 0.8)  # 0.5 + 0.3 = 0.8 covers the nucleus
    assert set(out.token_ids.tolist()) == {0, 1}
    assert np.isclose(out.probs.sum(), 1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/text/test_lm_common_pmf.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.text.lm_common'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/stegolab/text/lm_common.py`:

```python
"""Deterministic language-model layer: token distributions, PMF quantization,
CSPRNG keystream, and providers. Pure NumPy + stdlib — NO torch/transformers here
(the torch adapter lives in lm_transformers.py). Spec §7.2, §8.6, §9.7-9.8, §16.3.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np


@dataclass
class TokenDistribution:
    token_ids: np.ndarray
    probs: np.ndarray

    def __post_init__(self) -> None:
        self.token_ids = np.asarray(self.token_ids, dtype=np.int64)
        self.probs = np.asarray(self.probs, dtype=np.float64)
        if self.token_ids.shape != self.probs.shape:
            raise ValueError("token_ids and probs must have the same shape")
        if np.any(self.probs < 0):
            raise ValueError("probs must be non-negative")
        if self.probs.size and not np.isclose(self.probs.sum(), 1.0, atol=1e-6):
            raise ValueError(f"probs must sum to 1.0 (got {self.probs.sum()})")


def softmax(logits: np.ndarray) -> np.ndarray:
    logits = np.asarray(logits, dtype=np.float64)
    m = logits.max()
    e = np.exp(logits - m)
    return e / e.sum()


def normalize(probs: np.ndarray) -> np.ndarray:
    probs = np.asarray(probs, dtype=np.float64)
    total = probs.sum()
    if total <= 0:
        raise ValueError("cannot normalize a zero-sum distribution")
    return probs / total


def quantize_pmf(probs: np.ndarray, precision_bits: int = 16) -> np.ndarray:
    """Round to a 1/2**precision_bits grid: integer counts in [floor, floor+1] summing to
    2**precision_bits via largest-remainder (Hamilton) apportionment. Every count stays
    non-negative, the sum is exact, and the result is deterministic and idempotent.

    NOTE: this is bit-identical for inputs already on the grid (and for sub-grid
    perturbations of such inputs); it does NOT reconcile two machines whose float softmax
    differs near a grid boundary — cross-machine agreement requires the provider to
    reproduce the float logits bit-identically (eval mode, fixed precision)."""
    probs = np.asarray(probs, dtype=np.float64)
    scale = 1 << precision_bits
    scaled = probs * scale
    counts = np.floor(scaled).astype(np.int64)
    residual = scale - int(counts.sum())
    if residual > 0:
        order = np.argsort(-(scaled - counts), kind="stable")[:residual]
        counts[order] += 1  # give the +1s to the largest fractional remainders
    return counts.astype(np.float64) / scale


def top_k_filter(dist: TokenDistribution, k: int) -> TokenDistribution:
    if k >= dist.probs.size:
        return dist
    keep = np.argsort(-dist.probs, kind="stable")[:k]
    keep.sort()
    return TokenDistribution(dist.token_ids[keep], normalize(dist.probs[keep]))


def top_p_filter(dist: TokenDistribution, p: float) -> TokenDistribution:
    order = np.argsort(-dist.probs, kind="stable")
    csum = np.cumsum(dist.probs[order])
    n = int(np.searchsorted(csum, p) + 1)
    n = min(n, dist.probs.size)
    keep = np.sort(order[:n])
    return TokenDistribution(dist.token_ids[keep], normalize(dist.probs[keep]))


class Provider(Protocol):
    def next_distribution(self, context: Sequence[int]) -> TokenDistribution: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/text/test_lm_common_pmf.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/text/lm_common.py tests/text/test_lm_common_pmf.py
git commit -m "feat(text): deterministic LM token-distribution + PMF quantization"
```

---

### Task 2: `KeyStream` — CSPRNG keystream (HMAC-SHA256 counter mode)

**Files:**
- Modify: `src/stegolab/text/lm_common.py` (append `KeyStream`)
- Test: `tests/text/test_lm_keystream.py`

**Interfaces:**
- Consumes: `hashlib`, `hmac`.
- Produces: `class KeyStream(key: str, nonce: bytes = b"")` with `bytes(n) -> bytes`, `random() -> float` (uniform in `[0,1)`, 53-bit), `randint(n) -> int` (uniform in `[0, n)`). Deterministic per `(key, nonce)`; different keys → different streams.

- [ ] **Step 1: Write the failing test**

Create `tests/text/test_lm_keystream.py`:

```python
import numpy as np

from stegolab.text.lm_common import KeyStream


def test_deterministic_for_same_key():
    a = KeyStream("course-demo")
    b = KeyStream("course-demo")
    assert a.bytes(64) == b.bytes(64)


def test_different_keys_differ():
    assert KeyStream("k1").bytes(64) != KeyStream("k2").bytes(64)


def test_nonce_changes_stream():
    assert KeyStream("k", b"n1").bytes(32) != KeyStream("k", b"n2").bytes(32)


def test_random_in_unit_interval_and_uniformish():
    ks = KeyStream("seed")
    xs = np.array([ks.random() for _ in range(5000)])
    assert xs.min() >= 0.0 and xs.max() < 1.0
    assert abs(xs.mean() - 0.5) < 0.03  # rough uniformity


def test_randint_range_and_determinism():
    a = KeyStream("k")
    b = KeyStream("k")
    va = [a.randint(7) for _ in range(100)]
    vb = [b.randint(7) for _ in range(100)]
    assert va == vb
    assert all(0 <= v < 7 for v in va)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/text/test_lm_keystream.py -v`
Expected: FAIL — `ImportError: cannot import name 'KeyStream'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/stegolab/text/lm_common.py`:

```python
class KeyStream:
    """Deterministic CSPRNG keystream: HMAC-SHA256 in counter mode (spec §8.6).

    The key is the secret driving generative-stego sampling. Same (key, nonce) ->
    same stream; different key -> different stream. Not a general-purpose RNG seed
    substitute — it is the keyed entropy source for ANS/iMEC.
    """

    def __init__(self, key: str, nonce: bytes = b""):
        self._key = hashlib.sha256(b"stegolab-keystream\x00" + key.encode("utf-8")).digest()
        self._nonce = nonce
        self._counter = 0
        self._buf = bytearray()

    def _refill(self) -> None:
        msg = self._nonce + self._counter.to_bytes(8, "big")
        self._counter += 1
        self._buf += hmac.new(self._key, msg, hashlib.sha256).digest()

    def bytes(self, n: int) -> bytes:
        while len(self._buf) < n:
            self._refill()
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def random(self) -> float:
        val = int.from_bytes(self.bytes(8), "big") >> 11  # top 53 bits
        return val / float(1 << 53)

    def randint(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be positive")
        # rejection sampling for an unbiased value in [0, n)
        limit = (1 << 32) - ((1 << 32) % n)
        while True:
            x = int.from_bytes(self.bytes(4), "big")
            if x < limit:
                return x % n
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/text/test_lm_keystream.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/text/lm_common.py tests/text/test_lm_keystream.py
git commit -m "feat(text): HMAC-SHA256 CSPRNG keystream for generative stego"
```

---

### Task 3: `MockProvider` — deterministic synthetic distributions

**Files:**
- Modify: `src/stegolab/text/lm_common.py` (append `MockProvider`)
- Test: `tests/text/test_lm_mock_provider.py`

**Interfaces:**
- Consumes: `hashlib`, NumPy, `TokenDistribution`.
- Produces: `class MockProvider(vocab_size: int = 64, seed: int = 0)` implementing `Provider`. `next_distribution(context)` hashes `(seed, context)` to seed a NumPy `Generator`, draws standard-normal logits over `vocab_size`, returns a softmax `TokenDistribution`. Deterministic per `(seed, context)`; different contexts → different distributions. No torch, no network.

- [ ] **Step 1: Write the failing test**

Create `tests/text/test_lm_mock_provider.py`:

```python
import numpy as np

from stegolab.text.lm_common import MockProvider, TokenDistribution


def test_returns_valid_distribution():
    p = MockProvider(vocab_size=32)
    d = p.next_distribution([1, 2, 3])
    assert isinstance(d, TokenDistribution)
    assert d.probs.size == 32
    assert np.isclose(d.probs.sum(), 1.0)


def test_deterministic_for_same_context():
    p = MockProvider(vocab_size=50, seed=7)
    d1 = p.next_distribution([5, 9, 1])
    d2 = MockProvider(vocab_size=50, seed=7).next_distribution([5, 9, 1])
    assert np.array_equal(d1.probs, d2.probs)


def test_different_context_differs():
    p = MockProvider(vocab_size=50, seed=7)
    assert not np.array_equal(
        p.next_distribution([1, 2]).probs, p.next_distribution([1, 3]).probs
    )


def test_different_seed_differs():
    a = MockProvider(vocab_size=40, seed=1).next_distribution([1])
    b = MockProvider(vocab_size=40, seed=2).next_distribution([1])
    assert not np.array_equal(a.probs, b.probs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/text/test_lm_mock_provider.py -v`
Expected: FAIL — `ImportError: cannot import name 'MockProvider'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/stegolab/text/lm_common.py`:

```python
class MockProvider:
    """Deterministic synthetic next-token distribution for CI/tests (spec §16.3).

    No model, no network: hashes (seed, context) into a NumPy Generator and draws a
    softmax over a fixed vocabulary. Lets ANS/iMEC round-trips be reproducible offline.
    """

    def __init__(self, vocab_size: int = 64, seed: int = 0):
        self.vocab_size = int(vocab_size)
        self._seed = int(seed)
        self._token_ids = np.arange(self.vocab_size, dtype=np.int64)

    def next_distribution(self, context: Sequence[int]) -> TokenDistribution:
        ctx = ",".join(str(int(t)) for t in context)
        digest = hashlib.sha256(f"{self._seed}:{ctx}".encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
        logits = rng.standard_normal(self.vocab_size)
        return TokenDistribution(self._token_ids.copy(), softmax(logits))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/text/test_lm_mock_provider.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/stegolab/text/lm_common.py tests/text/test_lm_mock_provider.py
git commit -m "feat(text): deterministic MockProvider for offline generative-stego tests"
```

---

### Task 4: `TransformersProvider` — real-model adapter (torch-isolated)

**Files:**
- Create: `src/stegolab/text/lm_transformers.py`
- Modify: `pyproject.toml` (add the `linguistic` optional-dependencies extra)
- Test: `tests/text/test_lm_transformers.py`

**Interfaces:**
- Consumes: `torch`, `transformers` (import-guarded), `lm_common.{TokenDistribution, quantize_pmf}`.
- Produces:
  - `class TransformersProvider(model, *, precision_bits: int = 16)` implementing `Provider`; `next_distribution(context)` runs a no-grad forward pass, takes the last-token logits, softmaxes in float64, quantizes via `quantize_pmf`, and returns a `TokenDistribution` over the full vocabulary.
  - `TransformersProvider.tiny_for_test(vocab_size=64, seed=0)` — builds a small from-config GPT-2 (random seeded weights, **no download**) for tests.
  - `TransformersProvider.from_pretrained(model_id, revision=None)` — loads a real causal LM in eval mode (used at runtime; not exercised by CI).

- [ ] **Step 1: Add the `linguistic` extra**

In `pyproject.toml`, under `[project.optional-dependencies]`, add:

```toml
linguistic = [
    "torch>=2.2",
    "transformers>=4.40",
    "huggingface-hub>=0.23",
]
```

- [ ] **Step 2: Write the failing test**

Create `tests/text/test_lm_transformers.py`:

```python
import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from stegolab.text.lm_common import TokenDistribution
from stegolab.text.lm_transformers import TransformersProvider


def test_tiny_model_distribution_is_valid():
    p = TransformersProvider.tiny_for_test(vocab_size=48, seed=0)
    d = p.next_distribution([1, 2, 3, 4])
    assert isinstance(d, TokenDistribution)
    assert d.probs.size == 48
    assert np.isclose(d.probs.sum(), 1.0, atol=1e-9)


def test_distribution_is_deterministic_across_calls():
    p = TransformersProvider.tiny_for_test(vocab_size=48, seed=0)
    d1 = p.next_distribution([1, 2, 3, 4])
    d2 = p.next_distribution([1, 2, 3, 4])
    assert np.array_equal(d1.probs, d2.probs)


def test_same_seed_models_agree_bit_exact():
    # The cross-instance determinism guarantee that ANS/iMEC rely on.
    a = TransformersProvider.tiny_for_test(vocab_size=48, seed=123)
    b = TransformersProvider.tiny_for_test(vocab_size=48, seed=123)
    da = a.next_distribution([5, 6, 7])
    db = b.next_distribution([5, 6, 7])
    assert np.array_equal(da.probs, db.probs)


def test_output_is_quantized():
    p = TransformersProvider.tiny_for_test(vocab_size=48, seed=0, precision_bits=16)
    d = p.next_distribution([1, 2])
    scaled = d.probs * (1 << 16)
    assert np.allclose(scaled, np.round(scaled))  # every prob lies on the grid
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/text/test_lm_transformers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stegolab.text.lm_transformers'`.

- [ ] **Step 4: Write minimal implementation**

Create `src/stegolab/text/lm_transformers.py`:

```python
"""Torch/Transformers adapter for the deterministic LM layer (spec §9.7-9.8, §18.4).

Isolated here so lm_common.py stays import-light. Deterministic inference: eval mode,
no grad, float64 softmax, fixed-grid PMF quantization. Tested against a tiny from-config
model (no download); the real model is fetched once via models/fetch_models.py.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .lm_common import TokenDistribution, quantize_pmf


class TransformersProvider:
    def __init__(self, model, *, precision_bits: int = 16):
        import torch

        self._torch = torch
        self._model = model.eval()
        self._precision_bits = precision_bits
        self._vocab = int(model.config.vocab_size)

    @classmethod
    def tiny_for_test(cls, vocab_size: int = 64, seed: int = 0, *, precision_bits: int = 16) -> "TransformersProvider":
        import torch
        from transformers import GPT2Config, GPT2LMHeadModel

        torch.manual_seed(seed)
        config = GPT2Config(vocab_size=vocab_size, n_positions=64, n_embd=16, n_layer=2, n_head=2)
        model = GPT2LMHeadModel(config)
        return cls(model, precision_bits=precision_bits)

    @classmethod
    def from_pretrained(cls, model_id: str, revision: str | None = None, *, precision_bits: int = 16) -> "TransformersProvider":
        from transformers import AutoModelForCausalLM

        model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision)
        return cls(model, precision_bits=precision_bits)

    def next_distribution(self, context: Sequence[int]) -> TokenDistribution:
        torch = self._torch
        ids = torch.tensor([[int(t) for t in context]], dtype=torch.long)
        with torch.no_grad():
            logits = self._model(input_ids=ids).logits[0, -1, :]
        probs = torch.softmax(logits.double(), dim=-1).cpu().numpy()
        probs = quantize_pmf(probs, self._precision_bits)
        return TokenDistribution(np.arange(self._vocab, dtype=np.int64), probs)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/text/test_lm_transformers.py -v`
Expected: PASS (4 passed). (If torch/transformers were absent, all 4 would SKIP — that is the intended CI behavior.)

- [ ] **Step 6: Commit**

```bash
git add src/stegolab/text/lm_transformers.py pyproject.toml tests/text/test_lm_transformers.py
git commit -m "feat(text): torch-isolated TransformersProvider with deterministic inference"
```

---

### Task 5: Model fetch + checksum verify

**Files:**
- Create: `models/MODEL_CARD.md`
- Create: `models/fetch_models.py`
- Test: `tests/models/test_fetch_verify.py`

**Interfaces:**
- Consumes: `hashlib`, `pathlib`.
- Produces:
  - `PINNED_MODELS: dict` — the pinned causal LM (`repo_id`, `revision`, optional per-file `sha256`).
  - `verify_file(path, expected_sha256) -> bool` — streams the file and compares its SHA-256.
  - `fetch(model_key, dest=None, *, consent=False) -> str` — install-time only: requires `consent=True` (else raises `RuntimeError`), downloads via `huggingface_hub.snapshot_download(repo_id, revision=...)`, returns the local path. Not run by tests.

- [ ] **Step 1: Write the failing test**

Create `tests/models/test_fetch_verify.py`:

```python
import hashlib

import pytest

from models import fetch_models as fm


def test_verify_file_matches(tmp_path):
    p = tmp_path / "blob.bin"
    data = b"deterministic content " * 100
    p.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    assert fm.verify_file(p, digest) is True
    assert fm.verify_file(p, "0" * 64) is False


def test_pinned_models_has_a_causal_lm():
    assert "causal_lm" in fm.PINNED_MODELS
    entry = fm.PINNED_MODELS["causal_lm"]
    assert "repo_id" in entry and "revision" in entry


def test_fetch_requires_consent():
    with pytest.raises(RuntimeError):
        fm.fetch("causal_lm", consent=False)  # must never download without explicit consent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/models/test_fetch_verify.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models'`.

- [ ] **Step 3: Write minimal implementation**

First, make the root-level `models` package importable under pytest. In `pyproject.toml`, change the pytest `pythonpath` line to include the repo root:

```toml
pythonpath = ["src", "."]
```

> Do NOT create `tests/models/__init__.py`. With pytest's default prepend import mode, a `tests/models/__init__.py` would turn the test directory into a top-level package literally named `models`, shadowing the repo-root `models` package and aborting collection. Leaving it out (matching `tests/cli`/`tests/core`) lets `from models import fetch_models` resolve to the real package via the `"."` path entry.

Create `models/MODEL_CARD.md`:

```markdown
# StegoLab bundled models

| Key | Repo | Revision | Purpose | Approx size | License |
|---|---|---|---|---|---|
| `causal_lm` | `distilgpt2` | `main` (pin a commit before release) | Next-token provider for `text-ans-generative` and `text-mec` | ~330 MB | Apache-2.0 |

Models are fetched **once at install time** via `python -m models.fetch_models` (explicit
consent) and cached locally. The library never downloads at runtime (spec §20.1).
Pin `revision` to a specific commit hash and fill in per-file SHA-256 checksums before release.
```

Create `models/__init__.py`:

```python
"""StegoLab bundled-model fetch + verification (install-time only)."""
```

Create `models/fetch_models.py`:

```python
"""Install-time model fetch + checksum verification (spec §18.2, §20.1).

Never imported or invoked by the library at runtime. Run explicitly:
    python -m models.fetch_models
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PINNED_MODELS: dict = {
    "causal_lm": {
        "repo_id": "distilgpt2",
        # Pin to a specific commit hash before release; "main" is a placeholder.
        "revision": "main",
        "sha256": {},  # fill per-file checksums before release
    },
}


def verify_file(path, expected_sha256: str) -> bool:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == expected_sha256


def fetch(model_key: str, dest=None, *, consent: bool = False) -> str:
    if not consent:
        raise RuntimeError(
            "Refusing to download a model without explicit consent. "
            "Re-run with consent=True (this is a one-time install step; spec §20.1)."
        )
    if model_key not in PINNED_MODELS:
        raise KeyError(f"unknown model key: {model_key}")
    entry = PINNED_MODELS[model_key]
    from huggingface_hub import snapshot_download

    local = snapshot_download(repo_id=entry["repo_id"], revision=entry["revision"],
                              local_dir=str(dest) if dest else None)
    return local


if __name__ == "__main__":  # pragma: no cover
    path = fetch("causal_lm", consent=True)
    print(f"fetched causal_lm -> {path}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/models/test_fetch_verify.py -v`
Expected: PASS (3 passed). `test_fetch_requires_consent` confirms no download happens without consent (so the test never touches the network).

- [ ] **Step 5: Run the FULL suite**

Run: `python -m pytest -q`
Expected: PASS — 109 (Plan 03) + 7 + 5 + 4 + 4 + 3 = **132 passed** (or 128 passed + 4 skipped if torch/transformers are absent). Confirm no import error and no network access.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml models/__init__.py models/MODEL_CARD.md models/fetch_models.py tests/models/test_fetch_verify.py
git commit -m "feat(models): pinned-model fetch with checksum verify (install-time)"
```

---

## Self-Review

**1. Spec coverage (Plan 04 scope = M7 lm_common + bundled models):**
- Deterministic next-token provider (§9.7-9.8, §16.3): `Provider` protocol + `MockProvider` (CI) + `TransformersProvider` (real, tiny-model-tested). ✓
- PMF quantization for cross-machine determinism (§9.7-9.8): `quantize_pmf` + the sub-grid-noise-robustness test. ✓
- CSPRNG keystream (§8.6): `KeyStream` (HMAC-SHA256 counter mode). ✓
- torch isolated from the import-light core (§18.4): `lm_common` is torch-free; torch only in `lm_transformers`, import-guarded; the `linguistic` extra groups the heavy deps. ✓
- Bundled-model policy + no runtime network (§18.2, §20.1): `models/fetch_models.py` is install-time, consent-gated, checksum-verified; never invoked at runtime or by tests. ✓
- Mock-for-CI / real-marked (§16.3): real-model tests `importorskip` torch/transformers. ✓
- Deferred to Plan 05 by design: top_p/top_k integer-frequency coding, the ANS and minimum-entropy-coupling coders, the actual `text-ans-generative`/`text-mec` methods, and wiring a real bundled model end-to-end. This plan delivers only the shared layer they consume.

**2. Placeholder scan:** No `TBD`/`TODO`/vague steps. (The `MODEL_CARD.md`/`PINNED_MODELS` "pin a commit / fill checksums before release" notes are explicit release-checklist items with working defaults, not implementation gaps.)

**3. Type consistency:** `TokenDistribution`/`quantize_pmf` (Task 1) are consumed by `MockProvider` (Task 3) and `TransformersProvider` (Task 4) with matching signatures. `MockProvider` (Task 3) and `TransformersProvider` (Task 4) both implement the `Provider` protocol shape (`next_distribution(context) -> TokenDistribution`); `KeyStream` (Task 2) is the keyed CSPRNG entropy source (`bytes`/`random`/`randint`) consumed *alongside* a `Provider` during sampling, not a `Provider` itself. `verify_file`/`fetch`/`PINNED_MODELS` (Task 5) match the test usage. No torch symbol is referenced from `lm_common`.

> **Note for reviewers / executor:** Task 4 touches torch + transformers 5.3. The exact API used (`GPT2Config`, `GPT2LMHeadModel`, `model(input_ids=...).logits`, `torch.softmax(...double())`) was verified working and bit-exact-deterministic on this environment before the plan was written. If executing where the API differs, only `lm_transformers.py` is affected; consider running that task's implementer on a stronger model than the pure-Python tasks.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-28-stegolab-04-lm-layer.md`. This is Plan 04 of 08; it builds the deterministic LM layer that Plan 05's SOTA generative text methods consume. Two execution options:

**1. Subagent-Driven (recommended)** — fresh implementer per task, review between tasks.

**2. Inline Execution** — batch execution with checkpoints.
