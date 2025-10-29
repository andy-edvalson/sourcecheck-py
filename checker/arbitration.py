"""
Arbitration Engine for resolving conflicts between validators.

Provides config-driven conflict resolution, weighted voting, and
transparent explanation of arbitration decisions.
"""
import logging
from typing import List, Optional, Dict, Any
from .types import Claim, EvidenceSpan, Disposition, ValidatorResult

logger = logging.getLogger(__name__)


class ArbitrationEngine:
    """
    Resolves conflicts between validators using config-driven rules.
    
    Supports multiple aggregation strategies:
    - weighted_voting: Aggregate using validator weights
    - priority_based: Use configured verdict priority order
    - unanimous: Require all validators to agree
    - majority: Use majority vote
    - first_wins: Use first validator's result
    
    Also supports conflict resolution rules for specific scenarios.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize arbitration engine with configuration.
        
        Args:
            config: Aggregation configuration from policies.yaml
        
        Raises:
            ValueError: If configuration is invalid
        """
        cfg = config or {}
        
        self.strategy = cfg.get("strategy", "priority_based")
        self.weights = cfg.get("default_weights", {})
        self.priority = cfg.get("verdict_priority", ["refuted", "supported", "insufficient_evidence"])
        self.conflict_rules = cfg.get("conflict_resolution", [])
        self.explain_conflicts = cfg.get("explain_conflicts", True)
        self.min_confidence = cfg.get("min_confidence", 0.0)
        
        # Validate configuration
        self.validate_config()
    
    def validate_config(self):
        """
        Validate arbitration configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate strategy
        valid_strategies = ["weighted_voting", "priority_based", "unanimous", "majority", "first_wins"]
        if self.strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy '{self.strategy}'. "
                f"Must be one of: {valid_strategies}"
            )
        
        # Validate weights (if using weighted_voting)
        if self.strategy == "weighted_voting":
            if not self.weights:
                raise ValueError(
                    "weighted_voting strategy requires 'default_weights' configuration"
                )
            for validator, weight in self.weights.items():
                if not isinstance(weight, (int, float)) or weight < 0:
                    raise ValueError(
                        f"Invalid weight for validator '{validator}': {weight}. "
                        f"Weights must be non-negative numbers."
                    )
        
        # Validate priority order
        valid_verdicts = {"supported", "refuted", "insufficient_evidence"}
        for verdict in self.priority:
            if verdict not in valid_verdicts:
                raise ValueError(
                    f"Invalid verdict in priority order: '{verdict}'. "
                    f"Must be one of: {valid_verdicts}"
                )
        
        # Validate conflict resolution rules
        for i, rule in enumerate(self.conflict_rules):
            if not isinstance(rule, dict):
                raise ValueError(f"Conflict rule {i} must be a dictionary")
            
            if "action" not in rule:
                raise ValueError(f"Conflict rule {i} missing required 'action' field")
            
            if "validators" not in rule:
                raise ValueError(f"Conflict rule {i} missing required 'validators' field")
            
            validators = rule.get("validators", [])
            if not isinstance(validators, list):
                raise ValueError(
                    f"Conflict rule {i}: 'validators' must be a list"
                )
            
            if len(validators) < 2:
                raise ValueError(
                    f"Conflict rule {i}: 'validators' must contain at least 2 validators. "
                    f"Got: {validators}"
                )
            
            # Validate action-specific requirements
            action = rule.get("action")
            if action == "check_lexical_overlap":
                if "threshold" not in rule:
                    raise ValueError(
                        f"Conflict rule {i}: 'check_lexical_overlap' action requires 'threshold' field"
                    )
                threshold = rule.get("threshold")
                if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 1):
                    raise ValueError(
                        f"Conflict rule {i}: 'threshold' must be a number between 0 and 1. "
                        f"Got: {threshold}"
                    )
    
    def arbitrate(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Disposition:
        """
        Arbitrate between multiple validator results.
        
        Args:
            claim: The claim being validated
            validator_results: Results from all validators
            evidence: Evidence spans retrieved for this claim
        
        Returns:
            Final disposition after arbitration
        """
        if not validator_results:
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=evidence,
                validator="arbitration_engine",
                explanation="No validator results to arbitrate",
                validator_results=[]
            )
        
        if len(validator_results) == 1:
            # Single validator - use its result directly
            vr = validator_results[0]
            return Disposition(
                claim=claim,
                verdict=vr.verdict,
                evidence=evidence,
                validator=vr.validator,
                explanation=vr.explanation,
                validator_results=validator_results,
                confidence=vr.score
            )
        
        # Check for conflicts
        verdicts = [vr.verdict for vr in validator_results]
        has_conflict = len(set(verdicts)) > 1
        
        if has_conflict and self.conflict_rules:
            # Apply conflict resolution rules
            resolved = self._apply_conflict_rules(claim, validator_results, evidence)
            if resolved:
                return resolved
        
        # Apply aggregation strategy
        if self.strategy == "weighted_voting":
            disposition = self._weighted_voting(claim, validator_results, evidence)
        elif self.strategy == "unanimous":
            disposition = self._unanimous(claim, validator_results, evidence)
        elif self.strategy == "majority":
            disposition = self._majority(claim, validator_results, evidence)
        elif self.strategy == "first_wins":
            disposition = self._first_wins(claim, validator_results, evidence)
        else:
            # Default: priority-based
            disposition = self._priority_based(claim, validator_results, evidence)
        
        # Calculate quality score based on validator agreement
        quality_score = self._calculate_quality_score(validator_results, disposition.verdict)
        disposition.quality_score = quality_score
        
        # Log arbitration decision for telemetry
        logger.debug(
            "Arbitration decision",
            extra={
                "claim_field": claim.field,
                "claim_text_preview": claim.text[:100] if claim.text else "",
                "strategy": self.strategy,
                "validator_verdicts": {vr.validator: vr.verdict for vr in validator_results},
                "validator_scores": {vr.validator: vr.score for vr in validator_results},
                "final_verdict": disposition.verdict,
                "quality_score": quality_score,
                "has_conflict": has_conflict,
                "weights": self.weights if self.strategy == "weighted_voting" else None
            }
        )
        
        return disposition
    
    def _apply_conflict_rules(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Optional[Disposition]:
        """
        Apply config-driven conflict resolution rules.
        
        Args:
            claim: The claim being validated
            validator_results: Results from all validators
            evidence: Evidence spans
        
        Returns:
            Resolved disposition if rule matches, None otherwise
        """
        for rule in self.conflict_rules:
            # Get validator names to check for conflicts
            validator_names = rule.get("validators", [])
            
            if not validator_names or len(validator_names) < 2:
                continue
            
            # Find these validators in results
            matched_results = []
            for name in validator_names:
                for vr in validator_results:
                    if vr.validator == name:
                        matched_results.append(vr)
                        break
            
            # Check if we found all specified validators and they disagree
            if len(matched_results) == len(validator_names):
                verdicts = [vr.verdict for vr in matched_results]
                
                # Only apply rule if there's a conflict (different verdicts)
                if len(set(verdicts)) > 1:
                    action = rule.get("action")
                    
                    if action == "check_lexical_overlap" and evidence:
                        overlap = self._lexical_overlap(claim.text, evidence[0].text)
                        threshold = rule.get("threshold", 0.6)
                        
                        # Build explanation showing the conflict
                        conflict_desc = " vs ".join([f"{vr.validator}={vr.verdict}" for vr in matched_results])
                        
                        if overlap >= threshold:
                            verdict = rule.get("result_if_above", "supported")
                            explanation = (
                                f"Conflict resolved via lexical overlap: "
                                f"{conflict_desc}. "
                                f"Overlap {overlap:.2f} >= {threshold} threshold, "
                                f"accepting as {verdict}."
                            )
                        else:
                            # Low overlap - use the more conservative verdict
                            # If any validator said "refuted", use that
                            # Otherwise use "insufficient_evidence"
                            has_refuted = any(vr.verdict == "refuted" for vr in matched_results)
                            verdict = "refuted" if has_refuted else "insufficient_evidence"
                            
                            explanation = (
                                f"Conflict resolved via lexical overlap: "
                                f"{conflict_desc}. "
                                f"Overlap {overlap:.2f} < {threshold} threshold, "
                                f"accepting as {verdict}."
                            )
                        
                        return Disposition(
                            claim=claim,
                            verdict=verdict,
                            evidence=evidence,
                            validator="arbitration_engine",
                            explanation=explanation,
                            validator_results=validator_results
                        )
        
        return None
    
    def _calculate_quality_score(
        self,
        validator_results: List[ValidatorResult],
        final_verdict: str
    ) -> float:
        """
        Calculate quality score based on validator agreement.
        
        Quality score reflects how much validators agree:
        - 1.0: All validators agree with final verdict
        - 0.5-0.9: Some disagreement but majority agrees
        - 0.0-0.5: Significant disagreement
        
        Args:
            validator_results: Results from all validators
            final_verdict: The final verdict after arbitration
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not validator_results:
            return 1.0
        
        if len(validator_results) == 1:
            # Single validator - perfect quality
            return 1.0
        
        # Count how many validators agree with final verdict
        agreement_count = sum(
            1 for vr in validator_results
            if vr.verdict == final_verdict
        )
        
        # Base quality score on agreement rate
        agreement_rate = agreement_count / len(validator_results)
        
        # Penalize if there's a refutation that was overridden
        has_overridden_refutation = any(
            vr.verdict == "refuted" and final_verdict != "refuted"
            for vr in validator_results
        )
        
        if has_overridden_refutation:
            # Reduce quality score when overriding a refutation
            # This flags potential issues for review
            agreement_rate *= 0.9
        
        return round(agreement_rate, 3)
    
    def _lexical_overlap(self, text1: str, text2: str) -> float:
        """
        Calculate Jaccard similarity (lexical overlap) between two texts.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Overlap score between 0.0 and 1.0
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _weighted_voting(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Disposition:
        """
        Aggregate using weighted voting with confidence normalization.
        
        Each validator's verdict is weighted by its configured weight
        multiplied by its confidence score (if available).
        The verdict with the highest total weight wins.
        """
        verdict_scores: Dict[str, float] = {
            "supported": 0.0,
            "refuted": 0.0,
            "insufficient_evidence": 0.0
        }
        
        for vr in validator_results:
            weight = self.weights.get(vr.validator, 1.0)
            # Normalize by confidence if available (default to 1.0)
            confidence = vr.score if vr.score is not None else 1.0
            verdict_scores[vr.verdict] += weight * confidence
        
        # Get verdict with highest score
        final_verdict = max(verdict_scores, key=verdict_scores.get)
        
        # Build explanation
        explanation = f"Weighted voting result: {final_verdict}. "
        explanation += f"Scores: {verdict_scores}. "
        
        if self.explain_conflicts:
            validator_verdicts = [
                (vr.validator, vr.verdict, self.weights.get(vr.validator, 1.0), vr.score or 1.0) 
                for vr in validator_results
            ]
            explanation += f"Validators (name, verdict, weight, confidence): {validator_verdicts}"
        
        return Disposition(
            claim=claim,
            verdict=final_verdict,
            evidence=evidence,
            validator="arbitration_engine",
            explanation=explanation,
            validator_results=validator_results
        )
    
    def _priority_based(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Disposition:
        """
        Use configured priority order.
        
        Checks verdicts in priority order (e.g., refuted > supported > insufficient)
        and returns the first match.
        """
        for priority_verdict in self.priority:
            for vr in validator_results:
                if vr.verdict == priority_verdict:
                    explanation = vr.explanation
                    if self.explain_conflicts and len(validator_results) > 1:
                        other_verdicts = [
                            (v.validator, v.verdict) 
                            for v in validator_results if v != vr
                        ]
                        explanation += f" (Priority-based selection. Other validators: {other_verdicts})"
                    
                    return Disposition(
                        claim=claim,
                        verdict=vr.verdict,
                        evidence=evidence,
                        validator=vr.validator,
                        explanation=explanation,
                        validator_results=validator_results,
                        confidence=vr.score
                    )
        
        # Fallback
        return Disposition(
            claim=claim,
            verdict="insufficient_evidence",
            evidence=evidence,
            validator="arbitration_engine",
            explanation="No validators provided conclusive verdict",
            validator_results=validator_results
        )
    
    def _unanimous(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Disposition:
        """
        Require all validators to agree.
        
        If all validators return the same verdict, use it.
        Otherwise, return insufficient_evidence.
        """
        verdicts = [vr.verdict for vr in validator_results]
        
        if len(set(verdicts)) == 1:
            # All agree
            verdict = verdicts[0]
            explanation = f"Unanimous verdict: {verdict} from all {len(validator_results)} validators"
        else:
            # Disagreement
            verdict = "insufficient_evidence"
            verdict_counts = {v: verdicts.count(v) for v in set(verdicts)}
            explanation = f"No unanimous verdict. Counts: {verdict_counts}"
        
        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=evidence,
            validator="arbitration_engine",
            explanation=explanation,
            validator_results=validator_results
        )
    
    def _majority(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Disposition:
        """
        Use majority vote.
        
        The verdict with the most votes wins.
        Ties go to insufficient_evidence.
        """
        verdicts = [vr.verdict for vr in validator_results]
        verdict_counts = {v: verdicts.count(v) for v in set(verdicts)}
        
        # Find verdict with most votes
        max_count = max(verdict_counts.values())
        winners = [v for v, count in verdict_counts.items() if count == max_count]
        
        if len(winners) == 1:
            verdict = winners[0]
            explanation = f"Majority vote: {verdict} ({max_count}/{len(validator_results)} validators)"
        else:
            # Tie - use insufficient_evidence
            verdict = "insufficient_evidence"
            explanation = f"Tie in majority vote: {verdict_counts}"
        
        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=evidence,
            validator="arbitration_engine",
            explanation=explanation,
            validator_results=validator_results
        )
    
    def _first_wins(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Disposition:
        """
        Use first validator's result.
        
        Simple strategy that trusts the first validator in the list.
        """
        vr = validator_results[0]
        explanation = vr.explanation
        
        if self.explain_conflicts and len(validator_results) > 1:
            other_verdicts = [(v.validator, v.verdict) for v in validator_results[1:]]
            explanation += f" (First-wins strategy. Other validators: {other_verdicts})"
        
        return Disposition(
            claim=claim,
            verdict=vr.verdict,
            evidence=evidence,
            validator=vr.validator,
            explanation=explanation,
            validator_results=validator_results,
            confidence=vr.score
        )
