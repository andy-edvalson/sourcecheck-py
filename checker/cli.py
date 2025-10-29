#!/usr/bin/env python3
"""
Chart-Checker CLI - Verify clinical summaries against transcripts
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from .checker import Checker


def load_multi_json(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON file, handling both single and multi-JSON formats.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        Merged dictionary
    """
    with open(file_path) as f:
        content = f.read()
    
    # Try parsing as single JSON first
    try:
        obj = json.loads(content)
        # Convert sections array format if present
        if 'sections' in obj and isinstance(obj['sections'], list):
            flat = {}
            for section in obj['sections']:
                label = section.get('label', '')
                value = section.get('value', '')
                field_name = label.lower().replace('/', '_').replace(' ', '_').replace('-', '_')
                flat[field_name] = value
            return flat
        # Auto-flatten nested section dicts (e.g., history_section, course_section)
        if isinstance(obj, dict):
            # Detect if any values are dicts and flatten them
            has_nested = any(isinstance(v, dict) for v in obj.values())
            if has_nested:
                flat = {}
                for k, v in obj.items():
                    if isinstance(v, dict):
                        flat.update(v)
                    else:
                        flat[k] = v
                return flat
        return obj
    except json.JSONDecodeError:
        pass
    
    # Try parsing as multiple JSON objects
    objects = []
    decoder = json.JSONDecoder()
    idx = 0
    
    while idx < len(content):
        content_slice = content[idx:].lstrip()
        if not content_slice:
            break
        try:
            obj, end_idx = decoder.raw_decode(content_slice)
            objects.append(obj)
            idx += len(content[:idx]) + len(content[idx:]) - len(content_slice) + end_idx
        except json.JSONDecodeError as e:
            print(f"Error: Could not parse JSON at position {idx}: {e}", file=sys.stderr)
            sys.exit(1)
    
    if not objects:
        print(f"Error: No valid JSON found in {file_path}", file=sys.stderr)
        sys.exit(1)
    
    # Convert sections format to flat format
    def convert_sections(obj):
        """Convert sections array to flat field dict."""
        if 'sections' in obj and isinstance(obj['sections'], list):
            flat = {}
            for section in obj['sections']:
                label = section.get('label', '')
                value = section.get('value', '')
                # Convert to snake_case
                field_name = label.lower().replace('/', '_').replace(' ', '_').replace('-', '_')
                flat[field_name] = value
            return flat
        # Auto-flatten nested section dicts
        if isinstance(obj, dict):
            has_nested = any(isinstance(v, dict) for v in obj.values())
            if has_nested:
                flat = {}
                for k, v in obj.items():
                    if isinstance(v, dict):
                        flat.update(v)
                    else:
                        flat[k] = v
                return flat
        return obj
    
    # Handle single object
    if len(objects) == 1:
        return convert_sections(objects[0])
    
    # Merge multiple objects
    merged = {}
    for obj in objects:
        converted = convert_sections(obj)
        merged.update(converted)
    
    return merged


