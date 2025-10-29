#!/usr/bin/env python3
"""
Example script demonstrating how to use the checker library.

This example loads a sample transcript and summary, then runs verification
to detect true and false claims.
"""
import json
from pathlib import Path

# Add parent directory to path to import checker
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from checker import Checker


def main():
    """Run the example verification."""
    print("=" * 70)
    print("Chart Checker - Example Verification")
    print("=" * 70)
    print()
    
    # Load transcript
    transcript_path = Path(__file__).parent / "sample_transcript.txt"
    with open(transcript_path, 'r') as f:
        transcript = f.read()
    
    print(f"Loaded transcript ({len(transcript)} characters)")
    print()
    
    # Load summary
    summary_path = Path(__file__).parent / "sample_summary.json"
    with open(summary_path, 'r') as f:
        summary = json.load(f)
    
    print(f"Loaded summary with {len(summary)} fields:")
    for field, value in summary.items():
        print(f"  - {field}: {value[:60]}..." if len(value) > 60 else f"  - {field}: {value}")
    print()
    
    # Initialize checker
    print("Initializing checker...")
    checker = Checker(
        schema_path="checker/schema.yaml",
        policies_path="checker/policies.yaml"
    )
    print()
    
    # Run verification
    print("Running verification...")
    report = checker.verify_summary(
        transcript=transcript,
        summary=summary
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
    
    # Show dispositions
    print("CLAIM DISPOSITIONS:")
    print("-" * 70)
    for i, disp in enumerate(report.dispositions, 1):
        print(f"\n{i}. Field: {disp.claim.field}")
        print(f"   Claim: {disp.claim.text}")
        print(f"   Verdict: {disp.verdict}")
        print(f"   Validator: {disp.validator}")
        if disp.evidence:
            print(f"   Evidence found: {len(disp.evidence)} span(s)")
            for j, ev in enumerate(disp.evidence[:2], 1):  # Show first 2
                print(f"     {j}. Score: {ev.score:.2f} - {ev.text[:80]}...")
    
    print()
    print("-" * 70)
    
    # Show missing claims
    if report.missing_claims:
        print("\nPOSSIBLE MISSING INFORMATION:")
        print("-" * 70)
        for i, missing in enumerate(report.missing_claims, 1):
            print(f"{i}. {missing}")
        print()
    
    # Export to JSON
    output_path = Path(__file__).parent / "verification_report.json"
    with open(output_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    
    print(f"\nFull report saved to: {output_path}")
    print()
    
    # Summary of false claims (for this example)
    print("=" * 70)
    print("NOTES ON THIS EXAMPLE:")
    print("=" * 70)
    print()
    print("The sample summary contains several FALSE/HALLUCINATED claims:")
    print("  1. 'diabetes mellitus type 2' - NOT mentioned in transcript")
    print("  2. 'metformin 500mg twice daily' - NOT mentioned in transcript")
    print("  3. 'underlying coronary artery disease' - NOT mentioned in transcript")
    print()
    print("These false claims should be detected by more sophisticated validators.")
    print("The current 'always_true' validator is a placeholder that marks all")
    print("claims as supported. Replace it with real validators to catch errors.")
    print()


if __name__ == "__main__":
    main()
