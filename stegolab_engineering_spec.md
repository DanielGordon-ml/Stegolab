# StegoLab Engineering Specification

**Status:** Approved for implementation
**Version:** 1.0
**Date:** 2026-06-28
**Primary audience:** Engineering team, course staff, graduate-level cybersecurity students
**Project type:** Educational and research steganography demo codebase and notebooks
**Working name:** `stegolab`


---

## 1. Executive Summary

`stegolab` is an educational steganography codebase for hiding and extracting either text or image payloads inside either text or image covers. The project must provide:

1. A CLI for repeatable demonstrations and tests.
2. A lightweight UI for classroom/research interaction.
3. Jupyter notebooks explaining concepts, algorithms, capacity, detectability, and extraction.
4. A shared payload framing format so extraction can recover metadata and payload integrity across methods.
5. Baseline algorithms students can inspect and understand.
6. State-of-the-art (SOTA) algorithms that present research students with the current frontier, spanning all three text-steganography paradigms: format/encoding-based, linguistic edit-based, and generative.
7. Advanced adapters and notebooks connecting the baseline demos to modern image and linguistic steganography research.

The project is intended for Tel Aviv University graduate-level cybersecurity instruction and research. It must favor clarity, reproducibility, and SOTA methods while keeping a clear, visible safety and ethics framing.

---

## 2. Goals and Non-Goals

### 2.1 Goals

The implementation must support the following core flows. Each flow maps to a concrete method ID defined in §6.3 and specified in §9.

| Payload to hide | Cover to hide in | Method(s) | MVP? | Notes |
|---|---|---|---|---|
| Text | Image | `image-lsb`, `image-randomized-lsb`, `image-edge-adaptive-lsb` | Yes | Lossless image formats, primarily PNG. |
| Image | Image | `image-bitplane` | Yes | Visual bit-plane image-in-image demo. |
| Text/bytes | Image | `image-edge-adaptive-lsb` | Yes | Adaptive ("advanced bit manipulation") placement in high-variance regions. |
| Text | Text | `text-zero-width` | Yes | Invisible Unicode (zero-width) channel; supplied cover. |
| Text | Text | `text-mlm-substitution` | Yes | Linguistic edit-based; masked-LM word substitution into a supplied cover. SOTA-class. |
| Text | Generated text | `text-ans-generative` | Yes | Generative; ANS entropy coding over LM token probabilities (capacity-first). |
| Text | Generated text | `text-mec` | Yes | Generative; minimum-entropy-coupling / iMEC (security-first, provably/perfectly secure). |

The product must include:

- Hide and extract operations.
- Capacity estimation before embedding.
- Payload integrity checks after extraction.
- Visual/textual analysis comparing cover and stego artifacts.
- Attack/robustness demonstrations showing fragility of naive methods.
- Course notebooks that explain the methods without requiring students to read implementation internals first.

> **On "generated text" covers.** `text-ans-generative` and `text-mec` are *generative*: they synthesize new cover text from a language model rather than hiding into a user-supplied cover. They satisfy the "hide text in text" learning goal by a different mechanism than the cover-modification methods. The CLI/UI/API surface this difference explicitly (see §9.7, §9.8, §10.2).

### 2.2 Non-Goals

The MVP must not attempt to be an operational covert-communications system.

The MVP must not include:

- Network transport, messaging-platform integrations, email automation, or social-media posting.
- Claims that naive methods are undetectable.
- Malware-style persistence, automated exfiltration, or covert command-and-control features.
- Anti-forensic workflows intended to defeat deployed monitoring systems.
- Large-scale stego generation for evasion benchmarking outside controlled course datasets.

Advanced research modules should explain modern methods, but they must be framed as educational references and controlled local experiments.

---

## 3. Research Basis

This section summarizes the research and implementation references that motivate the spec.

### 3.1 Image Steganography

For the course demo, image methods are split into three tiers:

| Tier | Methods | Implementation role |
|---|---|---|
| Introductory | LSB replacement/matching, randomized LSB, **edge-adaptive LSB**, bit-plane image-in-image | Required MVP. Fully inspectable and deterministic. |
| Classical adaptive | S-UNIWARD, J-UNIWARD, UERD, nsF5, STC-based embedding | Optional adapters and advanced notebooks (Phase 4). |
| Neural/generative | Invertible neural networks and related deep hiding methods | Research notebook only unless explicitly prioritized later. |

Relevant references:

