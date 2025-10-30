"""
Semantic Quality Module.

Uses simple heuristics to detect meaningful omissions between
claims and evidence without relying on complex NLP or LLMs.
"""
import re
from typing import List
from .base import QualityModule
from .registry import register_quality_module
from ..types import Disposition, QualityIssue


@register_quality_module("semantic_quality")
class SemanticQualityModule(QualityModule):
    """
    Semantic quality analysis using simple heuristics.
    
    Detects meaningful omissions by identifying important details
    in evidence that are missing from claims:
    - Proper nouns (names, places)
    - Measurements and numbers
    - Quoted phrases
    - Contextual phrases (for X, with Y, etc.)
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize semantic quality module.
        
        Config options:
            min_quality_score: Analyze if quality_score < this (default: 0.95)
            min_confidence: Analyze if confidence < this (default: 0.75)
            analyze_insufficient: Analyze insufficient_evidence verdicts (default: True)
            max_issues: Maximum issues to report per claim (default: 3)
            min_phrase_length: Minimum words in a phrase to report (default: 2)
        """
        super().__init__(config)
        self.min_quality_score = self.config.get("min_quality_score", 0.95)
        self.min_confidence = self.config.get("min_confidence", 0.75)
        self.analyze_insufficient = self.config.get("analyze_insufficient", True)
        self.max_issues = self.config.get("max_issues", 3)
        self.min_phrase_length = self.config.get("min_phrase_length", 2)
    
    @property
    def name(self) -> str:
        return "semantic_quality"
    
    def should_analyze(self, disposition: Disposition) -> bool:
        """
        Determine if a disposition should undergo quality analysis.
        
        Triggers when any of the following are true:
          - Quality score below threshold (validator disagreement)
          - Confidence below threshold (validator uncertainty)
          - Verdict is 'insufficient_evidence' (borderline case)
          - Both quality_score and confidence are missing (no metrics available)
        
        Args:
            disposition: The disposition to check
        
        Returns:
            True if analysis should run, False to skip
        """
        # 0. Fallback gate - no metrics available
        if disposition.quality_score is None and disposition.confidence is None:
            return True  # Analyze when we have no quality metrics

        # 1. Quality gate - validator disagreement
        if disposition.quality_score is not None and disposition.quality_score < self.min_quality_score:
            return True

        # 2. Confidence gate - validator uncertainty
        if disposition.confidence is not None and disposition.confidence < self.min_confidence:
            return True

        # 3. Verdict gate - borderline cases
        if self.analyze_insufficient and disposition.verdict == "insufficient_evidence":
            return True

        # Otherwise skip analysis
        return False
    
    def analyze(
        self,
        disposition: Disposition,
        transcript: str
    ) -> dict:
        """
        Analyze for meaningful omissions between claim and evidence.
        
        Args:
            disposition: Validation result with claim and evidence
            transcript: Full transcript (not used in this simple version)
        
        Returns:
            List of detected quality issues
        """
        if not self.should_analyze(disposition):
            return {"issues": [], "quality_score": 1.0}
        
        if not disposition.evidence:
            return {"issues": [], "quality_score": 1.0}
        
        claim_text = disposition.claim.text
        evidence_text = disposition.evidence[0].text
        
        issues = []
        
        # Find important missing details (evidence → claim)
        missing_details = self._find_missing_important_details(
            claim_text,
            evidence_text
        )
        
        # Create quality issues for omissions
        for detail in missing_details[:self.max_issues]:
            issues.append(QualityIssue(
                type="omission",
                severity="low",
                detail=f"Claim omits important detail: '{detail}'",
                evidence_snippet=self._get_snippet(evidence_text, detail),
                claim_snippet=claim_text[:100],
                suggestion=f"Consider including: '{detail}'"
            ))
        
        # Find fabricated details (claim → evidence)
        fabricated_details = self._find_fabricated_details(
            claim_text,
            evidence_text
        )
        
        # Create quality issues for fabrications
        for detail in fabricated_details[:self.max_issues]:
            issues.append(QualityIssue(
                type="fabrication",
                severity="high",  # Fabrications are more serious than omissions
                detail=f"Claim includes detail not found in evidence: '{detail}'",
                evidence_snippet=evidence_text[:100],
                claim_snippet=self._get_snippet(claim_text, detail),
                suggestion=f"Verify or remove unsupported detail: '{detail}'"
            ))
        
        # Calculate quality_score based on issue severity
        quality_score = 1.0
        for issue in issues[:self.max_issues]:
            if issue.severity == "high":
                quality_score *= 0.5  # 50% penalty for high severity (fabrications)
            elif issue.severity == "medium":
                quality_score *= 0.8  # 20% penalty for medium severity
            elif issue.severity == "low":
                quality_score *= 0.9  # 10% penalty for low severity (omissions)
        
        return {
            "issues": issues[:self.max_issues],
            "quality_score": quality_score
        }
    
    def _find_missing_important_details(
        self,
        claim: str,
        evidence: str
    ) -> List[str]:
        """
        Find important details in evidence that are missing from claim.
        
        Uses simple heuristics:
        - Proper nouns (capitalized words/phrases)
        - Numbers with units (measurements)
        - Quoted phrases
        - Contextual prepositional phrases
        
        Args:
            claim: Claim text
            evidence: Evidence text
        
        Returns:
            List of missing important details, sorted by importance
        """
        important = []
        claim_lower = claim.lower()
        
        # 1. Find proper nouns (capitalized multi-word phrases)
        proper_nouns = self._extract_proper_nouns(evidence)
        for noun in proper_nouns:
            if noun.lower() not in claim_lower:
                if self._is_meaningful(noun):
                    important.append(noun)
        
        # 2. Find measurements (numbers with units) - improved detection
        measurements = re.findall(
            r'(\d+(?:\.\d+)?)\s*(x\s*\d+(?:\.\d+)?\s*)?(mg|cm|mm|kg|lb|g|ml|years?|months?|days?|hours?|minutes?|weeks?)',
            evidence,
            re.IGNORECASE
        )
        for num, multiplier, unit in measurements:
            # Reconstruct the full measurement
            full_measure = f"{num} {unit}" if not multiplier else f"{num} {multiplier}{unit}"
            
            # Check if this specific measurement is in claim
            if full_measure.lower() not in claim.lower():
                # Also check if just the number+unit combo exists
                simple_measure = f"{num} {unit}"
                if simple_measure.lower() not in claim.lower():
                    important.append(simple_measure)
        
        # 3. Find quoted phrases
        quotes = re.findall(r'"([^"]+)"', evidence)
        for quote in quotes:
            if quote.lower() not in claim_lower and len(quote.split()) >= self.min_phrase_length:
                if self._is_meaningful(quote):
                    important.append(f'"{quote}"')
        
        # 4. Find contextual prepositional phrases
        contextual = self._extract_contextual_phrases(evidence)
        for phrase in contextual:
            if phrase.lower() not in claim_lower:
                if self._is_meaningful(phrase):
                    important.append(phrase)
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for item in important:
            item_lower = item.lower()
            if item_lower not in seen:
                seen.add(item_lower)
                unique.append(item)
        
        return unique
    
    def _find_fabricated_details(
        self,
        claim: str,
        evidence: str
    ) -> List[str]:
        """
        Find important details in claim that are NOT found in evidence (fabrications).
        
        This is the reverse of _find_missing_important_details - it checks
        claim → evidence to detect hallucinations/fabrications.
        
        Args:
            claim: Claim text
            evidence: Evidence text
        
        Returns:
            List of fabricated details
        """
        fabricated = []
        evidence_lower = evidence.lower()
        
        # Stopwords to ignore (low-semantic tokens that don't indicate fabrication)
        STOP_TERMS = {
            'there', 'her', 'his', 'its', 'the', 'a', 'an', 'patient', 'subject',
            'this', 'that', 'these', 'those', 'he', 'she', 'it', 'they', 'them',
            'their', 'our', 'your', 'my', 'i', 'we', 'you', 'who', 'which', 'what',
            'when', 'where', 'why', 'how', 'is', 'was', 'are', 'were', 'been', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'of', 'in', 'on', 'at', 'to',
            'for', 'with', 'from', 'by', 'about', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'over', 'again',
            'further', 'then', 'once', 'here', 'also', 'all', 'both', 'each', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'just', 'now'
        }
        
        # 1. Check proper nouns in claim
        claim_nouns = self._extract_proper_nouns(claim)
        for noun in claim_nouns:
            # Skip if it's a stopword
            if noun.lower() in STOP_TERMS:
                continue
            if noun.lower() not in evidence_lower:
                if self._is_meaningful(noun):
                    fabricated.append(noun)
        
        # 2. Check key descriptive phrases (adjectives + nouns)
        # Look for patterns like "wet floor", "deep laceration", "severe pain"
        descriptive_patterns = [
            r'\b(wet|dry|deep|shallow|severe|mild|moderate|acute|chronic|large|small)\s+\w+',
            r'\b(hospital|clinic|emergency|urgent)\s+\w+',
        ]
        
        for pattern in descriptive_patterns:
            matches = re.finditer(pattern, claim, re.IGNORECASE)
            for match in matches:
                phrase = match.group(0)
                if phrase.lower() not in evidence_lower:
                    fabricated.append(phrase)
        
        # 3. Check medical symptoms/conditions mentioned in claim
        # Common symptoms that might be fabricated
        symptom_patterns = [
            r'\b(dizziness|nausea|vomiting|headache|fever|chills|weakness|fatigue)\b',
            r'\b(pain|ache|discomfort|soreness)\s+(?:in|at|around)\s+\w+',
        ]
        
        for pattern in symptom_patterns:
            matches = re.finditer(pattern, claim, re.IGNORECASE)
            for match in matches:
                symptom = match.group(0)
                if symptom.lower() not in evidence_lower:
                    fabricated.append(symptom)
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for item in fabricated:
            item_lower = item.lower()
            if item_lower not in seen:
                seen.add(item_lower)
                unique.append(item)
        
        return unique
    
    def _extract_proper_nouns(self, text: str) -> List[str]:
        """
        Extract proper nouns (capitalized words/phrases).
        
        Args:
            text: Text to extract from
        
        Returns:
            List of proper noun phrases
        """
        # Find sequences of capitalized words
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        matches = re.findall(pattern, text)
        
        # Filter out common non-proper-nouns
        stopwords = {'The', 'A', 'An', 'This', 'That', 'These', 'Those', 'I', 'He', 'She'}
        return [m for m in matches if m not in stopwords and len(m) > 2]
    
    def _extract_contextual_phrases(self, text: str) -> List[str]:
        """
        Extract contextual prepositional phrases that add meaning.
        
        Patterns like "for my husband", "with her assistance", etc.
        
        Args:
            text: Text to extract from
        
        Returns:
            List of contextual phrases
        """
        patterns = [
            r'for (?:my|his|her|their|the) \w+(?:\s+\w+)?',
            r'with (?:my|his|her|their|the) \w+(?:\s+\w+)?',
            r'about (?:my|his|her|their|the) \w+(?:\s+\w+)?',
            r'according to (?:the )?\w+',
            r'per (?:the )?\w+',
        ]
        
        phrases = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                phrase = match.group(0)
                if len(phrase.split()) >= self.min_phrase_length:
                    phrases.append(phrase)
        
        return phrases
    
    def _is_meaningful(self, phrase: str) -> bool:
        """
        Check if a phrase is meaningful (not just stopwords/articles).
        
        Args:
            phrase: Phrase to check
        
        Returns:
            True if phrase is meaningful
        """
        # Remove quotes if present
        phrase = phrase.strip('"')
        
        # Common stopwords and articles
        stopwords = {'the', 'a', 'an', 'it', 'this', 'that', 'these', 'those', 'by', 'at', 'in', 'on'}
        
        words = phrase.lower().split()
        
        # Must have at least one non-stopword
        meaningful_words = [w for w in words if w not in stopwords]
        
        return len(meaningful_words) >= 1
    
    def _get_snippet(self, text: str, phrase: str, context: int = 40) -> str:
        """
        Get a snippet of text around a phrase.
        
        Args:
            text: Full text
            phrase: Phrase to find
            context: Characters of context on each side
        
        Returns:
            Snippet with ellipsis if truncated
        """
        # Remove quotes for searching
        search_phrase = phrase.strip('"')
        
        # Find phrase in text (case-insensitive)
        pos = text.lower().find(search_phrase.lower())
        
        if pos == -1:
            # Phrase not found, return beginning of text
            return text[:min(100, len(text))] + ("..." if len(text) > 100 else "")
        
        # Get snippet with context
        start = max(0, pos - context)
        end = min(len(text), pos + len(search_phrase) + context)
        
        snippet = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
