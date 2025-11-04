"""
Temporal and Numeric Drift Quality Module.

Detects discrepancies in numbers, dates, durations, and temporal
context between claims and evidence using regex-based comparison.
"""
import re
import logging
from typing import List, Tuple, Set
from .base import QualityModule
from .registry import register_quality_module
from ..types import Disposition, QualityIssue, ScorePenalty

logger = logging.getLogger(__name__)

# Try to import spacy for number extraction
try:
    import spacy
    SPACY_AVAILABLE = True
    _nlp = None  # Lazy load
except ImportError:
    SPACY_AVAILABLE = False
    _nlp = None

# Try to import pint for unit handling
try:
    from pint import UnitRegistry
    PINT_AVAILABLE = True
    _ureg = None  # Lazy load
except ImportError:
    PINT_AVAILABLE = False
    _ureg = None


@register_quality_module("temporal_numeric_drift")
class TemporalNumericDriftModule(QualityModule):
    """
    Detects temporal and numeric drift between claims and evidence.
    
    Flags changes like:
    - "this morning" vs no time context
    - "6 years" → "4 years"
    - "10mg" → "5mg"
    - Dates that don't match
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize temporal/numeric drift module.
        
        Config options:
            min_quality_score: Analyze if quality_score < this (default: 0.95)
            tolerance_percent: Allow X% numeric difference (default: 10)
            check_temporal: Check temporal adverbs (default: True)
            check_numeric: Check numeric values (default: True)
            max_issues: Maximum issues to report (default: 3)
            context_window: Characters around number for context (default: 50)
            min_context_similarity: Minimum similarity to match contexts (default: 0.2)
            numeric_mismatch_severity: Severity for numeric mismatches (default: "high")
            insufficient_evidence_severity: Severity for missing numbers (default: "medium")
        """
        super().__init__(config)
        self.min_quality_score = self.config.get("min_quality_score", 0.95)
        self.tolerance_percent = self.config.get("tolerance_percent", 10)
        self.check_temporal = self.config.get("check_temporal", True)
        self.check_numeric = self.config.get("check_numeric", True)
        self.max_issues = self.config.get("max_issues", 3)
        self.context_window = self.config.get("context_window", 50)
        self.min_context_similarity = self.config.get("min_context_similarity", 0.2)
        
        # Configurable severity/penalty for numeric issues
        self.unit_mismatch_penalty = self.config.get("unit_mismatch_penalty", "high")
        self.numeric_mismatch_penalty = self.config.get("numeric_mismatch_penalty", "high")
        self.insufficient_evidence_penalty = self.config.get("insufficient_evidence_penalty", "medium")
        self.temporal_drift_penalty = self.config.get("temporal_drift_penalty", "medium")
        
        # Temporal adverbs and phrases
        self.temporal_patterns = [
            r'\bthis morning\b',
            r'\bthis afternoon\b',
            r'\bthis evening\b',
            r'\btonight\b',
            r'\byesterday\b',
            r'\blast night\b',
            r'\blast week\b',
            r'\blast month\b',
            r'\blast year\b',
            r'\btoday\b',
            r'\btomorrow\b',
            r'\brecently\b',
            r'\bearlier today\b',
        ]
    
    @property
    def name(self) -> str:
        return "temporal_numeric_drift"
    
    def should_analyze(self, disposition: Disposition) -> bool:
        """Only analyze if quality score indicates potential issues."""
        if disposition.quality_score is None:
            return True
        return disposition.quality_score < self.min_quality_score
    
    def analyze(
        self,
        disposition: Disposition,
        transcript: str
    ) -> dict:
        """
        Analyze for temporal and numeric drift.
        
        Args:
            disposition: Validation result with claim and evidence
            transcript: Full transcript (not used)
        
        Returns:
            Dict with 'issues' (List[QualityIssue]) and 'quality_score' (float)
        """
        if not self.should_analyze(disposition):
            return {"issues": [], "quality_score": 1.0}
        
        if not disposition.evidence:
            return {"issues": [], "quality_score": 1.0}
        
        claim_text = disposition.claim.text
        
        # Use first evidence for temporal drift
        evidence_text = disposition.evidence[0].text
        
        issues = []
        
        # Check temporal drift (using first evidence)
        if self.check_temporal:
            issues.extend(self._detect_temporal_drift(claim_text, evidence_text))
        
        # Check numeric drift (using ALL high-relevance evidence)
        if self.check_numeric:
            issues.extend(self._detect_numeric_drift_multi_evidence(claim_text, disposition.evidence))
        
        # Calculate quality_score using ScorePenalty enum
        quality_score = 1.0
        for issue in issues[:self.max_issues]:
            try:
                penalty = ScorePenalty.from_string(issue.severity)
                quality_score *= penalty.value
                logger.debug(f"Applied {issue.severity} penalty ({penalty.value}) for {issue.type}")
            except ValueError:
                # Fallback for unknown severity
                logger.warning(f"Unknown severity '{issue.severity}', using MEDIUM penalty")
                quality_score *= ScorePenalty.MEDIUM.value
        
        return {
            "issues": issues[:self.max_issues],
            "quality_score": quality_score
        }
    
    def _detect_temporal_drift(
        self,
        claim: str,
        evidence: str
    ) -> List[QualityIssue]:
        """
        Detect temporal context drift.
        
        Flags when evidence has temporal context but claim doesn't.
        """
        issues = []
        
        # Find temporal phrases in evidence
        evidence_temporal = set()
        for pattern in self.temporal_patterns:
            matches = re.finditer(pattern, evidence, re.IGNORECASE)
            for match in matches:
                evidence_temporal.add(match.group(0).lower())
        
        # Check if claim has these temporal phrases
        claim_lower = claim.lower()
        for temporal in evidence_temporal:
            if temporal not in claim_lower:
                issues.append(QualityIssue(
                    type="temporal_drift",
                    severity="medium",
                    detail=f"Evidence specifies temporal context '{temporal}' but claim omits it",
                    evidence_snippet=self._get_context(evidence, temporal),
                    claim_snippet=claim[:100],
                    suggestion=f"Consider adding temporal context: '{temporal}'"
                ))
        
        return issues
    
    def _detect_numeric_drift_multi_evidence(
        self,
        claim: str,
        evidence_spans: List
    ) -> List[QualityIssue]:
        """
        Detect numeric drift - domain agnostic approach.
        
        Strategy:
        1. Structured numbers (%, $, units): Must match exactly
        2. Bare numbers: Check if they exist ANYWHERE in high-relevance evidence
        
        Args:
            claim: Claim text
            evidence_spans: List of EvidenceSpan objects with text and score
        
        Returns:
            List of quality issues
        """
        issues = []
        
        # Extract numbers from claim
        claim_structured, claim_bare = self._extract_numeric_values(claim)
        
        if not claim_structured and not claim_bare:
            return []  # No numbers in claim, nothing to check
        
        logger.info(f"[NUMERIC DRIFT MULTI] Checking claim: '{claim[:100]}...'")
        logger.info(f"[NUMERIC DRIFT MULTI] Claim numbers: structured={claim_structured}, bare={claim_bare}")
        
        # Filter to high-relevance evidence (score > 0.5)
        high_relevance_evidence = [ev for ev in evidence_spans if ev.score > 0.5]
        
        if not high_relevance_evidence:
            logger.info(f"[NUMERIC DRIFT MULTI] No high-relevance evidence found")
            return []
        
        logger.info(f"[NUMERIC DRIFT MULTI] Checking {len(high_relevance_evidence)} high-relevance evidence spans")
        
        # Evidence is already sorted by relevance (highest first)
        # Process in order for accurate comparisons and early exit
        
        # Check structured numbers (%, $, units) - must match exactly
        for c_value, c_unit in claim_structured:
            found_match = False
            best_mismatch = None
            best_mismatch_score = 0
            unit_mismatch = None
            unit_mismatch_score = 0
            
            # Check evidence in order of relevance (highest first)
            for ev in high_relevance_evidence:
                ev_structured, ev_bare = self._extract_numeric_values(ev.text)
                
                # Look for matches in this evidence
                for e_value, e_unit in ev_structured:
                    # Check for exact match (same value, same unit)
                    if e_unit == c_unit and self._values_match(e_value, c_value):
                        found_match = True
                        logger.info(f"[NUMERIC DRIFT MULTI] Structured match: {c_value} {c_unit} ≈ {e_value} {e_unit} (relevance: {ev.score:.2f})")
                        break
                    
                    # Check for unit mismatch (same value, different unit)
                    if e_value == c_value and e_unit != c_unit:
                        if not unit_mismatch or ev.score > unit_mismatch_score:
                            unit_mismatch = (e_value, e_unit)
                            unit_mismatch_score = ev.score
                            logger.info(f"[NUMERIC DRIFT MULTI] Unit mismatch detected: {c_value} {c_unit} vs {e_value} {e_unit} (relevance: {ev.score:.2f})")
                    
                    # Check for value mismatch (same unit, different value)
                    elif e_unit == c_unit and not self._values_match(e_value, c_value):
                        if not best_mismatch or ev.score > best_mismatch_score:
                            best_mismatch = (e_value, e_unit)
                            best_mismatch_score = ev.score
                            logger.info(f"[NUMERIC DRIFT MULTI] Value mismatch: {c_value} {c_unit} vs {e_value} {e_unit} (relevance: {ev.score:.2f})")
                
                if found_match:
                    break  # Early exit - found match in most relevant evidence
            
            if not found_match:
                # Prioritize unit mismatch over value mismatch
                if unit_mismatch:
                    issues.append(QualityIssue(
                        type="unit_mismatch",
                        severity="high",  # Unit mismatches are always critical!
                        detail=f"UNIT MISMATCH: Claim says '{c_value} {c_unit}' but evidence says '{unit_mismatch[0]} {unit_mismatch[1]}'",
                        suggestion=f"Verify the correct unit: '{unit_mismatch[1]}' or '{c_unit}' - this could be a {abs(self._unit_conversion_factor(c_unit, unit_mismatch[1]))}x difference"
                    ))
                elif best_mismatch:
                    issues.append(QualityIssue(
                        type="numeric_mismatch",
                        severity=self.numeric_mismatch_penalty,
                        detail=f"Claim says '{c_value} {c_unit}' but high-relevance evidence says '{best_mismatch[0]} {best_mismatch[1]}'",
                        suggestion=f"Verify the correct value: '{best_mismatch[0]}' or '{c_value}'"
                    ))
                else:
                    issues.append(QualityIssue(
                        type="insufficient_numeric_evidence",
                        severity=self.insufficient_evidence_penalty,
                        detail=f"Claim mentions '{c_value} {c_unit}' but no high-relevance evidence contains this number",
                        suggestion=f"Verify '{c_value}' or check if evidence supports a different value"
                    ))
        
        # Check bare numbers - just need to exist SOMEWHERE in high-relevance evidence
        # Only check bare numbers that aren't already in structured (avoid duplicates)
        structured_values = {v for v, u in claim_structured}
        bare_only = [b for b in claim_bare if b not in structured_values]
        
        for claim_num in bare_only:
            found = False
            # Check evidence in order of relevance
            for ev in high_relevance_evidence:
                ev_structured, ev_bare = self._extract_numeric_values(ev.text)
                if claim_num in ev_bare:
                    found = True
                    logger.info(f"[NUMERIC DRIFT MULTI] Bare number '{claim_num}' found in evidence (relevance: {ev.score:.2f})")
                    break  # Early exit
            
            if not found:
                logger.info(f"[NUMERIC DRIFT MULTI] Bare number '{claim_num}' not found in any high-relevance evidence")
                issues.append(QualityIssue(
                    type="insufficient_numeric_evidence",
                    severity=self.insufficient_evidence_penalty,
                    detail=f"Claim mentions '{claim_num}' but no high-relevance evidence contains this number",
                    suggestion=f"Verify '{claim_num}' or check if evidence supports a different value"
                ))
        
        return issues
    
    def _detect_numeric_drift(
        self,
        claim: str,
        evidence: str
    ) -> List[QualityIssue]:
        """
        Detect numeric value drift using context-similarity matching.
        
        Domain-agnostic approach:
        1. Extract all numbers with surrounding context
        2. Match numbers by context similarity
        3. Flag mismatches
        """
        issues = []
        
        # Log the actual text being analyzed
        logger.info(f"[NUMERIC DRIFT] Analyzing claim: '{claim[:100]}...'")
        logger.info(f"[NUMERIC DRIFT] Against evidence: '{evidence[:200]}...'")
        
        # Extract numeric values with units (percentages, money, measurements) + bare numbers
        evidence_structured, evidence_bare = self._extract_numeric_values(evidence)
        claim_structured, claim_bare = self._extract_numeric_values(claim)
        
        logger.info(f"[NUMERIC DRIFT] Evidence structured numbers: {evidence_structured}")
        logger.info(f"[NUMERIC DRIFT] Evidence bare numbers: {evidence_bare}")
        logger.info(f"[NUMERIC DRIFT] Claim structured numbers: {claim_structured}")
        logger.info(f"[NUMERIC DRIFT] Claim bare numbers: {claim_bare}")
        
        # Check for mismatches in structured numbers (with units)
        for c_value, c_unit in claim_structured:
            # Tier 1: Try to find same unit in evidence (structured match)
            matching_evidence = [(e_value, e_unit) for e_value, e_unit in evidence_structured if e_unit == c_unit]
            
            if matching_evidence:
                # Found structured match - compare values
                for e_value, e_unit in matching_evidence:
                    if not self._values_match(e_value, c_value):
                        issues.append(QualityIssue(
                            type="numeric_drift",
                            severity="high",
                            detail=f"Numeric mismatch: evidence says '{e_value} {e_unit}' but claim says '{c_value} {c_unit}'",
                            evidence_snippet=self._get_context(evidence, f"{e_value} {e_unit}"),
                            claim_snippet=self._get_context(claim, f"{c_value} {c_unit}"),
                            suggestion=f"Verify the correct value: '{e_value} {e_unit}' or '{c_value} {c_unit}'"
                        ))
            else:
                # Tier 2: No structured match - check if claim number exists in evidence bare numbers
                # This handles cases like "30 employees" (claim) vs "hired 25" (evidence, no term)
                if c_value in evidence_bare:
                    # Found the claim number in evidence - but need to find what it actually says
                    # Look for any different number in evidence bare that could be the mismatch
                    different_nums = [num for num in evidence_bare if num != c_value and not self._values_match(num, c_value)]
                    if different_nums:
                        # Found a different number - likely a mismatch
                        issues.append(QualityIssue(
                            type="numeric_drift",
                            severity="high",
                            detail=f"Numeric mismatch: claim says '{c_value} {c_unit}' but evidence mentions '{different_nums[0]}' (no matching term found)",
                            evidence_snippet=self._get_context(evidence, different_nums[0]),
                            claim_snippet=self._get_context(claim, f"{c_value} {c_unit}"),
                            suggestion=f"Verify the correct value: '{different_nums[0]}' or '{c_value}'"
                        ))
        
        # Note: We rely on semantic retrieval to match claim to relevant evidence.
        # The evidence text here is already semantically matched to the claim.
        # No need for additional context similarity matching - that would be redundant
        # and can cause duplicates or false matches.
        
        return issues
    
    def _get_nlp(self):
        """Lazy load SpaCy model."""
        global _nlp
        if _nlp is None and SPACY_AVAILABLE:
            try:
                _nlp = spacy.load('en_core_web_sm')
            except OSError:
                logger.warning("SpaCy model 'en_core_web_sm' not found. Falling back to regex.")
        return _nlp
    
    def _get_ureg(self):
        """Lazy load Pint unit registry."""
        global _ureg
        if _ureg is None and PINT_AVAILABLE:
            try:
                _ureg = UnitRegistry()
            except Exception as e:
                logger.warning(f"Failed to initialize Pint UnitRegistry: {e}")
        return _ureg
    
    def _extract_quantities_with_pint(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Extract quantities with units using Pint.
        
        Handles word-form units like "milligrams", "grams", etc.
        
        Returns:
            List of (value, unit, normalized_unit) tuples
            e.g., [('20', 'milligrams', 'mg'), ('10', 'grams', 'g')]
        """
        ureg = self._get_ureg()
        if not ureg:
            return []
        
        quantities = []
        
        # Pattern to match number + unit (word form or abbreviation)
        # Matches: "20 milligrams", "10mg", "5 grams", "100 g"
        quantity_pattern = r'(\d+(?:\.\d+)?)\s*(milligrams?|grams?|kilograms?|mg|g|kg|milliliters?|liters?|ml|l|years?|months?|days?|hours?|minutes?|weeks?)'
        
        for match in re.finditer(quantity_pattern, text, re.IGNORECASE):
            value = match.group(1)
            unit_text = match.group(2).lower()
            
            try:
                # Parse with Pint
                quantity = ureg(f"{value} {unit_text}")
                
                # Get normalized unit (e.g., "milligrams" → "mg")
                normalized_unit = f"{quantity.units:~}"  # Compact format
                
                logger.info(f"[PINT] Extracted: {value} {unit_text} → {value} {normalized_unit}")
                quantities.append((value, unit_text, normalized_unit))
                
            except Exception as e:
                logger.debug(f"[PINT] Could not parse '{value} {unit_text}': {e}")
                continue
        
        return quantities
    
    def _extract_numbers_with_spacy(self, text: str) -> List[str]:
        """
        Extract numbers using SpaCy's NER (handles both digits and words).
        
        Returns:
            List of number strings (e.g., ['30', '25', '3', '2'])
        """
        nlp = self._get_nlp()
        if not nlp:
            return []
        
        doc = nlp(text)
        numbers = []
        
        for ent in doc.ents:
            if ent.label_ == 'CARDINAL':  # Numeric entities
                # SpaCy recognizes both "30" and "three" as CARDINAL
                numbers.append(ent.text)
                logger.info(f"[SPACY] Found number: '{ent.text}' in context: '{ent.sent.text[:100]}'")
        
        return numbers
    
    def _extract_numeric_values(self, text: str) -> Tuple[List[Tuple[str, str]], List[str]]:
        """
        Extract numeric values - domain agnostic approach with Pint support.
        
        Structured numbers: percentages, money, measurements (with units)
        Bare numbers: ALL numbers (digits + word-form via SpaCy)
        
        Returns:
            Tuple of (structured_numbers, bare_numbers)
            - structured_numbers: List of (value, normalized_unit) tuples
            - bare_numbers: List of ALL number strings found
        """
        structured = []
        bare_numbers = []
        
        # 1. Use Pint to extract quantities with units (handles word-form units!)
        pint_quantities = self._extract_quantities_with_pint(text)
        for value, original_unit, normalized_unit in pint_quantities:
            structured.append((value, normalized_unit))
            bare_numbers.append(value)
            logger.info(f"[EXTRACT PINT] {value} {original_unit} → ({value}, {normalized_unit})")
        
        # 2. Percentages (15%, 12%)
        percent_pattern = r'(\d+(?:\.\d+)?)\s*%'
        for match in re.finditer(percent_pattern, text):
            value = match.group(1)
            structured.append((value, '%'))
            bare_numbers.append(value)
        
        # 3. Dollar amounts ($48M, $45 million, $5M)
        money_pattern = r'\$\s*(\d+(?:\.\d+)?)\s*(million|billion|thousand|[MBK])?'
        for match in re.finditer(money_pattern, text, re.IGNORECASE):
            value = match.group(1)
            unit_raw = match.group(2) or ''
            # Normalize money units
            unit = unit_raw.lower()
            if unit in ['m', 'million']:
                unit = 'million'
            elif unit in ['b', 'billion']:
                unit = 'billion'
            elif unit in ['k', 'thousand']:
                unit = 'thousand'
            structured.append((value, f'${unit}' if unit else '$'))
            bare_numbers.append(value)
        
        # 4. Use SpaCy to extract ALL numbers (digits + word-form like "three", "two")
        spacy_numbers = self._extract_numbers_with_spacy(text)
        for num_text in spacy_numbers:
            if num_text not in bare_numbers:  # Avoid duplicates
                bare_numbers.append(num_text)
        
        # 5. Extract ALL digit-form numbers as fallback (in case SpaCy missed any)
        for match in re.finditer(r'\b(\d+)\b', text):
            num = match.group(1)
            if num not in bare_numbers:  # Avoid duplicates
                bare_numbers.append(num)
        
        logger.info(f"[EXTRACT] Text: '{text[:100]}...'")
        logger.info(f"[EXTRACT] Structured: {structured}")
        logger.info(f"[EXTRACT] Bare: {bare_numbers}")
        
        return structured, bare_numbers
    
    def _unit_conversion_factor(self, unit1: str, unit2: str) -> float:
        """
        Calculate conversion factor between two units using Pint.
        
        Args:
            unit1: First unit (e.g., 'g')
            unit2: Second unit (e.g., 'mg')
        
        Returns:
            Conversion factor (e.g., 1000 for g→mg)
        """
        ureg = self._get_ureg()
        if not ureg:
            return 1.0
        
        try:
            # Create quantities with value 1
            q1 = ureg(f"1 {unit1}")
            q2 = ureg(f"1 {unit2}")
            
            # Convert and get ratio
            converted = q1.to(unit2)
            factor = converted.magnitude
            
            return factor
        except Exception as e:
            logger.debug(f"Could not calculate conversion factor for {unit1}→{unit2}: {e}")
            return 1.0
    
    def _values_match(self, val1: str, val2: str) -> bool:
        """
        Check if two numeric values match within tolerance.
        
        Args:
            val1: First value as string
            val2: Second value as string
        
        Returns:
            True if values match within tolerance
        """
        try:
            v1 = float(val1)
            v2 = float(val2)
            
            # Check if within tolerance percentage
            if v1 == 0 and v2 == 0:
                return True
            
            max_val = max(abs(v1), abs(v2))
            diff_percent = abs(v1 - v2) / max_val * 100
            
            return diff_percent <= self.tolerance_percent
        except ValueError:
            # If can't convert to float, do string comparison
            return val1 == val2
    
    def _get_context(self, text: str, phrase: str, context: int = 40) -> str:
        """
        Get context around a phrase.
        
        Args:
            text: Full text
            phrase: Phrase to find
            context: Characters of context
        
        Returns:
            Snippet with context
        """
        pos = text.lower().find(phrase.lower())
        
        if pos == -1:
            return text[:min(100, len(text))] + ("..." if len(text) > 100 else "")
        
        start = max(0, pos - context)
        end = min(len(text), pos + len(phrase) + context)
        
        snippet = text[start:end]
        
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