- [Stegano documentation](https://stegano.readthedocs.io/) for a Python LSB-oriented baseline, command-line usage, generators, image description fields, and parity steganalysis.
- [Stegano PyPI project](https://pypi.org/project/stegano/) for the distinction between hiding and encryption.
- [Universal Distortion Function for Steganography in an Arbitrary Domain](https://link.springer.com/article/10.1186/1687-417X-2014-1) for UNIWARD-family distortion minimization.
- [HStego](https://github.com/daniellerch/hstego), which implements J-UNIWARD with cost polarization for JPEG images and S-UNIWARD for bitmap images.
- [ConSeal](https://github.com/uibk-uncover/conseal), which provides simulators for JPEG steganography methods including J-UNIWARD, UERD, and nsF5.
- [Binghamton DDE Steganographic Algorithms](https://dde.binghamton.edu/download/stego_algorithms/) for research implementations of spatial, JPEG, and side-informed JPEG algorithms.
- [Large-Capacity Image Steganography Based on Invertible Neural Networks](https://openaccess.thecvf.com/content/CVPR2021/papers/Lu_Large-Capacity_Image_Steganography_Based_on_Invertible_Neural_Networks_CVPR_2021_paper.pdf) for image-in-image deep steganography research context.

### 3.2 Text Steganography

Text methods are split into three paradigms. The MVP ships at least one runnable method from each paradigm, so students can directly compare the capacity-vs-security-vs-robustness trade-offs ("the steganography trilemma").

| Paradigm | Method(s) | Implementation role |
|---|---|---|
| Format/encoding-based (cover-modification) | Zero-width Unicode, Unicode whitespace, punctuation/spacing channels | `text-zero-width` is Required MVP (Phase 1). `text-unicode-whitespace` is Phase 3 (see §6.3). Deterministic and easy to inspect. |
| Linguistic edit-based (cover-modification) | Masked-language-model / synonym substitution into a supplied cover, syntactic transforms | `text-mlm-substitution` is Required MVP. SOTA-class, supplied-cover, exact recovery. |
| Generative (synthesizes the cover) | ANS / arithmetic-coding payload coding; minimum-entropy-coupling; distribution-copy sampling | `text-ans-generative` (capacity-first) and `text-mec` (security-first, perfect security) are Required MVP. Discop, SparSamp, ANStega, SAAC, SA-ANS are covered in the research notebook (Phase 5). |

Relevant references:

- [Unicode Steganography with Zero-Width Characters](https://330k.github.io/misc_tools/unicode_steganography.html) for practical zero-width character mapping and platform caveats.
- [Perfectly Secure Steganography Using Minimum Entropy Coupling](https://arxiv.org/abs/2210.14889) (Schroeder de Witt, Sokota, Kolter, Foerster, Strohmeier; ICLR 2023) — the theoretical and practical basis for `text-mec`. Reference implementation: [`ssokota/mec`](https://github.com/ssokota/mec) (MIT-licensed).
- [Discop: Provably Secure Steganography in Practice Based on "Distribution Copies"](https://dingjinyang.github.io/uploads/Discop_sp23_paper.pdf) (Ding, Chen, Wang, Zhao, Zhang, Yu; IEEE S&P 2023, DOI 10.1109/SP46215.2023.10179287) — distribution-preserving sampling; research-notebook contrast to `text-mec`.
- [Near-imperceptible Neural Linguistic Steganography via Self-Adjusting Arithmetic Coding](https://aclanthology.org/2020.emnlp-main.22/) for SAAC.
- [Linguistic Steganography via Self-Adjusting Asymmetric Numeral Systems](https://direct.mit.edu/coli/article/52/1/113/132854/Linguistic-Steganography-via-Self-Adjusting) for SA-ANS (motivates `text-ans-generative`).
- [SparSamp: Efficient Provably Secure Steganography Based on Sparse Sampling](https://www.usenix.org/conference/usenixsecurity25/presentation/wang-yaofei) (USENIX Security 2025) for the efficiency frontier of provably-secure generative steganography.
- [Breaking the Generative Steganography Trilemma: ANStega](https://www.ndss-symposium.org/ndss-paper/breaking-the-generative-steganography-trilemma-anstega-for-optimal-capacity-efficiency-and-security/) for recent ANS-based generative stego research.

> **Provenance note.** Discop is an IEEE S&P (Oakland) 2023 paper. iMEC is ICLR 2023. Cite venues accordingly in notebooks and docs.

### 3.3 Datasets and Benchmarks

The MVP must ship only with small course-owned sample files and the bundled models (§18). Larger datasets must be documented as optional external resources and must not be redistributed in this repository.

References:

- [BOSSbase 1.01](https://dde.binghamton.edu/download/) for a classic image steganography/steganalysis dataset.
- [ALASKA#2](https://alaska.utt.fr/) for a realistic JPEG steganalysis benchmark using heterogeneous camera sources and JPEG stego algorithms.

---

## 4. Safety, Ethics, and Abuse Boundaries

The project must include a visible ethics and safety notice in:

- `README.md`
- CLI `--help` footer
- UI landing page
- Notebook `00_course_intro_and_ethics.ipynb`

Required message themes:

1. Steganography hides the existence of data; encryption protects the content. These are different controls.
2. The MVP methods are educational and often detectable or fragile.
3. The tool is for local defensive research.
4. The tool **must not** include network transport, covert communication automation, or exfiltration features.

Engineering requirements:

- The codebase **must not** include any module that sends stego files over a network.
- The codebase must not include integrations with email, messaging apps, social media, cloud drives, or paste services.
- Logs **must not** print recovered secret payload contents by default.
- The UI must not auto-upload files to any external service.

---

## 5. Product Requirements

### 5.1 Primary User Stories

#### Story 1: Hide text inside image

As a student, I want to hide a text message inside a PNG image so that I can understand LSB steganography and then extract the message back.

Acceptance criteria:

- CLI accepts a text payload and PNG cover.
- CLI writes a stego PNG.
- Extraction recovers the exact text bytes.
- Capacity failure is reported before modifying output.
- Analysis reports at least payload size, capacity, bits per pixel, PSNR, and SSIM.

#### Story 2: Hide image inside image

As a student, I want to hide a small image inside a larger image so that I can visualize bit planes and lossy reconstruction.

Acceptance criteria:

- CLI accepts hidden image and cover image.
- CLI writes stego image.
- Extraction recovers a viewable image.
- Notebook shows original hidden image, cover image, stego image, difference image, and recovered image.
- Documentation states whether the method is exact-byte preserving or visual reconstruction only.

#### Story 3: Hide text inside text (invisible Unicode)

As a student, I want to hide text inside ordinary-looking text so that I can inspect invisible Unicode channels and text normalization failures.

Acceptance criteria:

- CLI accepts UTF-8 payload text and UTF-8 cover text.
- CLI writes stego text (`text-zero-width`).
- Extraction recovers exact payload bytes before normalization.
- Attack mode can apply Unicode normalization and demonstrate extraction failure or corruption.
- Analysis reports invisible character count and capacity usage.

#### Story 4: Hide text inside text (linguistic edit-based, supplied cover)

As a student, I want to hide a message inside a supplied natural-language cover by substituting words so that I can study linguistic (semantic-level) steganography that survives Unicode normalization, unlike invisible-character methods.

Acceptance criteria:

- CLI accepts a UTF-8 payload and a UTF-8 natural-language cover text.
- CLI writes stego text whose *visible* words differ from the cover (`text-mlm-substitution`).
- Extraction recovers the **exact** payload bytes deterministically and **without requiring a language model at embed or extract time** (see §9.6 — the substitution resource is curated offline and candidate sets are reconstructed deterministically).
- Method reports the number of candidate substitution slots and the per-slot bit capacity.
- Analysis includes a visible word-level diff and a semantic-similarity summary.
- The method survives NFC/NFKC normalization (it is not an invisible-character method); the attack notebook demonstrates this contrast against `text-zero-width`.

#### Story 5: Hide text inside generated text (capacity-first generative)

As a student, I want to encode a message into machine-generated text so that I can study generative linguistic steganography and how payload bits map onto language-model token choices.

Acceptance criteria:

- CLI accepts a UTF-8 (or bytes) payload, a prompt/context, and a key.
- CLI generates and writes stego text (`text-ans-generative`).
- Extraction recovers the **exact** payload bytes given the same model, prompt, key, and decoding parameters.
- Capacity is reported by running the model (bits per token), not as a static slot count.
- Analysis reports embedded bits per token and a language-model perplexity summary.

#### Story 6: Hide text inside generated text (security-first, perfect security)

As a researcher, I want to encode a message into generated text using minimum-entropy coupling so that I can study *provably/perfectly secure* steganography where the emitted text distribution is (near-)indistinguishable from honest model sampling.

Acceptance criteria:

- CLI accepts a payload, prompt/context, and key.
- CLI generates and writes stego text (`text-mec`).
- Extraction recovers the payload with the documented near-exact guarantee (§9.8); any recovery failure is explicit (`CorruptedPayload` for a damaged frame header, `IntegrityCheckFailed` for a checksum mismatch), never silent corruption.
- Documentation states that this method is **near-exact** (probabilistic recovery, error bound documented), distinguishing "perfect *security*" from "perfect *reliability*."
- Analysis reports a distribution-preservation indicator (e.g., estimated KL/score) contrasting it with `text-ans-generative`.

#### Story 7: Compare cover and stego artifacts

As a teaching assistant, I want to compare cover and stego files so that students can see distortion and detectability.

Acceptance criteria:

- Image comparison includes side-by-side preview, difference heatmap, PSNR, SSIM, and histogram summary.
- Text comparison includes visible diff, codepoint diff, count of unusual Unicode characters, and normalization behavior; for generative methods it includes perplexity and a distribution-preservation indicator instead of codepoint diff.
- CLI and UI both expose comparison functionality.

---

## 6. Functional Requirements

### 6.1 Required Operations

The system must support these high-level operations:

| Operation | Description | Interfaces |
|---|---|---|
| `hide` | Embed payload into (or generate) a stego artifact. | CLI, UI, Python package API. |
| `extract` | Recover hidden payload from stego artifact. | CLI, UI, Python package API. |
| `capacity` | Estimate maximum embeddable payload for cover/method/params. | CLI, UI, Python package API. |
| `analyze` | Compare cover and stego artifacts. | CLI, UI, notebooks, Python package API. |
| `attack` | Apply controlled transformations and test extraction robustness. | CLI, UI, notebooks. |
| `demo` | Run canned demo flows using bundled sample files. | CLI, notebooks. |

### 6.2 Supported File Types

#### Payload files

| Payload type | Required support | Notes |
|---|---|---|
| `.txt` | Yes | UTF-8 default. Preserve exact bytes where possible. |
| `.md` | Yes | Treat as UTF-8 text payload. |
| `.png` | Yes | Required for image payload demos. |
| `.jpg` / `.jpeg` | Yes | Read as payload bytes for byte-preserving methods; can decode for visual bit-plane method. |
| Arbitrary binary file | Yes (CLI) / Phase 3 (UI) | Frame supports arbitrary bytes; the UI initially limits to text/image and adds binary in Phase 3. |

#### Cover files

| Cover type | Required support | Notes |
|---|---|---|
| PNG image | Yes | Primary image cover format. |
| BMP image | Phase 2 | Useful because lossless and simple. |
| JPEG image | Advanced only | Use adapter/simulator for JPEG-domain methods; do not use naive pixel LSB on JPEG output. |
| UTF-8 text | Yes | Primary text cover format (cover-modification methods). |
| Markdown text | Yes | Treat as UTF-8 text cover. |
| Prompt/model (no supplied cover) | Yes | For `text-ans-generative` and `text-mec`, the "cover" is a prompt + model distribution, not a file. |
| DOCX/PDF | Out of scope for MVP | May be discussed in class but not implemented initially. |

### 6.3 Required Steganography Methods

| Method ID | Phase | Payload types | Cover types | Recovery | Model |
|---|---|---|---|---|---|
| `image-lsb` | 1 | Text, image, bytes | PNG | Exact payload bytes | none |
| `image-randomized-lsb` | 1 | Text, image, bytes | PNG | Exact payload bytes; key required (unless `--allow-unkeyed`) | none |
| `image-edge-adaptive-lsb` | 1 | Text, image, bytes | PNG | Exact payload bytes; key optional | none |
| `image-bitplane` | 1 | Image | PNG | Visual reconstruction image | none |
| `text-zero-width` | 1 | Text, image, bytes | UTF-8 text | Exact payload bytes before normalization | none |
| `text-mlm-substitution` | 2 | Text, bytes | UTF-8 natural-language text | Exact payload bytes | none at runtime (resource curated offline with a masked LM) |
| `text-ans-generative` | 2 | Text, bytes | Prompt + causal LM | Exact payload bytes | causal LM |
| `text-mec` | 2 | Text, bytes | Prompt + causal LM | Near-exact (documented error bound) | causal LM |
| `text-unicode-whitespace` | 3 | Text, image, bytes | UTF-8 text | Exact payload bytes before whitespace normalization | none |
| `image-adaptive-wrapper` | 4 | Text, image, bytes | PNG/JPEG depending on adapter | Exact payload bytes if adapter supports it | optional |
| `lm-generated-text` (research) | 5 | Text/bytes | Prompt/model distribution | Method-dependent | optional |

> **MVP** = Phases 1–3 (see §21). Phases 1 and 2 deliver all required hide/extract methods; Phase 3 delivers analysis, attack, and the UI. `image-edge-adaptive-lsb` is the concrete realization of the "advanced bit manipulation" goal in §2.1.

---

## 7. System Architecture

### 7.1 Repository Layout

```text
stegolab/
  pyproject.toml
  README.md
  LICENSE
  SECURITY.md
  data/
    covers/
    payloads/
    outputs/
  models/                         # bundled model cards + download/verify scripts; weights cached locally (see §18)
    README.md
  src/stegolab/
    cli.py
    ui/
      streamlit_app.py
    core/
      frame.py                    # binary frame encode/parse (see §8)
      payload_codec.py            # payload <-> frame, compression orchestration
      capacity.py
      crypto_optional.py
      keys.py                     # KDF + deterministic PRNG (see §8.6)
      errors.py
      io.py
      types.py
    image/
      lsb.py
      randomized_lsb.py
      edge_adaptive_lsb.py
      bitplane_image.py
      adaptive_wrappers.py        # Phase 4 optional adapters
    text/
      zero_width.py
      unicode_whitespace.py       # Phase 3
      mlm_substitution.py
      lm_common.py                # deterministic LM inference, PMF quantization, tokenizer pinning
      ans_generative.py
      mec.py                      # minimum-entropy-coupling / iMEC
    eval/
      image_metrics.py
      text_metrics.py
      steganalysis_baselines.py
      attacks.py
      reports.py
  notebooks/
    00_course_intro_and_ethics.ipynb
    01_payload_framing_and_capacity.ipynb
    02_text_in_image_lsb.ipynb
    03_image_in_image_bitplanes.ipynb
    04_text_in_text_unicode.ipynb
    05_text_in_text_mlm_substitution.ipynb
    06_generative_text_stego_ans_and_mec.ipynb
    07_steganalysis_against_naive_lsb.ipynb
    08_adaptive_image_stego_suniward_juniward.ipynb
    09_frontier_generative_linguistic_stego_research.ipynb
  tests/
    test_frame_roundtrip.py
    test_roundtrip_image_lsb.py
    test_roundtrip_image_randomized_lsb.py
    test_roundtrip_image_edge_adaptive_lsb.py
    test_roundtrip_image_in_image.py
    test_roundtrip_text_zero_width.py
    test_roundtrip_text_mlm_substitution.py
    test_roundtrip_text_ans_generative.py
    test_text_mec_near_exact.py
    test_capacity_failures.py
    test_corruption_and_wrong_key.py
    test_normalization_breaks_text_stego.py
    test_cli_contracts.py
  docs/
    method_image_lsb.md
    method_image_edge_adaptive_lsb.md
    method_image_bitplane.md
    method_text_zero_width.md
    method_text_mlm_substitution.md
    method_text_ans_generative.md
    method_text_mec.md
    method_adaptive_methods.md
    method_linguistic_research.md
```

### 7.2 Package Boundaries

#### `core`

Responsible for:

- Payload framing and parsing (`frame.py`).
- Compression and optional encryption orchestration.
- Capacity calculations shared across methods.
- Key derivation and deterministic PRNG (`keys.py`).
- Type definitions.
- Common error handling.
- File I/O and MIME detection.

Must not contain method-specific embedding logic.

#### `image`

Responsible for:

- Image cover validation.
- Image payload preprocessing.
- Image stego embedding and extraction (LSB, randomized LSB, edge-adaptive LSB, bit-plane).
- Image-specific capacity calculations.
- Optional integration with advanced external algorithms (Phase 4).

#### `text`

Responsible for:

- Text cover validation.
- Cover-modification embedding/extraction (zero-width, whitespace, MLM substitution).
- Generative embedding/extraction (`ans_generative.py`, `mec.py`) on top of the shared deterministic LM layer (`lm_common.py`).
- Text-specific capacity calculations.
- Text normalization and inspection helpers.

`lm_common.py` owns all language-model determinism concerns (fixed-precision CPU inference, PMF quantization, tokenizer/model-revision pinning, CSPRNG keystream) so that `ans_generative.py` and `mec.py` share one reproducibility contract. `mlm_substitution.py` is **model-free at runtime**: it relies only on the shipped, version-pinned substitution resource (§9.6), not on `lm_common.py`.

#### `eval`

Responsible for:

- Cover/stego comparison metrics.
- Steganalysis demonstrations.
- Controlled robustness attacks.
- Report objects consumed by CLI/UI/notebooks.

#### `ui`

Responsible for:

- Streamlit application (see §11).
- Interactive hide/extract/analyze/attack workflows.
- No external uploads or network transmission of user files.

---

## 8. Shared Payload Framing Format

### 8.1 Requirement

All exact and near-exact payload methods must embed a self-describing framed payload rather than raw user bytes.

This enables:

- Recovery of original filename.
- Recovery of MIME type.
- Payload length validation.
- Checksum validation.
- A `recovery_class` flag distinguishing **exact** from **near-exact** methods.
- Future compatibility.
- Common extraction behavior across image and text methods.

### 8.2 Frame Fields

| Field | Type | Required? | Description |
|---|---|---:|---|
| `magic` | 8 ASCII bytes | Yes | Identifies a StegoLab frame. Value: `STEGOLAB`. |
| `version` | uint8 | Yes | Frame format version. MVP value: `1`. |
| `header_len` | uint16 | Yes | Byte length of the header block that follows the fixed prefix. |
| `payload_type` | uint8 enum | Yes | `0=text`, `1=image`, `2=bytes`. |
| `compression` | uint8 enum | Yes | `0=none`, `1=zlib`, `2=zstd` (Phase 3). |
| `encryption` | uint8 enum | Yes | `0=none`, `1=aes-256-gcm`, `2=chacha20-poly1305` (encryption is Phase 3). |
| `recovery_class` | uint8 enum | Yes | `0=exact`, `1=near-exact`. Set by the method. |
| `sha256` | 32 bytes | Yes | SHA-256 over the **original decoded payload bytes** (before compression/encryption). See §8.3. |
| `payload_len` | uint32 | Yes | Length of `payload_bytes` (after compression/encryption). |
| `original_filename` | uint16 length + UTF-8 | Yes | Sanitized basename only. No paths. |
| `mime_type` | uint16 length + UTF-8 | Yes | Detected or user-supplied MIME type. |
| `salt` | uint8 length + bytes | Conditional | Present iff `encryption != none`. |
| `nonce` | uint8 length + bytes | Conditional | Present iff `encryption != none`. |
| `payload_bytes` | `payload_len` bytes | Yes | Encoded payload bytes. |

### 8.3 Wire Format (concrete byte layout)

All multi-byte integers are **big-endian** (network order). Strings are UTF-8.

```text
Fixed prefix (11 bytes):
  [0:8]    magic            "STEGOLAB"
  [8]      version          uint8  = 1
  [9:11]   header_len       uint16 = length of the Header block below

Header block (header_len bytes), in order:
  payload_type     uint8
  compression      uint8
  encryption       uint8
  recovery_class   uint8
  sha256           32 bytes
  payload_len      uint32
  filename_len     uint16, then filename_len UTF-8 bytes
  mime_len         uint16, then mime_len UTF-8 bytes
  (if encryption != 0) salt_len  uint8, then salt bytes
  (if encryption != 0) nonce_len uint8, then nonce bytes

Payload:
  payload_bytes    payload_len bytes
```

Two-stage read: the extractor first reads the 11-byte fixed prefix to learn `header_len`, then reads exactly `header_len` header bytes, parses `payload_len`, then reads exactly `payload_len` payload bytes. Total framed size = `11 + header_len + payload_len`. This lets bit-level extractors (image LSB, zero-width) know precisely how many bits to read.

The `sha256` field is computed over the **original decoded payload bytes** (the bytes the user supplied / will receive), independent of compression and encryption. This validates end-to-end integrity of the recovered payload. When authenticated encryption is used (Phase 3), the AEAD tag additionally protects the ciphertext; the two checks are complementary.

### Frame overhead

`frame_overhead_bytes`, subtracted in every capacity formula in §9, is defined as:

```text
frame_overhead_bytes = 11 (fixed prefix) + header_len
header_len = 40 (fixed header fields: payload_type 1 + compression 1 + encryption 1
                 + recovery_class 1 + sha256 32 + payload_len 4)
           + 2 + len(original_filename)        # UTF-8 bytes
           + 2 + len(mime_type)                # UTF-8 bytes
           + (encryption != none ? 1 + len(salt) + 1 + len(nonce) : 0)
```

Because `original_filename` and `mime_type` are variable-length, overhead is **not** constant. Policy:

- When a payload is supplied to `hide`, compute `frame_overhead_bytes` **exactly** from the sanitized basename and detected MIME type.
- The bare `capacity` command (§10.4) has no payload, so it reports an **estimate** using a documented nominal assumption: empty `original_filename` and the default MIME `application/octet-stream` (24 bytes), unencrypted — i.e. `frame_overhead_bytes ≈ 11 + 40 + 2 + 0 + 2 + 24 = 79` bytes. The output must label this an estimate and note that the exact value depends on the payload's filename and MIME type.

### 8.4 Frame Rules

- Numeric fields use big-endian consistently (§8.3).
- Frame parsing must fail closed on malformed headers, unsupported versions, invalid lengths, or checksum mismatch.
- The frame must not store absolute filesystem paths.
- The frame must not execute, evaluate, or deserialize untrusted code (no `pickle`/`eval`; parse fields explicitly).
- The frame must be method-agnostic.
- Extraction must never overwrite existing user files unless `--overwrite` is explicitly provided.
- For `recovery_class = near-exact` methods, a checksum mismatch must raise `IntegrityCheckFailed` rather than emit possibly-corrupted output.

### 8.5 Compression

MVP:

- Support `none` and `zlib`.
- Default (`auto`): `zlib` for text-like / uncompressed payloads; `none` for already-compressed payloads (PNG/JPEG and other high-entropy inputs detected by extension/MIME/entropy heuristic).

Phase 3:

- Add `zstd` if dependency footprint is acceptable.

Compression must happen before optional encryption.

### 8.6 Keys, KDF, and Deterministic PRNG

To guarantee cross-platform reproducibility:

- Key-seeded position permutations (`image-randomized-lsb`, optional keyed slot selection in `text-zero-width`) derive their seed as `seed = SHA-256(utf8(key))` and feed it into a documented, version-pinned PRNG (NumPy `Generator(PCG64(seed_int))`) to drive a Fisher–Yates permutation. The exact algorithm is documented in the method docs so a third party can reproduce it.
- Generative methods (`text-ans-generative`, `text-mec`) use a CSPRNG **keystream** derived from the key; the key is the actual secret. The keystream construction (e.g., HMAC-SHA-256 / a stream cipher in counter mode) is documented and version-pinned.
- Phase 3 encryption derives keys from passphrases with a memory-hard KDF (Argon2id preferred; scrypt acceptable) and uses authenticated encryption (AES-256-GCM or ChaCha20-Poly1305).

### 8.7 Optional Encryption

MVP omits encryption implementation but reserves the frame fields (§8.2).

If implemented in Phase 3:

- Use authenticated encryption.
- Recommended construction: passphrase-derived key (Argon2id) plus AES-256-GCM or ChaCha20-Poly1305.
- The project must clearly state that encryption is separate from steganography.
- Wrong-key extraction must fail with a clear integrity/authentication error and must not produce corrupted output silently.

---

## 9. Method Specifications

## 9.1 `image-lsb`

### Purpose

Baseline text/image/byte payload hiding in a lossless image cover.

### Required cover formats

- PNG for MVP.
- BMP optional in Phase 2.

### Required payload formats

- Text payloads, image payloads as bytes, generic bytes.

### High-Level Algorithm Behavior

- Convert payload to the shared framed payload format.
- Convert framed payload bytes to a bitstream.
- Embed bits into selected least-significant bits of image channels.
- Write a lossless stego image.
- Extract by reading the selected least-significant bits, reconstructing frame bytes, parsing the frame, and validating checksum.

### Parameters

| Parameter | Required? | Default | Description |
|---|---:|---|---|
| `bits_per_channel` | No | `1` | Number of LSBs used per channel. Range `1`–`4`. |
| `channels` | No | `rgb` | Channels eligible for embedding. MVP: RGB only. |
| `scan_order` | No | `row-major` | Pixel/channel traversal order. |
| `compress` | No | `auto` | Compression mode. |
| `key` | No | None | Not used in sequential LSB. Warn if provided but unused. |

### Capacity Formula

```text
capacity_bits = width × height × 3 × bits_per_channel
capacity_bytes = floor(capacity_bits / 8) - frame_overhead_bytes
```

For RGBA inputs:

- MVP ignores alpha by default.
- UI must explain that modifying alpha may cause visible artifacts.

### Validation Requirements

- Reject lossy output formats for this method.
- Reject unsupported image modes unless converted explicitly.
- Refuse embedding if the payload frame exceeds capacity.
- Warn when `bits_per_channel > 1` because detectability and distortion increase.

### Extraction Requirements

- Require the same method parameters used during embedding.
- If the header cannot be found or parsed, return `NoPayloadFound` or `CorruptedPayload`.
- If checksum fails, return `IntegrityCheckFailed`.

### Teaching Outputs

Notebook and UI must show: cover image, stego image, absolute pixel difference image, bit-plane visualization, PSNR and SSIM, capacity utilization.

---

## 9.2 `image-randomized-lsb`

### Purpose

Key-seeded variant of LSB embedding to demonstrate keyed pixel/channel order.

### Required Differences from `image-lsb`

- Requires a `key` (unless `--allow-unkeyed`).
- Uses a deterministic key-seeded permutation of eligible embedding positions (§8.6).
- Same key and parameters reproduce the same extraction order.
- The method must remain deterministic for testing.

### Parameters

| Parameter | Required? | Default | Description |
|---|---:|---|---|
| `key` | Yes (unless `--allow-unkeyed`) | None | Derives the deterministic embedding permutation. |
| `bits_per_channel` | No | `1` | Same as `image-lsb`. |
| `channels` | No | `rgb` | Same as `image-lsb`. |
| `prng` | No | `pcg64` (documented) | Deterministic PRNG seeded by `SHA-256(key)`. |

### Security Teaching Note

The documentation must state that randomizing the embedding order does not make naive LSB undetectable; it primarily changes where modifications occur.

---

## 9.3 `image-edge-adaptive-lsb`

### Purpose

"Advanced bit manipulation" baseline: embed preferentially in visually complex (high-variance / edge) regions, where LSB changes are harder to detect than in smooth regions. Bridges naive LSB and the classical adaptive methods of Phase 4.

### Required cover formats

- PNG.

### Required payload formats

- Text, image as bytes, generic bytes.

### High-Level Algorithm Behavior

- Compute a per-pixel local activity score (e.g., gradient magnitude or local variance over a small window).
- Select embedding positions whose activity exceeds an adaptive threshold, ordered deterministically (optionally key-seeded, §8.6).
- The selection rule must depend only on cover content that is **preserved by the embedding**: compute the activity map only from bit planes that `b`-bit LSB embedding leaves unchanged (bit planes ≥ `bits_per_channel`), not the LSBs being modified, so the receiver recomputes the identical position set from the stego image.
- Embed framed payload bits into the LSBs of selected positions.
- Extract by recomputing the same activity map and position order from the stego image, reading LSBs, parsing the frame, validating checksum.

### Parameters

| Parameter | Required? | Default | Description |
|---|---:|---|---|
| `activity` | No | `gradient` | `gradient` or `variance`. |
| `threshold_mode` | No | `auto` | `auto` (percentile-based to fit payload) or a fixed value. |
| `window` | No | `3` | Neighborhood size for the activity score. |
| `bits_per_channel` | No | `1` | LSBs per selected channel. Range `1`–`4`. |
| `key` | No | None | Optional key to permute among eligible positions. |

### Determinism Requirement

The activity map must be computed only from bit planes that `b`-bit LSB embedding leaves unchanged, i.e. bit planes ≥ `bits_per_channel` (mask out the lowest `bits_per_channel` planes per channel before scoring). With the default `bits_per_channel = 1` this is bit planes ≥ 1. The method must include a self-consistency test that extract reproduces embed's exact position set on all fixture images **across the full supported `bits_per_channel` range (1–4)**.

### Capacity Formula

Capacity is content-dependent, so the `capacity` operation must run the activity map over the cover. A *position* is a pixel; each selected (high-activity) pixel contributes its 3 RGB channels, consistent with §9.1:

```text
selected_pixels = count of pixels whose activity exceeds the threshold
capacity_bits   = selected_pixels × 3 × bits_per_channel
capacity_bytes  = floor(capacity_bits / 8) - frame_overhead_bytes   # frame_overhead_bytes: §8.3
```

Under `threshold_mode = auto`, capacity is reported at the documented percentile floor (the maximum-yield threshold); under a fixed threshold it is the count of pixels above that value.

### Validation Requirements

- If too few high-activity positions exist for the payload, either lower the threshold (auto mode) up to a documented floor or raise `CapacityExceeded`.
- Warn that `bits_per_channel > 1` increases detectability.

### Teaching Outputs

- Activity/edge map overlay.
- Cover, stego, and difference images showing changes concentrated in textured regions.
- Side-by-side steganalysis comparison vs `image-lsb` at equal payload size (notebook 07).

---

## 9.4 `image-bitplane`

### Purpose

Visual image-in-image demonstration using bit planes.

### Required cover formats

- PNG.

### Required payload formats

- Image payloads only.

### High-Level Algorithm Behavior

- Decode hidden image and cover image.
- Resize or reject hidden image according to user parameter.
- Take the most significant bits of hidden image pixels.
- Store those bits in the least significant bits of cover image pixels.
- Extract by reading cover LSBs and reconstructing an approximate hidden image.

### Parameters

| Parameter | Required? | Default | Description |
|---|---:|---|---|
| `hidden_msb_bits` | No | `4` | MSBs retained from hidden image. |
| `cover_lsb_bits` | No | `4` | LSBs overwritten in cover. Usually equals `hidden_msb_bits`. |
| `resize_mode` | No | `fit` | `reject`, `fit`, `stretch`, or `center-crop`. |
| `output_hidden_format` | No | `png` | Format for recovered image. |

### Exactness Requirement

This method is a visual reconstruction demo, not exact byte-preserving payload steganography. The UI and notebook must explicitly state:

- Original hidden image file bytes are not preserved.
- Recovered hidden image may differ from original.
- Reconstruction quality depends on bit depth and resizing.

### Teaching Outputs

Cover image, hidden image, stego image, recovered hidden image, cover bit planes before and after embedding, recovered image quality metrics when applicable.

---

## 9.5 `text-zero-width`

### Purpose

Baseline text-in-text and bytes-in-text demo using invisible Unicode characters.

### Required cover formats

- UTF-8 `.txt`, UTF-8 `.md`.

### Required payload formats

- Text, image as framed bytes, generic bytes.

### High-Level Algorithm Behavior

- Convert payload to the shared framed payload format.
- Convert framed payload bytes to a bitstream.
- Map bits or bit pairs to a configured alphabet of zero-width Unicode characters.
- Insert mapped characters at eligible positions in the cover text.
- Extract by scanning for the configured alphabet and decoding the bitstream.

### Candidate Character Set

Default alphabet for 2-bit symbols:

| Bits | Character name | Code point |
|---|---|---|
| `00` | Zero Width Non-Joiner | `U+200C` |
| `01` | Zero Width Joiner | `U+200D` |
| `10` | Zero Width Space | `U+200B` |
| `11` | Zero Width No-Break Space / BOM | `U+FEFF` |

Implementation notes:

- The default alphabet uses only true zero-width characters. `U+200B` may be stripped by some platforms; the method must document platform fragility and allow custom alphabets.
- Directional-formatting characters (e.g., `U+202C`) are **not** in the default alphabet because they can affect visible text rendering (bidi); they may be offered only via an explicit custom alphabet with a warning.
- The built-in `minimal` alphabet (CLI `--alphabet minimal`) uses 1-bit symbols (`0`→`U+200C` ZWNJ, `1`→`U+200D` ZWJ), setting `bits_per_symbol = 1` — half the capacity of the default for maximum platform robustness.

### Insertion Slots

Eligible positions: after whitespace, after punctuation, between words. MVP default: insert after word boundaries, distributing symbols across the cover.

### Parameters

| Parameter | Required? | Default | Description |
|---|---:|---|---|
| `alphabet` | No | Built-in 4-character alphabet | Maps bit groups to zero-width characters. |
| `bits_per_symbol` | No | `2` | Derived from alphabet size. |
| `slot_policy` | No | `word-boundary` | Determines insertion positions. |
| `key` | No | None | If provided, chooses eligible positions deterministically (§8.6). |
| `max_density` | No | Method default | Limits inserted symbols per visible token. |

### Capacity Formula

```text
capacity_bits = eligible_slots × bits_per_symbol
capacity_bytes = floor(capacity_bits / 8) - frame_overhead_bytes
```

### Validation Requirements

- Input cover must be valid UTF-8.
- Cover must contain enough eligible slots.
- Output must preserve visible text content except for inserted invisible characters.
- UI must warn that many communication tools, editors, and normalizers can remove or alter hidden characters.

### Extraction Requirements

- Scan the stego text for the configured alphabet, ignoring visible cover text.
- If the bitstream cannot parse a valid frame, return a clear error.
- Checksum validation is mandatory.

### Teaching Outputs

Visible cover/stego text side by side, codepoint-level view revealing hidden characters, zero-width count, normalization attack result, extraction success before normalization and expected failure after destructive normalization.

---

## 9.6 `text-mlm-substitution`

### Purpose

Linguistic edit-based steganography (SOTA-class): hide a message inside a **supplied** natural-language cover by substituting selected words with context-appropriate alternatives. Unlike `text-zero-width`, the channel is the *choice of visible words*, so it survives Unicode normalization and copy/paste.

### Phase

Phase 2 (MVP-required).

### Required cover formats

- UTF-8 `.txt`, UTF-8 `.md` (natural language).

### Required payload formats

- Text, generic bytes.

### High-Level Algorithm Behavior (exact recovery, model-free runtime)

The key design constraint is **deterministic, model-free runtime** with exact recovery. A masked language model (MLM, e.g. BERT/DistilBERT) is used **only offline**, to curate and version the bundled substitution resource (dropping awkward or ambiguous substitutes so the shipped candidate sets read fluently). At both embed and extract time the candidate *sets* are reconstructed deterministically from that shipped resource without running any model. Because the bits select which candidate is emitted, the MLM has no per-cover freedom at embed time and plays no role in decoding — so it is not needed at runtime at all.

Embed:

1. Tokenize the cover into words; identify **carrier slots** = content words that have at least 2 admissible substitutes in a shipped, versioned synonym/inflection resource (e.g., WordNet + a lemma/POS table). Carrier-slot selection depends only on the original cover word and the fixed resource, so it is reproducible.
2. For each carrier slot, build the candidate list = `{original_word} ∪ admissible_substitutes` and reduce it to the fixed block-coding size (a power-of-two ≤ `max_candidates`) by a **deterministic, resource-only** rule (e.g., the lexicographically-first `max_candidates` surface forms), in a deterministic order. Set membership and order come entirely from the shipped resource — never from a per-cover model call — so the extractor reconstructs the identical list. The transmitted index is always relative to this list (see step 4).
3. Each carrier slot with `k` candidates carries `floor(log2(k))` bits via block coding.
4. Read payload frame bits; at each slot, select the candidate at the index given by the next bits and emit that word.

Extract (no model):

1. Re-tokenize the stego text; identify carrier slots using the same resource-only rule applied to the **observed** (possibly substituted) word — admissibility is defined so that every candidate in a set maps back to the same set (synonym-set closure), making the slot and its candidate list reconstructible from any member.
2. For each carrier slot, recompute the deterministic candidate list and read the index of the observed word as the embedded bits.
3. Reassemble the bitstream, parse the frame, validate checksum.

> The synonym resource must be **closed under substitution** (all members of a candidate set share the same set) so extraction reconstructs identical candidate lists without the cover. This is the property that makes the method exact and model-free at runtime. The masked LM is used **only offline**, when building and versioning the bundled resource (to drop low-fluency or ambiguous substitutes); its effect is baked into the shipped resource and is identically available to sender and receiver. It is **not** run per-cover at embed time and plays no role in decoding.

### Parameters

| Parameter | Required? | Default | Description |
|---|---:|---|---|
| `resource` | No | Bundled WordNet-based set | Versioned synonym/inflection resource (must be closed under substitution). |
| `mlm_model` | No | Build-time masked LM | Used **offline** to construct/version the synonym resource; not invoked per-cover at embed time and not needed at runtime. |
| `max_candidates` | No | `4` | Cap on candidates per slot (`2`/`4`/`8` → 1/2/3 bits). |
| `min_similarity` | No | Method default | Semantic-similarity floor for admitting a substitute. |
| `key` | No | None | Optionally permutes carrier-slot order (§8.6). |

### Capacity Formula

```text
capacity_bits = Σ_slots floor(log2(candidates_in_slot))
capacity_bytes = floor(capacity_bits / 8) - frame_overhead_bytes
```

Capacity depends on the cover's vocabulary; the `capacity` operation must run the resource (and optionally the MLM) over the cover.

### Validation Requirements

- Reject covers with too few carrier slots (`CapacityExceeded`).
- The substitution must preserve part-of-speech and inflection.
- Output is human-readable; the method must produce a visible word-level diff.

### Extraction Requirements

- Model-free, deterministic, exact. Checksum mandatory.
- If re-tokenization or candidate reconstruction is ambiguous for a slot, fail closed (`CorruptedPayload`).

### Teaching Outputs

- Visible word-level diff (cover vs stego) with carrier slots highlighted.
- Per-slot candidate lists and the bits each slot carries.
- Semantic-similarity summary and (optional) MLM perplexity of cover vs stego.
- Normalization-survival demo contrasting with `text-zero-width` (this method survives NFC/NFKC).

---

## 9.7 `text-ans-generative`

### Purpose

Generative linguistic steganography, **capacity-first**: synthesize natural-looking text from a small causal language model while encoding payload bits through token selection using ANS / arithmetic-coding-style entropy coding over the model's next-token distribution.

### Phase

Phase 2 (MVP-required).

### Important Distinction

This method does **not** hide into a supplied cover. It generates new stego text from a prompt + model. There is no visible cover diff, and Unicode-normalization attacks do not apply; analysis uses generative metrics (bits/token, perplexity).

### High-Level Algorithm Behavior

- Load the pinned causal LM via `lm_common.py` (deterministic, fixed-precision CPU inference; quantized PMF; pinned tokenizer/model revision).
- At each step, obtain the next-token distribution, apply agreed truncation (top-p/top-k) so both ends see identical support.
- Use an ANS/arithmetic-coding payload coder to map the next payload bits onto a token choice consistent with the model distribution.
- Append the token, advance context, until the framed payload is exhausted; then optionally continue sampling or stop.
- Extract by replaying identical model + prompt + truncation params over the stego token stream and decoding the bits back; parse frame; validate checksum.

### Parameters

| Parameter | Required? | Default | Description |
|---|---:|---|---|
| `model_id` | No | Bundled causal LM (e.g. gpt2-class) | Must be byte-identical on both ends. |
| `prompt` | Yes | None | Seed/context conditioning generation. |
| `key` | No | None | Optional CSPRNG keystream (§8.6). |
| `top_p` / `top_k` | No | `top_p=0.95` | Truncation; must match on both ends. |
| `temperature` | No | `1.0` | Entropy/rate vs naturalness knob. |
| `prob_quantize_bits` | No | Documented default | PMF rounding for cross-machine determinism. |
| `max_tokens` | No | Derived from payload | Generation budget / stop condition. |

### Capacity

Entropy-bounded: capacity ≈ per-token Shannon entropy of the truncated distribution (near zero under greedy/low-temperature). The `capacity` operation must run the model and report expected bits/token; there is no static slot count.

### Determinism

Exact recovery requires **bit-identical** probability vectors on both ends. `lm_common.py` must pin fixed-precision CPU inference, quantize the PMF before coding, and pin the tokenizer and model revision. The frame checksum makes any drift fail loudly (`IntegrityCheckFailed`) rather than corrupt silently.

### Teaching Outputs

- Token-by-token view of how bits map to token choices.
- Bits/token (embedding rate) and LM perplexity.
- Capacity-vs-temperature/top-p sweep.
- Contrast with `text-mec` (capacity-first vs security-first).

---

## 9.8 `text-mec` (minimum-entropy-coupling / iMEC)

### Purpose

Generative linguistic steganography, **security-first**: encode a message via minimum-entropy coupling between the (encrypted, uniform) message and the language-model token distribution, yielding *provably/perfectly secure* — distribution-preserving — stego text. Based on "Perfectly Secure Steganography Using Minimum Entropy Coupling" (iMEC; ICLR 2023).

### Phase

Phase 2 (MVP-required).

### Important Distinctions

- **Generative**, not cover-modification (no supplied cover; analysis uses generative + distribution-preservation metrics).
- **Near-exact recovery.** The iMEC decoder is a MAP approximation: recovery is probabilistic with a small documented error rate (entropy-stopping yields error on the order of 1e-6 **per message recovery**, independent of payload length at a fixed `entropy_stop` — not a hard guarantee). The frame is marked `recovery_class = near-exact`. Recovery is **fail-closed**: a corrupted framing integer (`header_len`/`payload_len`) surfaces as a parse/length error (`CorruptedPayload`), and a corrupted payload surfaces as a checksum mismatch (`IntegrityCheckFailed`) — in no case is corrupted output emitted silently. This is a deliberate teaching point: **perfect *security* ≠ perfect *reliability*.**

### High-Level Algorithm Behavior

- Encrypt/uniformize the payload (so the message looks uniform), then couple it to the LM token distribution via a minimum-entropy coupling at each step, sampling tokens that (a) carry message information and (b) preserve the emitted distribution (KL ≈ 0 vs honest sampling).
- Extract by replaying the identical model + prompt + parameters and running the MAP decoder to recover the message bits; parse frame; validate checksum.

### Reference Implementation

[`ssokota/mec`](https://github.com/ssokota/mec) (MIT). The MIT license permits adaptation; vendor or reimplement with attribution under the project license. GPT-2-class weights are separately, permissively available.

### Parameters

| Parameter | Required? | Default | Description |
|---|---:|---|---|
| `model_id` | No | Bundled causal LM (shared with `text-ans-generative`) | Byte-identical on both ends. |
| `prompt` | Yes | None | Conditioning context. |
| `key` | Yes | None | Drives uniformization/coupling secret. |
| `variant` | No | `imec` | `imec` (perfectly secure) vs higher-rate `arimec` (not perfectly secure — must be labeled). |
| `top_k` | No | Documented | Vocabulary truncation for tractable coupling. |
| `entropy_stop` | No | Documented | Stopping threshold controlling the residual error rate. |

### Capacity

Entropy-bounded (as in §9.7). Report expected bits/token by running the model.

### Determinism

Same bit-exact-PMF requirement as §9.7 (handled by `lm_common.py`). Additionally, the MAP decoder's residual error rate must be surfaced in docs and reports; tests assert the recovery success rate over fixtures meets the documented threshold.

### Teaching Outputs

- Distribution-preservation indicator (estimated KL / steganalysis-classifier advantage) showing `text-mec` output is statistically close to honest model samples while a capacity-first coder is not.
- Side-by-side rate comparison with `text-ans-generative` (security vs capacity).
- Explicit "perfect security ≠ undetectable in practice" framing: indistinguishability holds only against a warden using the same/representative model and an unperturbed channel; off-topic or low-entropy text still reads as machine-generated.

---

## 9.9 `text-unicode-whitespace`

### Purpose

Alternative cover-modification text channel using visually similar Unicode whitespace characters.

### Phase

Phase 3.

### High-Level Algorithm Behavior

- Replace ordinary spaces at selected positions with Unicode whitespace variants.
- Map whitespace variants to bit groups.
- Extract by scanning whitespace codepoints.

### Requirements

- Preserve readability in common fonts/editors.
- Provide a codepoint reveal view.
- Provide a whitespace-collapse attack.
- Document that copy/paste, Markdown rendering, and normalization may destroy the payload.

---

## 9.10 `image-adaptive-wrapper`

### Purpose

Connect classroom demos to modern classical image steganography methods without reimplementing S-UNIWARD/J-UNIWARD from scratch.

### Phase

Phase 4.

### Candidate adapters

- HStego for S-UNIWARD and J-UNIWARD-style embedding.
- ConSeal for JPEG stego simulations with J-UNIWARD, UERD, and nsF5.
- Binghamton DDE reference implementations where licensing and runtime requirements allow.

### Requirements

- Adapters are optional dependencies (behind extras).
- Missing dependencies must produce clear install guidance (`MissingOptionalDependency`).
- Notebooks must explain distortion minimization and cost maps conceptually.
- Outputs must be separated from MVP outputs to avoid confusing exact-payload demos with simulation-only methods.

### Teaching Outputs

- Cost-map visualization when available.
- Comparison with naive LSB at equal payload size.
- Steganalysis demonstration showing why adaptive methods exist.

---

## 9.11 `lm-generated-text` (research family)

### Purpose

Research notebook explaining the frontier of generative linguistic steganography beyond the two MVP generative methods.

### Phase

Research notebook only (Phase 5).

### Concepts to Explain

- Arithmetic coding over LM token probabilities; SAAC; SA-ANS.
- Distribution-copy sampling (Discop); sparse sampling (SparSamp); ANStega.
- The capacity–efficiency–security trilemma, situating the two MVP methods (`text-ans-generative`, `text-mec`) within it.

### Implementation Requirement

- No additional production CLI methods are added here in MVP.
- Any toy demos must run locally and offline (mocked distribution or the bundled small model), clearly labeled experimental.

---

## 10. CLI Specification

### 10.1 General Requirements

CLI command name: `stegolab`. Required subcommands: `hide`, `extract`, `capacity`, `analyze`, `attack`, `demo`.

All commands must support: `--help`, `--verbose`, `--quiet`, and machine-readable `--json`.

### 10.2 `hide`

```bash
stegolab hide \
  --payload <payload-file> \
  --cover <cover-file> \
  --out <output-file> \
  --method <method-id>
```

For generative methods (`text-ans-generative`, `text-mec`) there is no `--cover`; use `--prompt` instead. The CLI must error clearly if `--cover` is given to a generative method or `--prompt` to a cover-modification method.

Common optional arguments:

```bash
  --key <passphrase-or-key-id>
  --compress none|zlib|zstd|auto
  --overwrite
  --json
```

> The option blocks below enumerate the **CLI-exposed** parameters. Any §9 parameter not listed here (e.g. `scan_order`, `window`, `output_hidden_format`, `prob_quantize_bits`, `entropy_stop`, `resource`, `mlm_model`) uses its documented default and is settable only via the Python API.

Image LSB / edge-adaptive options:

```bash
  --bits-per-channel 1
  --channels rgb
  --activity gradient|variance        # edge-adaptive
  --threshold-mode auto|<value>       # edge-adaptive
  --allow-unkeyed                     # image-randomized-lsb: embed without a key (default: key required)
```

Image bit-plane options:

```bash
  --hidden-msb-bits 4
  --cover-lsb-bits 4
  --resize-mode reject|fit|stretch|center-crop
```

Cover-modification text options:

```bash
  --slot-policy word-boundary|whitespace|punctuation   # zero-width
  --max-density <float>                                 # zero-width
  --alphabet default|minimal|custom:<name>              # zero-width
  --max-candidates 4                                    # mlm-substitution
  --min-similarity <float>                              # mlm-substitution
```

Generative text options:

```bash
  --prompt <text-or-file>
  --model <model-id>
  --top-p 0.95 --top-k <int> --temperature 1.0
  --variant imec|arimec                                 # text-mec
  --max-tokens <int>
```

Example commands:

```bash
stegolab hide --payload secret.txt --cover cover.png --out stego.png \
  --method image-edge-adaptive-lsb --activity gradient --bits-per-channel 1

stegolab hide --payload message.txt --cover article.txt --out article.stego.txt \
  --method text-mlm-substitution --max-candidates 4

stegolab hide --payload message.txt --prompt "Write a short product review:" \
  --out review.stego.txt --method text-mec --variant imec --key course-demo
```

### 10.3 `extract`

```bash
stegolab extract \
  --stego <stego-file> \
  --out <output-path> \
  --method <method-id>
```

Generative-method extraction additionally requires the matching `--prompt`, `--model`, and decoding params. `--key` is **required** for `text-mec` and **optional** for `text-ans-generative` (when a key was supplied at embed time it must match). Always optional: `--overwrite`, `--json`.

```bash
stegolab extract --stego review.stego.txt --out recovered.txt \
  --method text-mec --prompt "Write a short product review:" --key course-demo
```

### 10.4 `capacity`

```bash
stegolab capacity --cover <cover-file> --method <method-id> [method params...]
```

`capacity` accepts the same method-specific parameters as `hide` (e.g. `--bits-per-channel`, `--max-candidates`). For generative methods it accepts `--prompt`/`--model`/decoding params and reports expected bits/token by running the model.

Output must include: total capacity in bits and bytes, estimated frame overhead, estimated usable payload bytes, method-specific assumptions, and warning thresholds.

### 10.5 `analyze`

```bash
stegolab analyze --cover <cover-file> --stego <stego-file> \
  --method <method-id> --metrics <metric-list>
```

`--method` informs which text metrics apply (codepoint metrics for cover-modification; perplexity/distribution metrics for generative). Examples:

```bash
stegolab analyze --cover cover.png --stego stego.png \
  --metrics capacity,psnr,ssim,histogram,chi2,rs

stegolab analyze --cover article.txt --stego article.stego.txt --method text-mlm-substitution \
  --metrics visible-diff,word-diff,semantic-similarity,normalization
```

### 10.6 `attack`

```bash
stegolab attack --input <stego-file> --out <attacked-file> --operation <operation-id>
```

Image operations: `jpeg-recompress`, `resize`, `crop`, `blur`, `noise`, `png-resave`.
Text operations: `normalize-nfc`, `normalize-nfkc`, `strip-zero-width`, `collapse-whitespace`, `plain-text-roundtrip`.

### 10.7 `demo`

```bash
stegolab demo run --profile graduate-course
```

The profile runs a deterministic sequence using bundled sample files and the bundled models, producing outputs under `data/outputs/` or a user-provided directory. The profile must run fully offline.

### 10.8 Exit Codes

| Code | Meaning |
|---:|---|
| `0` | Success. |
| `1` | General runtime error. |
| `2` | Invalid arguments. |
| `3` | Capacity exceeded. |
| `4` | Extraction integrity/authentication failure. |
| `5` | Unsupported file type or method. |
| `6` | Dependency missing for optional method. |
| `7` | Output exists and `--overwrite` was not provided. |

### 10.9 JSON Output Contract

Every command's `--json` output uses a shared envelope:

```json
{
  "ok": true,
  "command": "hide|extract|capacity|analyze|attack|demo",
  "method": "<method-id or null>",
  "result": { },
  "error": null
}
```

On failure, `ok` is `false`, `result` is `null`, and `error` is `{"type": "<§15 error name>", "exit_code": <§10.8 code>, "message": "..."}`. The `result` object maps to the §14 report objects: `hide` → `StegoResult`, `extract` → `ExtractedPayload`, `capacity` → `CapacityReport`, `analyze` → `AnalysisReport`, `attack` → `AttackReport`. `test_cli_contracts.py` asserts this envelope and the per-command `result` shape.

---

## 11. UI Specification

### 11.1 Framework

Use **Streamlit** for the MVP.

Requirements: local execution by default, no external upload service, clear warning that files remain local, easy reset between classroom demos.

### 11.2 Required UI Tabs

#### Tab 1: Hide

Inputs: payload upload; **either** cover upload (cover-modification) **or** prompt + model controls (generative); method selector; method-specific parameter controls; optional key; compression selector.

Outputs: capacity estimate before embedding; warning if payload exceeds capacity; stego file (or generated stego text) download; summary report.

#### Tab 2: Extract

Inputs: stego file upload; method selector; optional key; method-specific parameter controls (including prompt/model for generative methods).

Outputs: extracted metadata; integrity status (including near-exact status for `text-mec`); recovered payload download; preview for text or image payloads.

#### Tab 3: Compare

Inputs: cover (or prompt) and stego.

Outputs (images): side-by-side previews, difference heatmap, PSNR/SSIM, histogram summary, bit-plane visualization.
Outputs (text): visible/word-level diff, codepoint hidden-character view (cover-modification), zero-width count, Unicode category summary, perplexity + distribution-preservation indicator (generative).

#### Tab 4: Attack / Robustness

Inputs: stego upload, attack operation selector, method selector for re-extraction.
Outputs: attacked artifact, extraction success/failure after attack, explanation of why the method survived or failed.

#### Tab 5: Course Demos

Inputs: demo selector. Outputs: step-by-step walkthrough, generated files, links to corresponding notebooks.

---

## 12. Notebook Specification

| Notebook | Phase | Required sections |
|---|---|---|
| `00_course_intro_and_ethics.ipynb` | 1 | Definitions (steganography, encryption, watermarking, covert channels, steganalysis); legitimate uses and misuse risks; course safety boundaries; overview of project methods; hiding vs encrypting demo. |
| `01_payload_framing_and_capacity.ipynb` | 1 | Why raw payloads need framing; frame fields, wire format, and versioning; capacity formulas for image and text covers; compression effect; payload-exceeds-capacity failure. |
| `02_text_in_image_lsb.ipynb` | 1 | LSB concept; hide/extract text in PNG; visual diff; vary `bits_per_channel`; edge-adaptive LSB vs flat LSB; why JPEG breaks naive pixel LSB. |
| `03_image_in_image_bitplanes.ipynb` | 1 | Bit-plane visualization; hide/extract image; compare bit depths; exact bytes vs visual reconstruction. |
| `04_text_in_text_unicode.ipynb` | 1 | Zero-width characters; hide/extract; reveal hidden codepoints; normalization attacks; platform fragility. |
| `05_text_in_text_mlm_substitution.ipynb` | 2 | Linguistic edit-based stego; carrier slots and candidate sets; deterministic model-free extraction; word-level diff; semantic similarity; normalization survival vs zero-width. |
| `06_generative_text_stego_ans_and_mec.ipynb` | 2 | Cover-modification vs generative; ANS capacity-first vs iMEC security-first; bits/token; perplexity; distribution-preservation indicator; determinism/reproducibility caveats; "perfect security ≠ undetectable." |
| `07_steganalysis_against_naive_lsb.ipynb` | 3 | Histogram comparison; chi-square intuition; RS-style detection; payload size vs detectability; false positives/negatives; why adaptive (edge-adaptive, UNIWARD) exists. |
| `08_adaptive_image_stego_suniward_juniward.ipynb` | 4 | Distortion minimization; cost maps and textured regions; UNIWARD family; HStego/ConSeal adapter demo if installed; comparison to naive LSB; reproducibility notes. |
| `09_frontier_generative_linguistic_stego_research.ipynb` | 5 | SAAC; SA-ANS; Discop (distribution copies); SparSamp; ANStega; the trilemma; situating the MVP methods; all claims cited. |

---

## 13. Analysis and Evaluation Requirements

### 13.1 Image Metrics

| Metric | MVP? | Description |
|---|---:|---|
| Capacity bytes | Yes | Usable payload bytes for selected method. |
| Capacity utilization | Yes | Payload size / usable capacity. |
| Bits per pixel | Yes | Payload bits normalized by image size. |
| PSNR | Yes | Visual distortion metric. |
| SSIM | Yes | Structural similarity metric. |
| Pixel difference image | Yes | Visualization artifact. |
| Histogram difference | Yes | Basic statistical comparison. |
| Activity/edge map | Yes | Teaching visualization for `image-edge-adaptive-lsb`. |
| Chi-square LSB test | Phase 3 | Steganalysis demo. |
| RS-style analysis | Phase 3 | Steganalysis demo. |
| Bit-plane visualization | Yes | Teaching visualization. |

> `chi2` and `rs` metrics ship in Phase 3 with the steganalysis notebook (07). CLI/notebook examples that pass `--metrics ...,chi2,rs` are Phase 3 examples.

### 13.2 Text Metrics

| Metric | MVP? | Applies to | Description |
|---|---:|---|---|
| Eligible slots / carrier slots | Yes | zero-width, mlm | Number of insertion/substitution positions. |
| Capacity bytes | Yes | all | Usable payload capacity. |
| Capacity utilization | Yes | all | Payload size / usable capacity. |
| Visible edit distance | Yes | zero-width | Should be zero for zero-width. |
| Visible word-level diff | Yes | mlm | Carrier-slot substitutions. |
| Zero-width character count | Yes | zero-width | Count of hidden symbols. |
| Unicode category summary | Yes | zero-width, whitespace | Summary of unusual codepoints. |
| Normalization survival | Yes | zero-width, whitespace, mlm | Whether payload survives NFC/NFKC. |
| Semantic similarity | Yes | mlm | Cover-vs-stego meaning preservation. |
| Bits per token | Yes | ans, mec | Embedding rate. |
| Language-model perplexity | Yes | ans, mec, mlm | Naturalness indicator. |
| Distribution-preservation indicator | Yes | ans, mec | Estimated KL / steganalysis-classifier advantage. |
| Whitespace-collapse survival | Phase 3 | whitespace | Required for whitespace method. |

### 13.3 Robustness Attacks

The attack module must be educational and local-only.

Image attacks: JPEG recompression, resize, crop, blur, add noise, re-save as PNG.
Text attacks: NFC normalization, NFKC normalization, strip zero-width characters, collapse whitespace, plain-text round trip.

For each attack, reports must include: attack parameters, whether extraction succeeded, whether checksum passed, and a qualitative explanation. The attack notebook must highlight that `text-mlm-substitution` survives normalization while `text-zero-width` does not.

---

## 14. Python Package API Requirements

The internal API must be structured enough for notebooks to call without shelling out to the CLI.

Required conceptual API objects:

| Object | Purpose |
|---|---|
| `Payload` | Original payload bytes and metadata. |
| `Cover` | Cover artifact and inferred type (or a `GenerationContext` for generative methods). |
| `GenerationContext` | Prompt, model id, decoding params, key (generative methods). |
| `StegoResult` | Output path/text, method, parameters, metrics summary, `recovery_class`. |
| `ExtractedPayload` | Recovered bytes, metadata, integrity status. |
| `CapacityReport` | Total and usable capacity (and expected bits/token for generative). |
| `AnalysisReport` | Metrics and generated visual/text artifacts. |
| `AttackReport` | Attack parameters and extraction outcome. |

Required conceptual API functions: `hide(...)`, `extract(...)`, `estimate_capacity(...)`, `analyze(...)`, `attack(...)`.

No implementation code is required at spec stage.

---

## 15. Error Handling Requirements

| Error | Scenario | CLI exit code |
|---|---|---:|
| `InvalidArguments` | Missing or incompatible CLI args (e.g. `--cover` to a generative method). | `2` |
| `UnsupportedFileType` | Unsupported payload/cover/stego file. | `5` |
| `UnsupportedMethod` | Unknown method ID. | `5` |
| `CapacityExceeded` | Payload frame does not fit cover/capacity. | `3` |
| `NoPayloadFound` | Extraction cannot find a valid frame. | `4` |
| `CorruptedPayload` | Frame is malformed or truncated. | `4` |
| `IntegrityCheckFailed` | Checksum/authentication failure (includes near-exact decode failure for `text-mec`). | `4` |
| `WrongKey` | Keyed extraction fails authentication/integrity. | `4` |
| `OutputExists` | Output path exists without `--overwrite`. | `7` |
| `MissingOptionalDependency` | Adapter dependency missing. | `6` |

Error messages must be understandable to students and suggest the likely fix. Examples:

- "Payload is 12,405 bytes after framing, but selected cover capacity is 8,192 bytes. Use a larger cover, compression, or a lower-overhead method."
- "Extraction failed checksum validation. The file may be corrupted, transformed, or extracted with the wrong key/parameters."
- "`text-mec` decode did not reproduce a valid payload (near-exact method). Re-run with identical model, prompt, and parameters; if it persists, the stego text may have been altered."
- "JPEG covers are not supported by `image-lsb`; use PNG for the baseline demo or install the adaptive JPEG adapter."

---

## 16. Testing Requirements

### 16.1 Unit Tests

| Test file | Required cases |
|---|---|
| `test_frame_roundtrip.py` | Encode/parse all field combinations; fail-closed on bad magic/version/length/checksum; near-exact flag round-trips. |
| `test_roundtrip_image_lsb.py` | Text in PNG, image in PNG, multiple bit depths. |
| `test_roundtrip_image_randomized_lsb.py` | Same key succeeds, wrong key fails, deterministic output under fixed key. |
| `test_roundtrip_image_edge_adaptive_lsb.py` | Extract reproduces embed's position set; payload concentrated in high-activity regions; capacity floor behavior. |
| `test_roundtrip_image_in_image.py` | Hidden image extraction produces valid image; bit-depth params affect quality. |
| `test_roundtrip_text_zero_width.py` | Text and image payload extraction; custom alphabet. |
| `test_roundtrip_text_mlm_substitution.py` | Exact, model-free deterministic recovery; carrier-slot/candidate reconstruction; POS/inflection preserved; survives NFC/NFKC. |
| `test_roundtrip_text_ans_generative.py` | Exact recovery under fixed model/prompt/params; deterministic over the offline mock distribution. |
| `test_text_mec_near_exact.py` | Recovery success rate over fixtures ≥ documented threshold; failures surface as `IntegrityCheckFailed` or `CorruptedPayload`, never silent corruption. |
| `test_capacity_failures.py` | Payload too large fails before output write. |
| `test_corruption_and_wrong_key.py` | Truncated stego and wrong-key extraction fail cleanly. |
| `test_normalization_breaks_text_stego.py` | Normalization breaks `text-zero-width`; `text-mlm-substitution` survives. |
| `test_cli_contracts.py` | Exit codes, `--json` shape, help output, generative-vs-cover argument validation. |

### 16.2 Golden Files

```text
tests/fixtures/
  covers/    cover_small.png  cover_medium.png  article.txt
  payloads/  short_secret.txt  tiny_icon.png
  prompts/   review_prompt.txt
  expected/  README.md
```

Golden files must contain no sensitive or real private data.

### 16.3 Determinism Fixtures for LM Methods

- A small, version-pinned **deterministic mock token distribution** ships for CI so `text-ans-generative` and `text-mec` round-trips are reproducible **without** loading the real model or any network.
- Tests against the real bundled model are marked and run on release/nightly (not necessarily every commit), since cross-machine float determinism is environment-sensitive.

### 16.4 Property-Style Tests

Random short text payloads, random small binary payloads, multiple cover sizes, multiple `bits_per_channel`, multiple keys for randomized methods.

### 16.5 Notebook Tests

Notebooks must be executable via a documented command, complete without exceptions on small fixtures, and avoid external network calls by default (use bundled models / mock distributions). CI runs a fast smoke subset every commit and full notebook execution on release/nightly (see §21 exit criteria).

---

## 17. Performance Requirements

| Operation | Input size | Target |
|---|---:|---:|
| Image LSB hide/extract | 1024×1024 PNG, small text payload | < 3 s each. |
| Image edge-adaptive hide/extract | 1024×1024 PNG, small payload | < 4 s each. |
| Image bit-plane hide/extract | 1024×1024 cover, 256×256 hidden | < 3 s each. |
| Text zero-width hide/extract | 100 KB cover text | < 2 s each. |
| Text MLM substitution hide | 10 KB cover | < 2 s (model-free at runtime). |
| Text MLM substitution extract | 10 KB stego | < 2 s (model-free). |
| Generative (`ans`/`mec`) hide/extract | ~200 tokens, bundled small LM, CPU | document expected runtime (tens of seconds acceptable). |
| Analyze image | 1024×1024 pair | < 5 s for MVP metrics. |
| UI interaction | Course sample files | Responsive enough for live demo. |

LM-based methods are slower and must document expected runtime; the demo profile should keep generative examples short.

---

## 18. Dependency Requirements

### 18.1 Core Dependencies

- Python 3.11 or newer.
- Pillow (image I/O), NumPy (arrays/metrics).
- scikit-image (SSIM).
- Click or Typer (CLI); Rich (terminal output, optional).
- Streamlit (UI).
- pytest (tests); JupyterLab / notebook tooling.
- PyTorch + Transformers (Hugging Face) — required by the generative text methods (`text-ans-generative`, `text-mec`), which load the bundled causal LM at runtime.
- NLTK/WordNet (or an equivalent versioned synonym resource) for `text-mlm-substitution`; the curated resource is shipped, so this method needs **no** language model at runtime.

### 18.2 Bundled Models

Per the project decision, the MVP **bundles models in the base install** so the LM methods work offline with no network calls at runtime:

- A causal LM (GPT-2-class, ~500 MB) shared by `text-ans-generative` and `text-mec`.
- A pre-built, versioned substitution resource for `text-mlm-substitution` (a small data file, curated offline with a masked LM — see §9.6). The masked LM itself is a **build-time / dev** tool, not bundled or loaded at runtime.

`models/` contains model cards, pinned revisions, checksums, and a fetch-and-verify script. Weights are downloaded once at install time (with explicit user action), then cached locally; **runtime never performs network calls** (§20.1). The runtime bundled footprint (~500 MB causal LM + a small resource file) is the deliberate cost of making the generative SOTA text methods first-class; `text-mlm-substitution` adds no runtime model. A configuration option may relocate the causal LM behind the `linguistic` extra if a lighter base install is later desired.

### 18.3 Optional Dependencies

- `zstandard` for `zstd` compression.
- `cryptography` (or `pyca`) for Phase 3 authenticated encryption; `argon2-cffi` for the KDF.
- HStego for the adaptive image stego adapter.
- ConSeal and jpeglib dependencies for JPEG stego simulation adapter.

### 18.4 Dependency Policy

- The deterministic, model-free methods (image methods, `text-zero-width`) must import and run **without** PyTorch/Transformers loaded, so a "core-only" path stays lightweight even though the full MVP bundles models.
- Optional advanced dependencies are grouped behind extras.

```text
stegolab[ui]
stegolab[notebooks]
stegolab[crypto]
stegolab[adaptive]
stegolab[linguistic-research]
stegolab[dev]
```

(The causal + masked LMs needed by the MVP text methods are part of the base install per §18.2; the `linguistic-research` extra covers only the Phase 5 research add-ons.)

---

## 19. Documentation Requirements

### 19.1 README

Project purpose; safety and ethics notice; installation (including the one-time model fetch); quickstart for each MVP flow; CLI examples; UI launch; notebook overview; supported methods table; known limitations.

### 19.2 Method Docs

Each method doc must include: conceptual explanation; supported inputs/outputs; parameters; capacity formula; failure modes; detectability discussion; robustness discussion; example CLI commands. Generative-method docs must state the determinism requirements and (for `text-mec`) the near-exact guarantee.

### 19.3 Engineering Docs

Architecture overview; payload frame specification (§8); deterministic-LM-inference contract (`lm_common.py`); testing strategy; dependency extras and bundled-model policy; release checklist.

---

## 20. Security and Privacy Requirements

### 20.1 Local Processing

- All CLI and UI processing must be local by default.
- No telemetry.
- No automatic network calls at runtime (the model fetch is an explicit one-time install step).
- No file uploads to third-party services.

### 20.2 File Safety

- Do not overwrite files unless `--overwrite` is provided.
- Sanitize filenames from payload metadata (basename only).
- Do not write extracted files outside the requested output directory.
- Avoid path traversal when restoring original filenames.

### 20.3 Secret Handling

- Do not print payload contents to logs by default.
- Do not store passphrases.
- Do not include secret payloads in exception messages.
- UI key fields must use password-style inputs.

### 20.4 Integrity

- All exact-payload extraction must validate the checksum (or authentication tag).
- Near-exact methods (`text-mec`) must validate the checksum and fail closed on mismatch.
- Corrupted or failed extraction must not silently produce output as if successful.

---

## 21. Implementation Phases

> **MVP = Phases 1–3.** Phases 4–5 are advanced/research extensions.

### Phase 1: Deterministic MVP Hide/Extract

Deliverables: core payload framing (§8) + `frame.py`; `image-lsb`; `image-randomized-lsb`; `image-edge-adaptive-lsb`; `image-bitplane`; `text-zero-width`; CLI `hide`, `extract`, `capacity`; round-trip tests; notebooks 00–04; README quickstart.

Exit criteria: all Phase 1 methods round-trip on fixtures; capacity errors handled before output write; notebooks 00–04 execute successfully.

### Phase 2: SOTA Text Methods (MVP)

Deliverables: `lm_common.py` deterministic-inference layer + bundled models + fetch/verify script; `text-mlm-substitution`; `text-ans-generative`; `text-mec`; their tests (incl. deterministic mock distribution for CI and near-exact success-rate test); notebooks 05–06.

Exit criteria: `text-mlm-substitution` and `text-ans-generative` round-trip exactly on fixtures; `text-mec` meets its documented recovery-success threshold and fails closed otherwise; notebooks 05–06 execute offline.

### Phase 3: Analysis, UI, and Robustness (MVP)

Deliverables: CLI `analyze` and `attack`; image metrics (PSNR, SSIM, diff image, histogram, chi2, rs); text metrics (codepoint reveal, zero-width count, word diff, semantic similarity, perplexity, distribution-preservation, normalization behavior); Streamlit UI (Hide, Extract, Compare, Attack, Course Demos); `text-unicode-whitespace`; notebook 07.

Exit criteria: UI supports all MVP flows (including generative via prompt/model); attack demonstrations work on sample files; notebook 07 executes successfully.

### Phase 4: Advanced Classical Image Stego

Deliverables: optional HStego adapter; optional ConSeal adapter; advanced method docs; cost-map visualization where supported; notebook 08.

Exit criteria: missing dependencies fail gracefully (`MissingOptionalDependency`); at least one adaptive image stego demonstration runs locally when optional deps are installed; notebook clearly compares naive and adaptive approaches.

### Phase 5: Frontier Linguistic Research Notebook

Deliverables: notebook 09; conceptual SAAC/SA-ANS/Discop/SparSamp/ANStega explanations situating the MVP methods in the trilemma; optional toy demos over the mocked distribution or bundled model.

Exit criteria: notebook runs without network access by default; all research claims are cited; no production CLI feature added unless separately approved.

---

## 22. Definition of Done

The project is complete for the initial course release when:

1. CLI supports hide, extract, capacity, analyze, attack, and demo for all MVP methods.
2. UI supports hide, extract, compare, and attack for all MVP methods (cover-modification and generative).
3. Notebooks 00–07 are complete and executable offline.
4. Phase 1–3 tests pass, including the `text-mec` near-exact success-rate test.
5. README and method docs (including the two new SOTA text methods) are complete.
6. Safety/ethics notices are visible in README, CLI help, UI, and notebook 00, and match §4.
7. No network transport or external upload features exist; runtime makes no network calls.
8. Exact-payload methods validate checksum on extraction; near-exact methods fail closed on mismatch.
9. Capacity failures are clear and non-destructive.
10. Sample fixtures and demos contain no sensitive data; bundled models carry cards, pinned revisions, and checksums.

---

## 23. Resolved Engineering Decisions

The Section 23 open questions from draft 0.1 are resolved as follows:

1. **Arbitrary binary payloads in UI** — CLI supports arbitrary bytes now (frame is byte-agnostic); the UI limits to text/image in MVP and adds binary in Phase 3.
2. **`image-randomized-lsb` key** — requires a key unless `--allow-unkeyed` is passed.
3. **Frame checksum coverage** — SHA-256 over the **original decoded payload bytes** (pre-compression/encryption); AEAD tag additionally covers ciphertext when encryption is enabled (§8.3).
4. **Compression default** — `auto`: `zlib` for text-like/uncompressed payloads, `none` for already-compressed payloads.
5. **UI framework** — Streamlit.
6. **Advanced adapters** — thin adapter shims live in-repo; heavy dependencies stay behind optional extras / documented external installs.
7. **CI notebook execution** — fast smoke subset every commit; full notebook execution on release/nightly.
8. **Sample files & license** — code under **MIT**; course-owned sample media under **CC-BY-4.0**. The exact sample files (and any third-party media licensing) remain a teaching-team action item; external datasets (BOSSbase, ALASKA) are referenced, not redistributed.

Remaining genuinely-open item: the specific course-owned sample files to ship (owner: teaching team).

---

## 24. Suggested Engineering Milestones

| Milestone | Scope | Suggested owner type |
|---|---|---|
| M1 | Core frame format, I/O, error model, capacity reports, keys/PRNG | Backend engineer |
| M2 | Image LSB, randomized LSB | Backend/image engineer |
| M3 | Image edge-adaptive LSB | Backend/image engineer |
| M4 | Image-in-image bit-plane method | Backend/image engineer |
| M5 | Text zero-width method | Backend/text engineer |
| M6 | CLI integration and JSON reports | Backend engineer |
| M7 | `lm_common` deterministic inference + bundled models | ML/infra engineer |
| M8 | `text-mlm-substitution` (supplied-cover, exact) | NLP/text engineer |
| M9 | `text-ans-generative` and `text-mec` (generative) | ML/research engineer |
| M10 | Metrics and attack suite | Security/research engineer |
| M11 | Streamlit UI | Full-stack/data-app engineer |
| M12 | Notebooks 00–07 | Teaching/research engineer |
| M13 | Advanced adapters and notebooks 08–09 | Research engineer |
| M14 | QA, docs, release packaging | QA/devex engineer |

---

## 25. Appendix A: Example CLI Workflows

### Text inside image (edge-adaptive)

```bash
stegolab hide --payload data/payloads/secret.txt --cover data/covers/cover.png \
  --out data/outputs/stego.png --method image-edge-adaptive-lsb --activity gradient --bits-per-channel 1

stegolab extract --stego data/outputs/stego.png --out data/outputs/recovered_secret.txt \
  --method image-edge-adaptive-lsb --activity gradient
```

### Image inside image

```bash
stegolab hide --payload data/payloads/tiny_icon.png --cover data/covers/cover.png \
  --out data/outputs/stego_image.png --method image-bitplane --hidden-msb-bits 4 --cover-lsb-bits 4

stegolab extract --stego data/outputs/stego_image.png --out data/outputs/recovered_icon.png \
  --method image-bitplane
```

### Text inside text (invisible Unicode)

```bash
stegolab hide --payload data/payloads/secret.txt --cover data/covers/article.txt \
  --out data/outputs/article.stego.txt --method text-zero-width --key course-demo

stegolab extract --stego data/outputs/article.stego.txt --out data/outputs/recovered_secret.txt \
  --method text-zero-width --key course-demo
```

### Text inside text (linguistic, supplied cover)

```bash
stegolab capacity --cover data/covers/article.txt --method text-mlm-substitution --max-candidates 4

stegolab hide --payload data/payloads/short_secret.txt --cover data/covers/article.txt \
  --out data/outputs/article.mlm.txt --method text-mlm-substitution --max-candidates 4

stegolab extract --stego data/outputs/article.mlm.txt --out data/outputs/recovered_mlm.txt \
  --method text-mlm-substitution
```

### Text inside generated text (security-first, iMEC)

```bash
stegolab hide --payload data/payloads/short_secret.txt --prompt data/prompts/review_prompt.txt \
  --out data/outputs/review.mec.txt --method text-mec --variant imec --key course-demo

stegolab extract --stego data/outputs/review.mec.txt --out data/outputs/recovered_mec.txt \
  --method text-mec --prompt data/prompts/review_prompt.txt --key course-demo
```

### Analyze and attack

```bash
stegolab analyze --cover data/covers/cover.png --stego data/outputs/stego.png \
  --metrics capacity,psnr,ssim,histogram,chi2,rs

stegolab attack --input data/outputs/article.stego.txt --out data/outputs/article.normalized.txt \
  --operation normalize-nfkc

stegolab extract --stego data/outputs/article.normalized.txt --out data/outputs/recovered_after_attack.txt \
  --method text-zero-width --key course-demo
```

---

## 26. Appendix B: Glossary

| Term | Meaning |
|---|---|
| Cover | Innocuous-looking file (or, for generative methods, prompt+model distribution) into which data is hidden. |
| Payload | Text, image, or bytes to hide. |
| Stego artifact | Output file/text containing hidden data. |
| Extraction | Process of recovering hidden payload. |
| LSB | Least significant bit. Common beginner image stego technique. |
| Edge-adaptive LSB | LSB embedding biased toward high-activity (edge/textured) regions to reduce detectability. |
| Bit plane | Set of bits at the same significance position across pixels. |
| Unicode zero-width character | Invisible/near-invisible character used for text stego. |
| Cover-modification stego | Hides into a supplied cover (zero-width, whitespace, MLM substitution). |
| Generative stego | Synthesizes the cover while encoding the message (ANS, iMEC, Discop). |
| Steganalysis | Detection or analysis of hidden data in media. |
| PSNR | Peak signal-to-noise ratio; image distortion metric (higher = less distortion). |
| SSIM | Structural similarity index; perceptual image similarity. |
| Perplexity | Language-model measure of text naturalness (lower = more expected). |
| KL divergence | Distance between distributions; ≈0 indicates distribution preservation. |
| Distortion function | Cost model deciding where embedding changes are least detectable. |
| STC | Syndrome-trellis code, used in efficient distortion-minimizing embedding. |
| UNIWARD | Universal wavelet relative distortion family of image stego methods. |
| nsF5 / UERD | JPEG-domain steganography algorithms. |
| SAAC | Self-adjusting arithmetic coding for neural linguistic steganography. |
| ANS | Asymmetric numeral systems; entropy coding used in some generative stego. |
| MLM | Masked language model (e.g. BERT); predicts masked tokens from context. |
| MEC / iMEC | Minimum entropy coupling; basis of perfectly secure generative steganography. |
| Discop | Distribution-copies provably-secure generative stego (IEEE S&P 2023). |
| SparSamp | Sparse-sampling provably-secure generative stego (USENIX Security 2025). |
| ANStega | ANS-based generative stego addressing the capacity/efficiency/security trilemma. |
| Provably/perfectly secure stego | Stego whose stego distribution is (computationally/statistically) indistinguishable from honest cover sampling. |
| Recovery class | Frame flag: `exact` (byte-exact recovery) vs `near-exact` (probabilistic, checksum-guarded). |

---

## 27. Appendix C: Bibliography and Reference Links

1. Stegano documentation: <https://stegano.readthedocs.io/>
2. Stegano PyPI: <https://pypi.org/project/stegano/>
3. Universal Distortion Function for Steganography in an Arbitrary Domain: <https://link.springer.com/article/10.1186/1687-417X-2014-1>
4. HStego: <https://github.com/daniellerch/hstego>
5. ConSeal: <https://github.com/uibk-uncover/conseal>
6. Binghamton DDE steganographic algorithms: <https://dde.binghamton.edu/download/stego_algorithms/>
7. Binghamton DDE downloads and BOSSbase: <https://dde.binghamton.edu/download/>
8. ALASKA#2: <https://alaska.utt.fr/>
9. Large-Capacity Image Steganography Based on Invertible Neural Networks: <https://openaccess.thecvf.com/content/CVPR2021/papers/Lu_Large-Capacity_Image_Steganography_Based_on_Invertible_Neural_Networks_CVPR_2021_paper.pdf>
10. Unicode Steganography with Zero-Width Characters: <https://330k.github.io/misc_tools/unicode_steganography.html>
11. Perfectly Secure Steganography Using Minimum Entropy Coupling (iMEC, ICLR 2023): <https://arxiv.org/abs/2210.14889>
12. iMEC reference implementation (`ssokota/mec`, MIT): <https://github.com/ssokota/mec>
13. Discop: Provably Secure Steganography Based on "Distribution Copies" (IEEE S&P 2023): <https://dingjinyang.github.io/uploads/Discop_sp23_paper.pdf> · <https://ieeexplore.ieee.org/document/10179287/>
14. Near-imperceptible Neural Linguistic Steganography via Self-Adjusting Arithmetic Coding (SAAC): <https://aclanthology.org/2020.emnlp-main.22/>
15. Linguistic Steganography via Self-Adjusting Asymmetric Numeral Systems (SA-ANS): <https://direct.mit.edu/coli/article/52/1/113/132854/Linguistic-Steganography-via-Self-Adjusting>
16. SparSamp: Efficient Provably Secure Steganography Based on Sparse Sampling (USENIX Security 2025): <https://www.usenix.org/conference/usenixsecurity25/presentation/wang-yaofei>
17. Breaking the Generative Steganography Trilemma: ANStega (NDSS): <https://www.ndss-symposium.org/ndss-paper/breaking-the-generative-steganography-trilemma-anstega-for-optimal-capacity-efficiency-and-security/>

---

## 28. Changelog (0.1 → 1.0)

1. **Safety (§4).** Corrected four inverted/contradictory requirements (network transport, exfiltration module, default secret logging, anti-forensic workflows) to match §2.2 and §20; kept message themes 1–3 and the no-integrations rule.
2. **Exec summary (§1).** Removed "over explicit safety boundaries."
3. **New MVP method — `text-mlm-substitution` (§9.6).** SOTA-class linguistic edit-based stego into a supplied cover, with deterministic model-free exact extraction; supersedes the old Phase-3 `text-synonym-substitution`.
4. **New MVP method — `text-mec` (§9.8).** Minimum-entropy-coupling / iMEC, perfectly secure generative stego; near-exact recovery handled via the frame `recovery_class` flag and mandatory checksum.
5. **New MVP method — `text-ans-generative` (§9.7).** Capacity-first generative stego (ANS).
6. **New MVP method — `image-edge-adaptive-lsb` (§9.3).** Concretizes the "advanced bit manipulation" goal and the previously-orphaned `edge_adaptive_lsb.py`.
7. **Scope reconciliation.** §2.1, §3.2, §6.3, §12, §13, §21, §22, §24 now agree on one MVP method set across all paradigms.
8. **Frame wire format (§8.3).** Concrete big-endian byte layout, two-stage read, `recovery_class` field, checksum-coverage decision.
9. **Determinism (§7.2, §8.6, §9.7, §9.8, §16.3).** Pinned PRNG/KDF; `lm_common.py` deterministic-inference contract; offline mock distribution for CI.
10. **Dependencies (§18).** Bundled-model policy for the MVP LM methods; core deterministic methods remain importable without PyTorch.
11. **Open questions (§23).** All eight resolved; only the specific sample-file selection remains open (teaching team).
12. **Stories rewritten (§5).** Story 4 reframed; new Stories 5–6 for the generative methods; comparison story renumbered to 7.
13. **Research (§9.11, §12, §27).** Discop/SparSamp/ANStega/SAAC/SA-ANS moved to the research notebook with verified citations.

### Post-review corrections (v1.0 adversarial review pass)

A 39-agent consistency + reference-verification review produced 15 confirmed fixes, all applied:

- **`frame_overhead_bytes` defined (§8.3).** Concrete formula plus the policy the no-payload `capacity` command uses (nominal estimate).
- **Edge-adaptive determinism generalized (§9.3).** Activity map is read from bit planes ≥ `bits_per_channel` (not hard-coded to single-LSB), so multi-bit embedding stays decodable; added the missing capacity formula and the `1`–`4` range.
- **MLM contradiction resolved (§9.6).** The masked LM is now strictly an **offline resource-curation tool**; `text-mlm-substitution` is **model-free at runtime** (embed and extract). This also lightens the runtime bundle to one causal LM + a small resource file (§7.2, §17, §18.1–18.2, §6.3 updated to match).
- **Citation fix (§3.2).** iMEC fifth author corrected to **Strohmeier**.
- **`text-mec` fail-closed wording (§9.8, Story 6, §16.1).** Names both `CorruptedPayload` (framing-integer corruption) and `IntegrityCheckFailed` (checksum); residual error stated as ~1e-6 per message recovery.
- **CLI gaps (§10).** Added `--allow-unkeyed`, made generative `--key` method-specific, defined the `minimal` alphabet (§9.5), noted that unlisted §9 params are API-only, and added the §10.9 `--json` envelope contract.
- **Phase label (§3.2).** `text-unicode-whitespace` corrected to Phase 3.
