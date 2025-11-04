# Chart-Checker CLI Usage Guide

## Overview

The `chart-checker` CLI tool verifies summaries against larger text using configurable validators and policies.

## Installation

```bash
# Make the script executable (already done)
chmod +x bin/chart-checker

# Add to PATH (optional)
export PATH="$PATH:/Users/edvalsona/source/chart-checker/bin"
```

## Basic Usage

```bash
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_raw.json \
  -p checker/policies.yaml
```

## Command-Line Arguments

### Required Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `--transcript` | `-t` | Path to transcript text file |
| `--summary` | `-s` | Path to summary JSON file (supports multi-JSON) |
| `--policies` | `-p` | Path to policies.yaml configuration file |

### Optional Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--schema` | | `checker/schema_configured.yaml` | Path to schema.yaml file |
| `--output` | `-o` | `validation_report.json` | Output report path |
| `--format` | | `json` | Output format: `json` or `text` |
| `--verbose` | `-v` | | Enable verbose output |
| `--quiet` | `-q` | | Quiet mode (only errors) |

## Examples

### Basic Verification (JSON Output)

```bash
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_raw.json \
  -p checker/policies.yaml
```

Output:
```
Running verification...

✓ Verification complete!
  Total claims: 6
  Supported: 6/6 (100.0%)
  Overall score: 1.000
  Report saved to: validation_report.json
```

### Human-Readable Text Output

```bash
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_raw.json \
  -p checker/policies.yaml \
  --format text
```

Output:
```
================================================================================
CHART-CHECKER VALIDATION REPORT
================================================================================

Total Claims: 6
  ✓ Supported:             6 (100.0%)
  ? Insufficient Evidence: 0 (0.0%)
  ✗ Refuted:               0 (0.0%)

Overall Score: 1.000

================================================================================
RESULTS BY FIELD
================================================================================

📋 HPI
   Claims: 6, Supported: 6/6
```

### Custom Output File

```bash
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_raw.json \
  -p checker/policies.yaml \
  -o my_report.json
```

### Verbose Mode

```bash
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_raw.json \
  -p checker/policies.yaml \
  --verbose
```

Output includes:
- File loading progress
- Field count from summary
- Schema and policies paths
- Detailed error messages

### Quiet Mode

```bash
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_raw.json \
  -p checker/policies.yaml \
  --quiet
```

Only shows errors (useful for scripting).

## Input File Formats

### Transcript File

Plain text file containing the transcript:

```
examples/real_transcript.txt
```

### Summary File (Multi-JSON Support)

The CLI automatically handles both single and multi-JSON formats:

**Single JSON:**
```json
{
  "chief_complaint": "Fall",
  "hpi": "Patient fell...",
  "pmh": "Hypertension"
}
```

**Multi-JSON (LLM Output):**
```json
{
  "sections": [
    {"label": "Chief Complaint", "value": "Fall"},
    {"label": "HPI", "value": "Patient fell..."}
  ]
}
{
  "sections": [
    {"label": "PMH", "value": "Hypertension"}
  ]
}
```

The CLI automatically:
1. Detects multi-JSON format
2. Parses each JSON object
3. Merges sections into flat structure
4. Converts labels to snake_case field names

### Policies File

YAML configuration specifying validators per field:

```yaml
validators:
  hpi:
    - bm25_validator
  
  identifiers:
    - regex_validator
  
  pmh:
    - regex_validator
```

## Output Formats

### JSON Format (Default)

```json
{
  "dispositions": [
    {
      "claim": {
        "text": "Fall",
        "field": "chief_complaint"
      },
      "verdict": "supported",
      "evidence": [...],
      "validator": "bm25_validator",
      "explanation": "Found evidence..."
    }
  ],
  "overall_score": 1.0
}
```

### Text Format

Human-readable summary with:
- Total claims count
- Supported/insufficient/refuted breakdown
- Overall score
- Results grouped by field

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (file not found, validation failed, etc.) |

## Error Handling

The CLI provides clear error messages:

```bash
# Missing transcript file
Error: Transcript file not found: missing.txt

# Invalid JSON
Error: Could not parse JSON at position 123: ...

# Validation error
Error during verification: ...
```

Use `--verbose` for detailed error traces.

## Integration Examples

### Shell Script

```bash
#!/bin/bash
for summary in summaries/*.json; do
  ./bin/chart-checker \
    -t transcript.txt \
    -s "$summary" \
    -p policies.yaml \
    -o "reports/$(basename $summary .json)_report.json"
done
```

### Python Script

```python
import subprocess
import json

result = subprocess.run([
    './bin/chart-checker',
    '-t', 'transcript.txt',
    '-s', 'summary.json',
    '-p', 'policies.yaml',
    '-o', 'report.json'
], capture_output=True, text=True)

if result.returncode == 0:
    with open('report.json') as f:
        report = json.load(f)
    print(f"Score: {report['overall_score']}")
```

### CI/CD Pipeline

```yaml
# .github/workflows/validate.yml
- name: Validate Summary
  run: |
    ./bin/chart-checker \
      -t ${{ inputs.transcript }} \
      -s ${{ inputs.summary }} \
      -p checker/policies.yaml \
      --quiet
```

## Tips

1. **Use absolute paths** when calling from other directories
2. **Check exit code** for scripting: `$?` in bash
3. **Use --quiet** in automated pipelines
4. **Use --verbose** for debugging
5. **Text format** is great for quick reviews
6. **JSON format** is best for programmatic analysis

## Troubleshooting

### "Module not found" Error

Make sure you're running from the project root:
```bash
cd /Users/edvalsona/source/chart-checker
./bin/chart-checker ...
```

### "Permission denied" Error

Make the script executable:
```bash
chmod +x bin/chart-checker
```

### Multi-JSON Not Parsing

The CLI automatically detects and handles multi-JSON. If you see parsing errors, check that each JSON object is valid independently.

## Advanced Usage

### Custom Schema

```bash
./bin/chart-checker \
  -t transcript.txt \
  -s summary.json \
  -p policies.yaml \
  --schema custom_schema.yaml
```

### Batch Processing

```bash
# Process all summaries in a directory
for f in summaries/*.json; do
  ./bin/chart-checker -t transcript.txt -s "$f" -p policies.yaml \
    -o "reports/$(basename $f)"
done
```

### Compare Policies

```bash
# Test with different policies
./bin/chart-checker -t transcript.txt -s summary.json -p policies_strict.yaml -o report_strict.json
./bin/chart-checker -t transcript.txt -s summary.json -p policies_lenient.yaml -o report_lenient.json
```

## Support

For issues or questions:
1. Check this documentation
2. Review example files in `examples/`
3. Use `--verbose` for detailed output
4. Check `DEVELOPMENT.md` for architecture details
