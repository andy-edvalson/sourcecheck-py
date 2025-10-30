# SourceCheck

A Python library for verifying text claims against source documents using NLI and retrieval methods.

## Overview

SourceCheck validates claims by:
1. Extracting claims from structured text fields
2. Retrieving supporting evidence from source documents
3. Running configurable validators on each claim
4. Providing detailed verification reports

## Use Cases

- **LLM Output Validation** - Verify AI-generated text against source material
- **Agent Hallucination Detection** - Catch false claims in agent outputs
- **Summarization Verification** - Ensure summaries match source documents
- **RAG Pipeline Quality** - Validate retrieval-augmented generation results
- **Content Verification** - Check any text against reference documents

## Installation

### From GitHub (Private Repository)

```bash
# Clone the repository
git clone https://github.com/yourusername/sourcecheck.git
cd sourcecheck

# Create virtual environment
python3 -m venv venv
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

```python
from sourcecheck import Checker

# Initialize checker with config files
checker = Checker(
    schema_path="sourcecheck/schema.yaml",
    policies_path="sourcecheck/policies.yaml"
)

# Verify claims against source document
source_text = "Patient reports chest pain for 2 days..."
claims = {
    "chief_complaint": "Chest pain for 2 days",
    "history": "Patient has no significant medical history"
}

report = checker.verify_summary(source_text, claims)
print(f"Verification Score: {report.overall_score:.2%}")
```

## CLI Usage

```bash
# Run verification from command line
sourcecheck --transcript source.txt \
            --summary claims.json \
            --schema sourcecheck/schema.yaml \
            --policies sourcecheck/policies.yaml \
            --output report.json
```

## Project Structure

```
sourcecheck/
├── checker.py              # Main orchestrator
├── config.py               # Configuration loader
├── types.py                # Shared data types
├── schema.yaml             # Field definitions
├── policies.yaml           # Validator mappings
├── validators/             # Validation logic
├── retrieval/              # Evidence retrieval
├── quality/                # Quality metrics
└── claimextractor/         # Claim extraction
```

## Configuration

### schema.yaml
Defines expected claim fields, types, and criticality levels.

### policies.yaml
Maps validators to specific claim fields and configures retrieval strategies.

## Available Validators

- **BM25 Validator** - Keyword-based matching
- **Semantic Validator** - Dense embedding similarity
- **NLI Validator** - Natural language inference models
- **Hybrid Validator** - Combined BM25 + semantic
- **Context-Aware Validator** - Expanded context retrieval
- **Negation Detector** - Identifies negated claims

## Development

Run tests:
```bash
pytest tests/ -v
```

Run example:
```bash
python examples/run_example.py
```

## Documentation

- [Configuration Guide](CONFIGURATION_GUIDE.md)
- [Development Guide](DEVELOPMENT.md)
- [CLI Usage](CLI_USAGE.md)
- [Performance Optimization](PERFORMANCE_OPTIMIZATION.md)

## License

Proprietary - All Rights Reserved

Copyright (c) 2025. This software and associated documentation files are proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.
