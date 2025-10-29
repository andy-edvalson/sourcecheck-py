# Chart Checker Quickstart

Purpose: Verify clinical summaries against source transcripts using configurable claim extraction, retrieval, and validators.

## Prerequisites
- Python `>=3.8`.
- Recommended: virtual environment.
- Minimal install: `pip install -e .` (uses `pyproject.toml`).
- Advanced validators/retrievers (spaCy/Transformers): `pip install -r requirements.txt`.

## Install
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install the project
pip install -e .

# Optional: full stack for semantic/NLI validators
pip install -r requirements.txt
```

## Inputs
- Transcript: plaintext file (e.g., `examples/sample_transcript.txt`).
- Summary: JSON file. Supports:
  - Flat dict of fields → values.
  - Multi‑JSON streams.
  - `{"sections": [{label, value}, ...]}` format auto‑flattened.
- Policy and schema:
  - Use `checker/policies.yaml` and `checker/schema_configured.yaml` for ED‑style fields.

## Run the CLI
```bash
chart-checker \
  -t examples/sample_transcript.txt \
  -s examples/sample_summary.json \
  -p checker/policies.yaml \
  --schema checker/schema_configured.yaml \
  --format text --detailed
```
- Output default: `validation_report.json` (or `validation_report.txt` for `--format text`).
- Helpful flags: `--debug` (cache stats + internals), `-v` (verbose), `-q` (quiet).

## Programmatic API
```python
from checker import Checker

checker = Checker(
    schema_path='checker/schema_configured.yaml',
    policies_path='checker/policies.yaml',
)

report = checker.verify_summary(transcript, summary)
print(report.to_dict())
```

## Report Basics
- Dispositions per claim: `supported`, `refuted`, `insufficient_evidence`.
- Evidence spans: text + score + indices.
- Overall score: weighted claims support + completeness.
- Missing claims: fields expected but absent/empty.

## Troubleshooting
- Policies missing keys
  - Ensure `version`, `validators`; typically `settings`, `retriever`, `retriever_config`.
  - See `checker/config.py` for validation requirements.
- Validator not found
  - Check name in `checker/validators/registry.py` and spelling in `policies.yaml`.
  - Use string (`validator_name`) or object (`{validator_name: {config}}`).
- Import errors (spaCy/Transformers/Torch)
  - Install full requirements: `pip install -r requirements.txt`.
  - Or switch to purely lexical validators (`bm25_validator`) in policies for lighter setup.
- No claims extracted
  - Verify summary field names match schema.
  - Confirm extraction method (e.g., `delimited` vs `single_value`) in `checker/schema_configured.yaml`.
  - For bullet text, ensure lines start with `-` or use `fallback: sentence_split`.
- Low evidence scores / few matches
  - Tune `retriever_config` (`chunk_size`, `overlap`, `context_window`).
  - Increase `settings.max_evidence_spans`.
  - Try `hybrid_bm25_minilm_validator` or `semantic` retriever.
- Performance
  - `Checker` caches retrievers per transcript/config; enable `--debug` to view hit/miss stats.
  - Prefer BM25 retriever/validators for speed; reduce `chunk_size` if memory‑bound.

## Next Steps
- Customize `checker/policies.yaml` to map validators to your fields.
- Extend schema extraction rules in `checker/schema_configured.yaml` for new field formats.
- Explore `examples/` and `CLI_USAGE.md` for more scenarios.

