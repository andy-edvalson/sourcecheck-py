# Example Commands

This document provides ready-to-run commands using the example files in this repository.

## Available Example Files

- `examples/real_transcript.txt` - Real deidentified ED transcript (2,500+ words)
- `examples/real_summary_hal.json` - Structured summary with sections array
- `examples/agent_output.txt` - Free-form text output (simulated LLM agent)
- `schemas/sayvant_hpi.yaml` - Schema for Sayvant HPI format
- `schemas/text_output.yaml` - Schema for raw text validation
- `policies/sayvant_hpi.yaml` - Policies for structured summaries
- `policies/text_output.yaml` - Policies for text validation

## Quick Start Commands

### 1. Validate Structured Summary (Sayvant HPI Format)

```bash
# Uses default schema and policies
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json
```

**What this does:**
- Validates structured JSON summary against transcript
- Uses sections array format with query-based paths
- Extracts 40+ fields with various extraction methods
- Reports supported/refuted/insufficient evidence claims

### 2. Validate Text Output (LLM Agent)

```bash
# Validate free-form text against transcript
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/agent_output.txt \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml
```

**What this does:**
- Auto-detects `.txt` file and wraps as JSON
- Splits text into sentences
- Validates each sentence against transcript
- Uses semantic validators (NLI + hybrid)

### 3. Verbose Output with Debug Info

```bash
# See detailed extraction and validation process
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  --verbose \
  --debug
```

**What this shows:**
- Field resolution paths
- Extraction methods used
- Cache statistics
- Validator decisions

### 4. Text Format Report

```bash
# Generate human-readable text report
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  --format text \
  --detailed \
  -o report.txt
```

**What this generates:**
- Formatted text report (not JSON)
- Detailed claim-by-claim breakdown
- Evidence score distribution
- Saved to `report.txt`

## Multi-Agent Pipeline Example

Simulate a multi-stage LLM pipeline where each agent's output is validated:

```bash
# Stage 1: Validate structured summary
echo "=== Stage 1: Structured Summary ==="
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  -o stage1_report.json

# Stage 2: Validate text analysis
echo "=== Stage 2: Text Analysis ==="
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/agent_output.txt \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml \
  -o stage2_report.json

echo "Pipeline validation complete!"
echo "Review stage1_report.json and stage2_report.json"
```

## Advanced Usage

### Custom Output Location

```bash
# Save report to specific location
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  -o ~/Desktop/validation_report.json
```

### Quiet Mode (Errors Only)

```bash
# Suppress all output except errors
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  --quiet
```

### Compare Different Validators

```bash
# Test with different policy configurations
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  --policies policies/sayvant_hpi.yaml \
  -o report_default.json

# Note: You can create custom policies to compare results
```

## Testing Different Input Formats

### Test with Sample Data

```bash
# Use smaller sample files for quick testing
./bin/chart-checker \
  -t examples/sample_transcript.txt \
  -s examples/sample_summary.json \
  --schema checker/schema_configured.yaml \
  --policies checker/policies.yaml
```

### Test Text Wrapping

```bash
# Create a simple text file
echo "Patient is 56 years old. Has hypertension. Takes medication." > test.txt

# Validate it
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s test.txt \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml
```

### Test JSON with Text Field

```bash
# Create JSON with text field
echo '{"text": "Patient presented with fall. Left knee injury noted."}' > test.json

# Validate it (uses text schema)
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s test.json \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml
```

## Troubleshooting Commands

### Check if Files Exist

```bash
# Verify all example files are present
ls -lh examples/real_transcript.txt
ls -lh examples/real_summary_hal.json
ls -lh examples/agent_output.txt
ls -lh schemas/sayvant_hpi.yaml
ls -lh policies/sayvant_hpi.yaml
```

### Test Minimal Example

```bash
# Simplest possible command (uses all defaults)
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json
```

### View Help

```bash
# See all available options
./bin/chart-checker --help
```

## Performance Testing

### With Cache Statistics

```bash
# See cache performance
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  --debug 2>&1 | grep -A 5 "Cache Statistics"
```

### Time Execution

```bash
# Measure execution time
time ./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  --quiet
```

## Batch Processing

### Validate Multiple Summaries

```bash
# Loop through multiple summary files
for summary in examples/*.json; do
  echo "Validating $summary..."
  ./bin/chart-checker \
    -t examples/real_transcript.txt \
    -s "$summary" \
    -o "report_$(basename $summary .json).json"
done
```

## Integration Examples

### Use in CI/CD Pipeline

```bash
# Exit with error if validation fails
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  --quiet

# Check exit code
if [ $? -eq 0 ]; then
  echo "✓ Validation passed"
else
  echo "✗ Validation failed"
  exit 1
fi
```

### Parse JSON Output

```bash
# Extract overall score from report
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/real_summary_hal.json \
  -o report.json \
  --quiet

# Get score using jq
score=$(jq -r '.overall_score' report.json)
echo "Overall score: $score"
```

## Expected Results

### Structured Summary Validation
- **Total Claims**: ~40-50 (depending on extraction)
- **Supported**: ~70-90%
- **Overall Score**: ~0.7-0.9

### Text Output Validation
- **Total Claims**: ~8-10 sentences
- **Supported**: ~80-95%
- **Overall Score**: ~0.8-0.95

## Notes

- First run will be slower (loading ML models)
- Subsequent runs use cached retrievers
- Debug mode shows detailed internal operations
- Text format reports are more human-readable
- JSON reports are better for programmatic processing
