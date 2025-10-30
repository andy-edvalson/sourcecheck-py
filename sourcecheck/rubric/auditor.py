"""
Auditor for detecting missing claims from transcript.
"""
import re
from typing import List, Dict, Any


def detect_missing_claims(
    transcript: str,
    summary: Dict[str, Any],
    schema: Dict[str, Any]
) -> List[str]:
    """
    Detect important information in transcript that's missing from summary.
    
    This is a stub implementation. Future versions could:
    - Use NLP to extract key facts from transcript
    - Compare against summary claims
    - Identify critical omissions
    
    Args:
        transcript: Full transcript text
        summary: Summary dictionary with field values
        schema: Schema configuration for fields
    
    Returns:
        List of missing claim descriptions
    """
    # TODO: Implement sophisticated missing claim detection
    # For now, return empty list as placeholder
    missing = []
    
    # Simple stub: Check if transcript mentions common medical terms
    # that aren't in the summary
    medical_keywords = [
        'allergy', 'allergies', 'medication', 'surgery', 'diagnosis',
        'symptom', 'pain', 'fever', 'treatment'
    ]
    
    transcript_lower = transcript.lower()
    # Handle both dict and string summary
    if isinstance(summary, dict):
        summary_text = ' '.join(str(v) for v in summary.values()).lower()
    else:
        summary_text = str(summary).lower()
    
    for keyword in medical_keywords:
        if keyword in transcript_lower and keyword not in summary_text:
            # Found a keyword in transcript but not in summary
            # Extract a snippet for context
            pattern = re.compile(rf'\b\w*{keyword}\w*\b', re.IGNORECASE)
            match = pattern.search(transcript)
            if match:
                start = max(0, match.start() - 50)
                end = min(len(transcript), match.end() + 50)
                snippet = transcript[start:end].strip()
                missing.append(f"Possible missing info about '{keyword}': ...{snippet}...")
    
    return missing
