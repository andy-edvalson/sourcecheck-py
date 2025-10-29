"""
regex_validator.py

A simple, configurable regex-based validator for exact/near-exact facts
(age, sex, tetanus status, vitals, simple structured phrases).

Usage:
- Registeres as "regex_validator" in the validator registry.
- Configurable via validator config (self.config). Defaults provided.
- validate(claim, evidence, transcript) -> Disposition

Behavior:
1. If evidence spans are provided, tries to match patterns inside each span.
2. If no evidence or no matches in evidence, searches the full transcript.
3. Returns `supported` when at least one match is found, `insufficient_evidence` otherwise.
4. Produces EvidenceSpan(s) for each regex match (score=1.0).
"""

import re
from typing import List, Dict, Pattern, Tuple, Optional
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition


DEFAULT_PATTERNS = {
    # identifiers: age and sex
    "identifiers": [
        r"(?P<age>\b\d{1,3})\s*[-]?\s*year\s*[-]?\s*old\b",                        # 56-year-old / 56 year old
        r"\bage\s*(?:is|:)?\s*(?P<age2>\d{1,3})\b",                               # age 56 / age: 56
        r"\b(?P<sex>male|female|man|woman|m\b|f\b|M\b|F\b)\b",                    # male/female/M/F
        r"\b(?P<age3>\d{1,3})\s*yo\b",                                            # 56yo
    ],

    # tetanus: simple phrasing
    "tetanus": [
        r"tetanus (?:shot|vaccination|vaccine) (?:status )?(?:is )?(?P<years>\d{1,2})\s*years?\s*ago\b",
        r"last tetanus (?:shot|vaccine|vaccination) (?:was )?(?P<years2>\d{1,2})\s*years?\s*ago\b",
        r"tetanus (?:status )?(?:up to date|uptodate|up-to-date)",
    ],

    # vitals (simple numeric patterns)
    "vitals": [
        r"\bhr[: ]?\s*(?P<hr>\d{2,3})\b",
        r"\bbp[: ]?\s*(?P<systolic>\d{2,3})[\/](?P<diastolic>\d{2,3})\b",
        r"\btemp[: ]?\s*(?P<temp>\d{2}\.\d)\b",
    ],

    # generic exact phrase fallback (useful for dispositions, follow-ups)
    "phrase": [
        r"\bdischarg(?:ed|e)[: ]?\s*(?P<dispo>home|admit|observation)\b",
        r"\bfollow[- ]?up (?:in|at) \d{1,3} (?:hours|days)\b",
        r"\bwound care instructions\b",
        r"\bsuture removal\b",
    ],
}


def _compile_patterns(pattern_list: List[str]) -> List[Pattern[str]]:
    return [re.compile(pat, flags=re.IGNORECASE) for pat in pattern_list]


