# Working with Real ED Ambient Transcription Data

This directory contains examples using real Emergency Department ambient transcription data from your live system.

## Files

- **real_transcript.txt**: Deidentified ED encounter transcript
- **real_summary.json**: Structured summary with nested sections (history_section, course_section)
- **run_real_example.py**: Demo script showing how to use the transformer

## The Transformation Approach

Your ED system outputs summaries in a **nested section structure**:

```json
{
  "history_section": {
    "chief_complaint": "Fall",
    "hpi": "Patient fell...",
    "pmh": "Hypertension"
  },
  "course_section": {
    "dx": "Laceration",
    "dispo": "Discharge",
    "treatments": "Toradol 30mg"
  }
}
```

Rather than building complex parsers, we use a **simple transformer** to flatten this into the format the checker expects:

```json
{
  "chief_complaint": "Fall",
  "hpi": "Patient fell...",
  "pmh": "Hypertension",
  "dx": "Laceration",
  "dispo": "Discharge",
  "treatments": "Toradol 30mg"
}
```

## Usage

```python
from checker import Checker
from checker.transform import normalize_summary

# Load your nested summary
nested_summary = {
    "history_section": {...},
    "course_section": {...}
}

# Transform to flat structure
flat_summary = normalize_summary(nested_summary)

# Use with existing checker
checker = Checker(
    schema_path="checker/schema.yaml",
    policies_path="checker/policies.yaml"
)

report = checker.verify_summary(transcript, flat_summary)
```

## Why This Approach?

1. **Simplicity**: One simple function vs. rewriting all the checker logic
2. **Flexibility**: Works with both flat and nested structures
3. **Maintainability**: Existing checker code doesn't need to change
4. **Extensibility**: Easy to add more transformation logic if needed

## Schema Files

We maintain two schema files:

1. **schema.yaml** (flat structure)
   - Used by the checker after transformation
   - Simple field definitions

2. **schema_ed.yaml** (nested structure)
   - Documents your actual ED output format
   - Useful for reference and validation
   - Can be used with ConfigED if you need section-aware logic

## Running the Example

```bash
source venv/bin/activate
python examples/run_real_example.py
```

This will:
1. Load the real transcript and nested summary
2. Transform the nested structure to flat
3. Run verification with the existing checker
4. Generate a detailed report

## Current Results

With the real data:
- ✓ Successfully transforms 40 fields from 2 sections
- ✓ Extracts claims from all populated fields
- ✓ Retrieves evidence from transcript
- ✓ Generates verification report

## Next Steps

1. **Add ED-specific validators**
   - Validate diagnosis codes (ICD-10)
   - Check medication dosages
   - Verify disposition logic

2. **Fine-tune for ED use case**
   - Adjust criticality levels for ED fields
   - Add ED-specific validation rules
   - Handle empty fields appropriately

3. **Enhance claim extraction**
   - Better handling of multi-line fields (HPI, treatments)
   - Extract structured data (medications, procedures)
   - Integrate with Claimify

4. **Add real validators**
   - Replace `always_true` with evidence-based validation
   - Add LLM-based verification
   - Implement medical knowledge checks

## Field Mapping

Your ED summary fields map to the checker as follows:

### History Section
- `high_risk_dx` → Critical safety checks
- `chief_complaint` → Primary complaint
- `hpi` → Detailed history
- `pmh`, `psh` → Medical/surgical history
- `medications` → Current meds
- `pe_findings` → Physical exam

### Course Section
- `procedures_by_me` → Procedures performed
- `treatments` → Medications given
- `imaging_interpreted` → Imaging results
- `dx` → Final diagnosis
- `dispo` → Disposition
- `follow_up` → Follow-up instructions

All fields are flattened and validated individually.
