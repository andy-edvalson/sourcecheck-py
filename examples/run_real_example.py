#!/usr/bin/env python3
"""
Example using real ED ambient transcription data.

Demonstrates how to use the transformer to work with nested section structure.
"""
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from checker import Checker
from checker.transform import normalize_summary


def main():
    """Run verification on real ED data."""
    print("=" * 70)
    print("Chart Checker - Real ED Data Example")
    print("=" * 70)
    print()
    
    # Load real transcript
    transcript_path = Path(__file__).parent / "real_transcript.txt"
    with open(transcript_path, 'r') as f:
        transcript = f.read()
    
    print(f"Loaded transcript ({len(transcript)} characters)")
    print()
    
    # Load real summary (nested structure)
    summary_path = Path(__file__).parent / "real_summary.json"
    with open(summary_path, 'r') as f:
        nested_summary = json.load(f)
    
    print("Loaded nested summary structure:")
    print(f"  Sections: {list(nested_summary.keys())}")
    for section_name, section_content in nested_summary.items():
        if isinstance(section_content, dict):
            print(f"    {section_name}: {len(section_content)} fields")
    print()
    
    # Transform nested structure to flat
    print("Transforming nested structure to flat...")
    flat_summary = normalize_summary(nested_summary)
    print(f"Flattened to {len(flat_summary)} total fields")
    print()
    
    # Show some sample fields
    print("Sample fields:")
    sample_fields = ['chief_complaint', 'hpi', 'dx', 'dispo']
    for field in sample_fields:
        if field in flat_summary:
            value = flat_summary[field]
            display = value[:60] + "..." if len(value) > 60 else value
            print(f"  {field}: {display}")
    print()
    
    # Initialize checker with standard schema
    print("Initializing checker...")
    checker = Checker(
        schema_path="checker/schema.yaml",
        policies_path="checker/policies.yaml"
    )
    print()
    
    # Run verification on flattened summary
    print("Running verification...")
    report = checker.verify_summary(
        transcript=transcript,
        summary=flat_summary
    )
    print()
    
    # Display results
    print("=" * 70)
    print("VERIFICATION REPORT")
    print("=" * 70)
    print()
    
    print(f"Overall Score: {report.overall_score:.2%}")
    print(f"Total Claims Extracted: {len(report.dispositions)}")
    print()
    
    # Group dispositions by field
    by_field = {}
    for disp in report.dispositions:
        field = disp.claim.field
        if field not in by_field:
            by_field[field] = []
        by_field[field].append(disp)
    
    print(f"Claims found in {len(by_field)} fields:")
    for field, disps in sorted(by_field.items()):
        print(f"  {field}: {len(disps)} claim(s)")
    print()
    
    # Show sample dispositions
    print("SAMPLE CLAIM DISPOSITIONS:")
    print("-" * 70)
    for i, disp in enumerate(report.dispositions[:5], 1):
        print(f"\n{i}. Field: {disp.claim.field}")
        claim_text = disp.claim.text[:80] + "..." if len(disp.claim.text) > 80 else disp.claim.text
        print(f"   Claim: {claim_text}")
        print(f"   Verdict: {disp.verdict}")
        if disp.evidence:
            print(f"   Evidence: {len(disp.evidence)} span(s) found")
    
    if len(report.dispositions) > 5:
        print(f"\n... and {len(report.dispositions) - 5} more claims")
    
    print()
    print("-" * 70)
    
    # Show missing claims
    if report.missing_claims:
        print("\nPOSSIBLE MISSING INFORMATION:")
        print("-" * 70)
        for i, missing in enumerate(report.missing_claims[:5], 1):
            print(f"{i}. {missing}")
        if len(report.missing_claims) > 5:
            print(f"... and {len(report.missing_claims) - 5} more")
        print()
    
    # Export report
    output_path = Path(__file__).parent / "real_verification_report.json"
    with open(output_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    
    print(f"Full report saved to: {output_path}")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print("✓ Successfully transformed nested ED summary to flat structure")
    print("✓ Extracted and validated claims from all fields")
    print("✓ Generated comprehensive verification report")
    print()
    print("Next steps:")
    print("  1. Review the verification report")
    print("  2. Replace 'always_true' validator with real validation logic")
    print("  3. Fine-tune schema criticality levels for your use case")
    print("  4. Add more sophisticated validators (LLM-based, evidence-based)")
    print()


if __name__ == "__main__":
    main()