@register_validator("regex_validator")
class RegexValidator(Validator):
    """
    Regex-based validator.

    Configuration (self.config) options:
      patterns: dict mapping field -> list of regex strings (overrides defaults)
      search_transcript_if_no_evidence: bool (default True)
      min_matches: int (default 1)  # number of matches required to consider supported
    """

    def __init__(self, config: Dict = None, debug: bool = False):
        super().__init__(config, debug)
        cfg = self.config or {}
        # Merge defaults with provided patterns (provided overrides)
        provided = cfg.get("patterns", {})
        merged = dict(DEFAULT_PATTERNS)
        for k, v in provided.items():
            # v expected to be list of pattern strings
            merged[k] = v
        # Compile patterns by field name
        self.compiled: Dict[str, List[Pattern[str]]] = {
            k: _compile_patterns(v) for k, v in merged.items()
        }
        self.search_transcript_if_no_evidence: bool = cfg.get(
            "search_transcript_if_no_evidence", True
        )
        self.min_matches: int = int(cfg.get("min_matches", 1))

    @property
    def name(self) -> str:
        return "regex_validator"

    def _match_in_text(self, patterns: List[Pattern[str]], text: str) -> List[Tuple[int, int, str]]:
        """
        Return list of (start, end, matched_text) for all patterns found in text.
        """
        matches = []
        for pat in patterns:
            for m in pat.finditer(text):
                start, end = m.start(), m.end()
                matches.append((start, end, text[start:end]))
        return matches

    def _find_patterns_for_field(self, field: str) -> Optional[List[Pattern[str]]]:
        """
        Heuristic mapping from claim field to pattern groups.
        """
        fld = field.lower() if field else ""
        # direct mapping
        if fld in self.compiled:
            return self.compiled[fld]
        # heuristics
        if "identif" in fld or fld == "identifiers":
            return self.compiled.get("identifiers")
        if "tetanus" in fld or "tetanus" in fld:
            return self.compiled.get("tetanus")
        if "vital" in fld or fld in ("vital_signs", "vitals"):
            return self.compiled.get("vitals")
        if "follow" in fld or fld == "follow_up":
            return self.compiled.get("phrase")
        if "dispo" in fld or fld == "disposition":
            return self.compiled.get("phrase")
        # fallback: try generic phrase patterns
        return self.compiled.get("phrase")

    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        """
        Validate a claim by regex search.

        Priority:
          1) Search evidence spans provided (if any)
          2) If none found and config allows, search full transcript

        Returns a Disposition object.
        """
        field = getattr(claim, "field", "") or ""
        text_to_match = claim.text or ""
        patterns = self._find_patterns_for_field(field)

        matched_spans: List[EvidenceSpan] = []

        # If the claim text itself looks like an age/sex tuple, try direct match first
        # (e.g., "56-year-old female") — quick sanity pass
        if field == "identifiers":
            # quick direct match against the claim text
            if patterns:
                for pat in patterns:
                    m = pat.search(text_to_match)
                    if m:
                        # treat the claim itself as evidence (high confidence)
                        matched_spans.append(EvidenceSpan(
                            text=text_to_match,
                            start_idx=0,
                            end_idx=len(text_to_match),
                            score=1.0
                        ))
                        break

        # 1) Search inside provided evidence spans
        if evidence and patterns:
            for ev in evidence:
                ev_text = ev.text or ""
                matches = self._match_in_text(patterns, ev_text)
                for (s, e, matched_text) in matches:
                    # compute absolute positions if evidence provides start_idx
                    abs_start = (ev.start_idx or 0) + s if ev.start_idx is not None else s
                    abs_end = (ev.start_idx or 0) + e if ev.start_idx is not None else e
                    matched_spans.append(EvidenceSpan(
                        text=matched_text,
                        start_idx=abs_start,
                        end_idx=abs_end,
                        score=1.0
                    ))
            # If we found enough matches, return supported
            if len(matched_spans) >= self.min_matches:
                return Disposition(
                    claim=claim,
                    verdict="supported",
                    evidence=matched_spans[: self.config.get("max_evidence_spans", 5)],
                    validator=self.name,
                    explanation=f"Found {len(matched_spans)} regex match(es) in evidence spans."
                )

        # 2) Search full transcript if allowed
        if self.search_transcript_if_no_evidence and patterns and transcript:
            for pat in patterns:
                for m in pat.finditer(transcript):
                    matched_text = m.group(0)
                    matched_spans.append(EvidenceSpan(
                        text=matched_text,
                        start_idx=m.start(),
                        end_idx=m.end(),
                        score=1.0
                    ))
                    if len(matched_spans) >= self.min_matches:
                        break
                if len(matched_spans) >= self.min_matches:
                    break

            if len(matched_spans) >= self.min_matches:
                return Disposition(
                    claim=claim,
                    verdict="supported",
                    evidence=matched_spans[: self.config.get("max_evidence_spans", 5)],
                    validator=self.name,
                    explanation=f"Found {len(matched_spans)} regex match(es) in transcript."
                )

        # No matches found
        explanation = "No regex matches found"
        if not patterns:
            explanation = "No patterns available for this field"
        return Disposition(
            claim=claim,
            verdict="insufficient_evidence",
            evidence=[],
            validator=self.name,
            explanation=explanation
        )
