# Chart Checker

A Python library for verifying clinical summaries using extracted claims and transcript evidence.

## Overview

Chart Checker validates clinical summaries by:
1. Extracting claims from structured summary fields
2. Retrieving supporting evidence from source transcripts
3. Running configurable validators on each claim
4. Auditing for completeness and missing information

## Installation

### Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install the package
pip install -e .
```

For development with testing tools:
```bash
pip install -e ".[dev]"
```

## Quick Start

For a guided CLI walkthrough with troubleshooting tips, see `.codex/quickstart.md`.

```python
from checker import Checker

# Initialize checker with config files
checker = Checker(
    schema_path="checker/schema.yaml",
    policies_path="checker/policies.yaml"
)

# Verify a summary against a transcript
transcript = "Patient reports chest pain for 2 days..."
summary = {
    "chief_complaint": "Chest pain for 2 days",
    "history": "Patient has no significant medical history"
}

report = checker.verify_summary(transcript, summary)
print(report)
```

## Project Structure

```
checker/
├── checker.py              # Main orchestrator
├── config.py               # Configuration loader
├── types.py                # Shared data types
├── schema.yaml             # Field definitions
├── policies.yaml           # Validator mappings
├── validators/             # Validation logic
├── retrieval/              # Evidence retrieval
├── rubric/                 # Completeness auditing
└── claimextractor/         # Claim extraction
```

## Configuration

### schema.yaml
Defines expected summary fields, types, and criticality levels.

### policies.yaml
Maps validators to specific summary fields.

## Development

Run tests:
```bash
pytest tests/
```

See `examples/` for working demonstrations.

## Future Enhancements

- Integration with Claimify for advanced claim extraction
- Dense retrieval with embeddings
- Additional validator implementations
- Async support for external API calls

## License

TBD
