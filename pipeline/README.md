# Hardware-Aware Embedded Python Code Generation Pipeline

A validation-in-the-loop pipeline that synthesizes **Raspberry Pi Python instruction→code
examples** for LLM fine-tuning. It samples a structured hardware taxonomy, generates a coding
prompt, generates code with an LLM, validates it (syntax, library whitelist/blacklist, length,
structure, quality score), repairs failures, and standardizes the instruction.

> Cleaned, production-oriented version. API keys are read from the environment (never hardcoded),
> generation is bounded, and a library **blacklist** is enforced alongside the whitelist.

## Pipeline stages
1. **Taxonomy sampling** — category × subcategory × complexity × style × Pi-model × integration × context (`dkb.py`).
2. **Prompt construction** (`prompt_generator.py`) — base prompt → enrichment (1–4 library recommendations).
3. **Code generation** (`code_generator.py` + `api_client.py`) — bounded Gemini call, robust fence extraction.
4. **Validation-in-the-loop** (`validation.py`) — `compile()` syntax, **whitelist + blacklist** imports, length, structure, composite quality score (≥60/100); up to 4 LLM correction attempts.
5. **Instruction standardization** (`prompt_standardizer.py`) — rewrites the verbose prompt into a concise instruction.
6. **Persistence + resume** (`progress_manager.py`) — atomic checkpointing.

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env            # then put your real keys in .env (NOT committed)
export GEMINI_API_KEYS="key1,key2,key3"   # or load the .env in your shell
```
Get keys at <https://aistudio.google.com/app/apikey>. The pipeline rotates across multiple keys
to spread rate limits.

## Usage
```bash
python cgs_v3.py --examples 8000 --output-dir raspberry_pi_code_examples_v6 --quality-threshold 60
python cgs_v3.py --report-only            # summarize an existing run
```
Common flags: `--examples`, `--output-dir`, `--quality-threshold`, `--max-correction-attempts`, `--reset`.
Output: per-example `.py` files + JSON in `valid/` and `invalid/`, plus `generation_metadata_*.json`.

## Configuration (key constants in `cgs_v3.py`)
| Constant | Meaning | Default |
|---|---|---|
| `TOTAL_EXAMPLES` | examples to generate | 8000 |
| `MIN_QUALITY_SCORE` | composite quality cutoff (0–100) | 60 |
| `MAX_CORRECTION_ATTEMPTS` | LLM repair attempts per example | 4 |
| `MAX_OUTPUT_TOKENS` | bound on generated code length | 2048 |

## Library governance
- **Whitelist:** `STANDARD_LIBRARIES` / `STANDARD_LIBRARIES_FLAT` in `dkb.py`.
- **Blacklist:** `DISALLOWED_LIBRARIES` (deprecated / wrong-platform / hallucinated / Py2-only) — enforced by the validator via `is_disallowed()`; `LIBRARY_ALIASES` suggests modern replacements.

## Security
- **No secrets in source.** Keys come from `GEMINI_API_KEYS`. Never commit `.env`.
- Generated code is **not** security-audited; review before running on hardware.

## Tests
```bash
pytest -q          # deterministic components: taxonomy, validation, blacklist, fence extraction
```

## Layout
```
cgs_v3.py             orchestrator / CLI
prompt_generator.py   two-stage prompt construction
code_generator.py     prompt -> code, fence extraction, retry
prompt_standardizer.py concise-instruction rewrite
validation.py         validation-in-the-loop + quality score
dkb.py                domain knowledge base: taxonomy + whitelist + blacklist + board specs
api_client.py         Gemini HTTP client (key rotation, bounded output, backoff)
progress_manager.py   checkpoint / resume (atomic)
tests/                pytest suite
```
