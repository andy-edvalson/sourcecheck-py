# Text Validation Guide

This guide explains how to validate free-form text output (e.g., from LLM agents) against source transcripts.

## Overview

The chart-checker system can now validate raw text in addition to structured JSON. This is useful for:

- **Multi-Agent Pipelines**: Validate each agent's output stays grounded to the original source
- **LLM Output Verification**: Ensure generated text doesn't hallucinate facts
- **Document Summarization**: Verify summaries against source documents
- **Content Generation**: Check that generated content is factually accurate

## Quick Start

### Validate Text File

```bash
./bin/chart-checker \
  -t examples/real_transcript.txt \
  -s examples/agent_output.txt \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml
```

The system will:
1. Load the text file (auto-detected by `.txt` extension)
2. Split it into sentences
3. Validate each sentence against the transcript
4. Generate a validation report

### Validate JSON with Text Field

```bash
# If your JSON has a "text" field:
echo '{"text": "Patient is 56 years old. Has diabetes."}' > output.json

./bin/chart-checker \
  -t transcript.txt \
  -s output.json \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml
```

## How It Works

### 1. Path Resolution with "."

The schema uses `path: "."` to indicate the root value:

```yaml
# schemas/text_output.yaml
fields:
  content:
    path: "."  # Root path
    extraction_method: sentence_split
```

This works with:
- **Text files**: `{"text": "content"}` (auto-wrapped by CLI)
- **JSON with text field**: `{"text": "content"}`
- **Raw strings**: `"content"` (if passed directly)

### 2. Sentence Splitting

The `sentence_split` extraction method breaks text into individual claims:

```
Input: "Patient is 56. Has diabetes. Takes metformin."

Claims:
  1. "Patient is 56."
  2. "Has diabetes."
  3. "Takes metformin."
```

Each sentence is validated independently against the source transcript.

### 3. Semantic Validation

Text validation uses semantic validators for best results:

```yaml
# policies/text_output.yaml
validators:
  content:
    - validator: "nli_validator"        # Natural Language Inference
      weight: 0.6
    - validator: "hybrid_bm25_minilm_validator"  # Keyword + Semantic
      weight: 0.4
```

## Multi-Agent Pipeline Example

Validate each stage of your LLM pipeline:

```bash
# Stage 1: Structured summary
./bin/chart-checker \
  -t transcript.txt \
  -s summary.json \
  --schema schemas/sayvant_hpi.yaml \
  --policies policies/sayvant_hpi.yaml

# Stage 2: Clinical analysis (text output)
./bin/chart-checker \
  -t transcript.txt \
  -s analysis.txt \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml

# Stage 3: Treatment recommendations (text output)
./bin/chart-checker \
  -t transcript.txt \
  -s recommendations.txt \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml
```

Each stage validates against the **original transcript**, preventing hallucination drift.

## Configuration

### Custom Schema

Create a custom schema for your text format:

```yaml
# schemas/my_text_format.yaml
version: "2.0"

fields:
  content:
    path: "."
    extraction_method: sentence_split  # or single_value, delimited, etc.
    criticality: high
```

### Custom Policies

Adjust validators and thresholds:

```yaml
# policies/my_text_policies.yaml
version: "1.0"

retriever: "semantic"  # or "bm25", "hybrid"
threshold: 0.3

validators:
  content:
    - validator: "nli_validator"
      weight: 1.0
      threshold: 0.5
```

## Supported File Types

The CLI auto-detects text files by extension:

- `.txt` - Plain text
- `.text` - Plain text
- `.md` - Markdown (treated as plain text)

All other extensions are treated as JSON.

## Example Output

```
SUMMARY:
  Total Claims: 8
  Supported: 7 (87.5%)
  Insufficient Evidence: 1 (12.5%)
  Refuted: 0 (0.0%)
  Overall Score: 0.875

VALIDATION WARNINGS

UNVALIDATED CLAIMS (Insufficient Evidence):
  - CONTENT: "Her last tetanus shot was 6 years ago."
    Reason: No matching evidence found in transcript
    Validator: nli_validator
```

## Best Practices

1. **Use Semantic Validators**: NLI and hybrid validators work best for free-form text
2. **Adjust Thresholds**: Lower thresholds (0.3-0.4) for more lenient validation
3. **Validate Early**: Check each pipeline stage to catch drift early
4. **Review Insufficient Evidence**: These may indicate missing information, not hallucinations

## Advanced Usage

### Custom Sentence Splitting

Modify the `split_into_sentences()` function in `checker/claimextractor/configurable.py` for custom splitting logic.

### Multiple Text Fields

Create a schema with multiple text fields:

```yaml
fields:
  summary:
    path: "summary"
    extraction_method: sentence_split
  
  recommendations:
    path: "recommendations"
    extraction_method: sentence_split
```

### Paragraph-Level Validation

Use `single_value` instead of `sentence_split` to validate entire paragraphs:

```yaml
fields:
  content:
    path: "."
    extraction_method: single_value  # Treat whole text as one claim
```

## Troubleshooting

**No claims extracted?**
- Check that your schema path is correct (use `"."` for root)
- Verify extraction_method is set (default: `single_value`)

**Low validation scores?**
- Try different validators (nli_validator, hybrid_bm25_minilm_validator)
- Adjust thresholds in policies
- Check that transcript contains relevant information

**Text file not detected?**
- Ensure file extension is `.txt`, `.text`, or `.md`
- Or manually wrap in JSON: `{"text": "your content"}`
