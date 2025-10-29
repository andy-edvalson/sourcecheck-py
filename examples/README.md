# Examples

This directory contains example data and scripts demonstrating how to use the chart-checker library.

## Files

- **sample_transcript.txt**: A fake clinical encounter transcript with detailed patient information
- **sample_summary.json**: A structured summary with both true and false claims
- **run_example.py**: Python script that runs verification on the sample data

## False Claims in Sample Data

The sample summary intentionally contains several **false/hallucinated** claims to demonstrate what the library should detect:

1. **"diabetes mellitus type 2"** in `past_medical_history` - NOT mentioned in transcript
2. **"metformin 500mg twice daily"** in `medications` - NOT mentioned in transcript  
3. **"underlying coronary artery disease"** in `assessment` - NOT mentioned in transcript

The transcript clearly states:
- Past medical history: hypertension and high cholesterol (NO diabetes)
- Medications: lisinopril and atorvastatin only (NO metformin)
- Assessment: costochondritis (NO coronary artery disease mentioned)

## Running the Example

```bash
# From the project root directory
python examples/run_example.py
```

This will:
1. Load the sample transcript and summary
2. Run the verification pipeline
3. Display the verification report
4. Save a detailed JSON report to `verification_report.json`

## Expected Output

With the current `always_true` validator (placeholder), all claims will be marked as "supported". This is expected behavior for the initial implementation.

To properly detect the false claims, you'll need to implement real validators that:
- Compare claims against retrieved evidence
- Use NLP or LLM-based verification
- Apply domain-specific medical knowledge

## Next Steps

1. Replace `always_true` validator with real validation logic
2. Implement additional validators (e.g., `evidence_based`, `llm_validator`)
3. Test with your own clinical data
4. Integrate with Claimify for advanced claim extraction
