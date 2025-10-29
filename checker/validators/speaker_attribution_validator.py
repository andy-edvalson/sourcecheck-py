import re
from typing import List, Set
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition

@register_validator("speaker_attribution_validator")
class SpeakerAttributionValidator(Validator):
    """
    Validates the 'historians' field by heuristically attributing speakers
    in the transcript.
    """

    @property
    def name(self) -> str:
        return "speaker_attribution_validator"

    def _extract_historians(self, transcript: str) -> Set[str]:
        historians = set()

        # Always assume patient is a speaker
        historians.add("Patient")

        # Look for common co-historian patterns
        if re.search(r'\b(my|the)\s+(daughter|son|wife|husband|mother|father|sister|brother)\b', transcript, re.I):
            matches = re.findall(r'\b(my|the)\s+(daughter|son|wife|husband|mother|father|sister|brother)\b', transcript, re.I)
            for _, relation in matches:
                historians.add(relation.capitalize())

        return historians

    def validate(self, claim: Claim, evidence: List[EvidenceSpan], transcript: str) -> Disposition:
        claimed_historians = {s.strip().capitalize() for s in claim.text.split('|') if s.strip()}
        detected_historians = self._extract_historians(transcript)

        missing = claimed_historians - detected_historians
        if not missing:
            verdict = "supported"
            explanation = f"All claimed historians found in transcript: {claimed_historians}"
        else:
            verdict = "insufficient_evidence"
            explanation = f"Missing historians: {missing}. Detected: {detected_historians}"

        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=[],
            validator=self.name,
            explanation=explanation
        )