def format_text_report(report: Dict[str, Any], detailed: bool = False) -> str:
    """Format report as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("CHART-CHECKER VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # Summary
    total = len(report['dispositions'])
    
    if total == 0:
        lines.append("Total Claims: 0")
        lines.append("No claims found to validate.")
        lines.append("")
        return "\n".join(lines)
    
    supported = sum(1 for d in report['dispositions'] if d['verdict'] == 'supported')
    insufficient = sum(1 for d in report['dispositions'] if d['verdict'] == 'insufficient_evidence')
    refuted = sum(1 for d in report['dispositions'] if d['verdict'] == 'refuted')
    
    lines.append(f"Total Claims: {total}")
    lines.append(f"  ✓ Supported:             {supported} ({supported/total*100:.1f}%)")
    lines.append(f"  ? Insufficient Evidence: {insufficient} ({insufficient/total*100:.1f}%)")
    lines.append(f"  ✗ Refuted:               {refuted} ({refuted/total*100:.1f}%)")
    lines.append(f"\nOverall Score: {report['overall_score']:.3f}")
    lines.append("")
    
    # Group by field
    by_field = {}
    for disp in report['dispositions']:
        field = disp['claim']['field']
        if field not in by_field:
            by_field[field] = []
        by_field[field].append(disp)
    
    if not detailed:
        # Simple summary
        lines.append("=" * 80)
        lines.append("RESULTS BY FIELD")
        lines.append("=" * 80)
        lines.append("")
        
        for field, disps in sorted(by_field.items()):
            field_supported = sum(1 for d in disps if d['verdict'] == 'supported')
            lines.append(f"📋 {field.upper()}")
            lines.append(f"   Claims: {len(disps)}, Supported: {field_supported}/{len(disps)}")
            lines.append("")
    else:
        # Detailed breakdown
        lines.append("=" * 80)
        lines.append("DETAILED RESULTS BY FIELD")
        lines.append("=" * 80)
        lines.append("")
        
        for field in sorted(by_field.keys()):
            field_disps = by_field[field]
            field_supported = sum(1 for d in field_disps if d['verdict'] == 'supported')
            
            lines.append(f"📋 {field.upper()}")
            lines.append(f"   Claims: {len(field_disps)}")
            lines.append(f"   Supported: {field_supported}/{len(field_disps)}")
            lines.append("")
            
            # Show first 3 claims in detail
            for i, disp in enumerate(field_disps[:3], 1):
                claim_text = disp['claim']['text']
                if len(claim_text) > 60:
                    claim_text = claim_text[:60] + "..."
                
                verdict_symbol = "✓" if disp['verdict'] == 'supported' else "?" if disp['verdict'] == 'insufficient_evidence' else "✗"
                
                lines.append(f"   {verdict_symbol} Claim {i}: {claim_text}")
                lines.append(f"      Verdict: {disp['verdict']}")
                lines.append(f"      Validator: {disp['validator']}")
                
                if disp['evidence']:
                    lines.append(f"      Evidence: {len(disp['evidence'])} span(s)")
                    best_evidence = disp['evidence'][0]
                    evidence_text = best_evidence['text']
                    if len(evidence_text) > 80:
                        evidence_text = evidence_text[:80] + "..."
                    lines.append(f"      Best Match (score={best_evidence['score']:.3f}): {evidence_text}")
                else:
                    lines.append(f"      Evidence: None found")
                
                # Show explanation if present
                if disp.get('explanation'):
                    explanation = disp['explanation']
                    if len(explanation) > 100:
                        explanation = explanation[:100] + "..."
                    lines.append(f"      Explanation: {explanation}")
                
                lines.append("")
            
            if len(field_disps) > 3:
                lines.append(f"   ... and {len(field_disps) - 3} more claims")
                lines.append("")
        
        # Score distribution
        lines.append("=" * 80)
        lines.append("EVIDENCE SCORE DISTRIBUTION")
        lines.append("=" * 80)
        lines.append("")
        
        all_scores = []
        for disp in report['dispositions']:
            for evidence in disp['evidence']:
                all_scores.append(evidence['score'])
        
        if all_scores:
            all_scores.sort(reverse=True)
            lines.append(f"Total Evidence Spans: {len(all_scores)}")
            lines.append(f"Score Range: {min(all_scores):.3f} - {max(all_scores):.3f}")
            lines.append(f"Average Score: {sum(all_scores)/len(all_scores):.3f}")
            lines.append(f"Median Score: {all_scores[len(all_scores)//2]:.3f}")
            lines.append("")
            
            # Score buckets
            high = sum(1 for s in all_scores if s >= 0.5)
            medium = sum(1 for s in all_scores if 0.3 <= s < 0.5)
            low = sum(1 for s in all_scores if s < 0.3)
            
            lines.append("Score Distribution:")
            lines.append(f"  High (≥0.5):      {high:3d} ({high/len(all_scores)*100:.1f}%)")
            lines.append(f"  Medium (0.3-0.5): {medium:3d} ({medium/len(all_scores)*100:.1f}%)")
            lines.append(f"  Low (<0.3):       {low:3d} ({low/len(all_scores)*100:.1f}%)")
            lines.append("")
        else:
            lines.append("No evidence spans found")
            lines.append("")
    
    return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Verify clinical summaries against transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  chart-checker -t transcript.txt -s summary.json -p policies.yaml
  
  # With custom output
  chart-checker -t transcript.txt -s summary.json -p policies.yaml -o report.json
  
  # Text format output
  chart-checker -t transcript.txt -s summary.json -p policies.yaml --format text
        """
    )
    
    parser.add_argument(
        '-t', '--transcript',
        required=True,
        help='Path to transcript text file'
    )
    parser.add_argument(
        '-s', '--summary',
        required=True,
        help='Path to summary JSON file (supports multi-JSON format)'
    )
    parser.add_argument(
        '-p', '--policies',
        required=True,
        help='Path to policies.yaml file'
    )
    parser.add_argument(
        '--schema',
        default='checker/schema_configured.yaml',
        help='Path to schema.yaml file (default: checker/schema_configured.yaml)'
    )
    parser.add_argument(
        '-o', '--output',
        default='validation_report.json',
        help='Output report path (default: validation_report.json)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'text'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed report with claim-by-claim breakdown (text format only)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output (shows internal operations, cache stats, etc.)'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (only errors)'
    )
    
    args = parser.parse_args()
    
    # Validate file paths
    transcript_path = Path(args.transcript)
    summary_path = Path(args.summary)
    policies_path = Path(args.policies)
    schema_path = Path(args.schema)
    
    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)
    
    if not summary_path.exists():
        print(f"Error: Summary file not found: {summary_path}", file=sys.stderr)
        sys.exit(1)
    
    if not policies_path.exists():
        print(f"Error: Policies file not found: {policies_path}", file=sys.stderr)
        sys.exit(1)
    
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load files
    if args.verbose:
        print(f"Loading transcript from: {transcript_path}")
    
    with open(transcript_path) as f:
        transcript = f.read()
    
    if args.verbose:
        print(f"Loading summary from: {summary_path}")
    
    summary = load_multi_json(summary_path)
    
    if args.verbose:
        print(f"Loaded {len(summary)} fields from summary")
        print(f"Initializing checker with schema: {schema_path}")
        print(f"                      and policies: {policies_path}")
    
    # Initialize checker
    try:
        checker = Checker(
            schema_path=str(schema_path),
            policies_path=str(policies_path),
            debug=args.debug
        )
    except Exception as e:
        print(f"Error initializing checker: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run verification
    if not args.quiet:
        print("Running verification...")
    
    if args.debug:
        print(f"DEBUG: Extracted {len(summary)} fields from summary")
        print(f"DEBUG: Transcript length: {len(transcript)} characters")
    
    try:
        report = checker.verify_summary(
            transcript=transcript,
            summary=summary
        )
        
        # Show cache stats in debug mode
        if args.debug:
            cache_stats = checker.get_cache_stats()
            print(f"\nDEBUG: Cache Statistics:")
            print(f"  Cache size: {cache_stats['cache_size']}/{cache_stats['max_cache_size']}")
            print(f"  Cache hits: {cache_stats['cache_hits']}")
            print(f"  Cache misses: {cache_stats['cache_misses']}")
            print(f"  Hit rate: {cache_stats['hit_rate']:.1%}")
    except Exception as e:
        print(f"Error during verification: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Save report
    report_dict = report.to_dict()
    
    if args.format == 'json':
        with open(args.output, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        if not args.quiet:
            # Collect refuted and insufficient evidence claims
            refuted = [d for d in report.dispositions if d.verdict == 'refuted']
            insufficient = [d for d in report.dispositions if d.verdict == 'insufficient_evidence']
            supported = sum(1 for d in report.dispositions if d.verdict == 'supported')
            total = len(report.dispositions)
            
            print(f"\nReport saved to: {args.output}")
            
            # Print warnings if there are any non-supported claims
            if refuted or insufficient:
                print("\nVALIDATION WARNINGS")
                print("=" * 80)
                
                if refuted:
                    print("\nREFUTED CLAIMS (Likely Hallucinations):")
                    for d in refuted:
                        claim_text = d.claim.text[:60] + "..." if len(d.claim.text) > 60 else d.claim.text
                        print(f"  - {d.claim.field.upper()}: \"{claim_text}\"")
                        print(f"    Reason: {d.explanation}")
                        print(f"    Validator: {d.validator}")
                        print()
                
                if insufficient:
                    print("UNVALIDATED CLAIMS (Insufficient Evidence):")
                    for d in insufficient[:5]:  # Limit to first 5
                        claim_text = d.claim.text[:60] + "..." if len(d.claim.text) > 60 else d.claim.text
                        print(f"  - {d.claim.field.upper()}: \"{claim_text}\"")
                        print(f"    Reason: {d.explanation}")
                        print(f"    Validator: {d.validator}")
                        print()
                    if len(insufficient) > 5:
                        print(f"  ... and {len(insufficient) - 5} more unvalidated claims")
                        print()
            
            # Print summary
            print("SUMMARY:")
            print(f"  Total Claims: {total}")
            print(f"  Supported: {supported} ({supported/total*100:.1f}%)")
            print(f"  Insufficient Evidence: {len(insufficient)} ({len(insufficient)/total*100:.1f}%)")
            print(f"  Refuted: {len(refuted)} ({len(refuted)/total*100:.1f}%)")
            print(f"  Overall Score: {report.overall_score:.3f}")
    
    elif args.format == 'text':
        text_report = format_text_report(report_dict, detailed=args.detailed)
        
        if args.output == 'validation_report.json':
            # Change default extension for text
            args.output = 'validation_report.txt'
        
        with open(args.output, 'w') as f:
            f.write(text_report)
        
        if not args.quiet:
            print(text_report)
            print(f"\n✓ Report saved to: {args.output}")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
