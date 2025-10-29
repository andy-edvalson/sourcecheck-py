# Validator Arbitration & Configuration Enhancement

## Overview

Enhance the validator system to support sophisticated arbitration logic, weighted voting, and conflict resolution - all driven by YAML configuration without hardcoded domain logic.

## Current State

**Limitations:**
- Hardcoded verdict priority in `checker.py` (refuted > supported > insufficient)
- No arbitration between conflicting validators
- Limited per-validator configuration
- No weighted voting or confidence-based aggregation

**Example Current Behavior:**
```python
# In checker.py - hardcoded priority
if vr.verdict == "refuted":
    final_verdict = "refuted"
    break  # Refuted always wins
```

## Proposed Architecture

### 1. Enhanced Policy Schema

```yaml
version: "2.0"
description: "Advanced validation policies with arbitration"

# Global settings
retriever: "semantic"
threshold: 0.3

# Per-field validator configuration
validators:
  content:
    - nli_validator:
        support_threshold: 0.50
        refute_threshold: 0.96
        weight: 0.4
        arbitration:
          on_conflict: "prefer_support"   # Options: prefer_support, prefer_refute, neutral, weighted
          min_overlap: 0.60               # Lexical overlap required to override refute
          confidence_boost: 0.1           # Boost confidence if overlap is high
    
    - hybrid_bm25_minilm_validator:
        min_score: 0.30
        weight: 0.6
        arbitration:
          on_conflict: "neutral"

# Global aggregation strategy
aggregation:
  strategy: "weighted_voting"           # Options: weighted_voting, unanimous, majority, first_wins
  default_weights:
    nli_validator: 0.4
    hybrid_bm25_minilm_validator: 0.6
  verdict_priority: ["refuted", "supported", "insufficient"]  # Configurable priority
  explain_conflicts: true               # Include conflict explanation in report
  min_confidence: 0.3                   # Minimum confidence to accept verdict
  
  # Conflict resolution rules
  conflict_resolution:
    - condition: "nli_refuted_and_hybrid_supported"
      action: "check_lexical_overlap"
      threshold: 0.60
      result_if_above: "supported"
      result_if_below: "refuted"
    
    - condition: "low_confidence_refute"
      threshold: 0.85
      action: "downgrade_to_insufficient"
```

### 2. Validator Base Class Enhancement

```python
# checker/validators/base.py

class Validator:
    """Base validator with config-driven behavior."""
    
    def __init__(self, config: dict = None, debug: bool = False):
        self.config = config or {}
        self.debug = debug
        self.weight = self.config.get("weight", 1.0)
        self.arbitration_rules = self.config.get("arbitration", {})
    
    def validate(self, claim, evidence, transcript) -> Disposition:
        """
        Validate claim using config-driven thresholds.
        Subclasses implement _run_validation() for domain logic.
        """
        # Get thresholds from config
        support_threshold = self.config.get("support_threshold", 0.5)
        refute_threshold = self.config.get("refute_threshold", 0.9)
        
        # Run domain-specific validation
        verdict, confidence, explanation = self._run_validation(claim, evidence, transcript)
        
        # Apply thresholds (config-driven)
        if verdict == "contradiction" and confidence >= refute_threshold:
            final_verdict = "refuted"
        elif verdict == "entailment" and confidence >= support_threshold:
            final_verdict = "supported"
        else:
            final_verdict = "insufficient_evidence"
        
        return Disposition(
            claim=claim,
            verdict=final_verdict,
            evidence=evidence,
            validator=self.name,
            explanation=explanation,
            confidence=confidence
        )
    
    @abstractmethod
    def _run_validation(self, claim, evidence, transcript) -> Tuple[str, float, str]:
        """
        Domain-specific validation logic.
        Returns: (raw_verdict, confidence, explanation)
        """
        pass
```

### 3. Arbitration Engine

```python
# checker/arbitration.py

class ArbitrationEngine:
    """
    Resolves conflicts between validators using config-driven rules.
    """
    
    def __init__(self, config: dict):
        self.strategy = config.get("strategy", "weighted_voting")
        self.weights = config.get("default_weights", {})
        self.priority = config.get("verdict_priority", ["refuted", "supported", "insufficient_evidence"])
        self.conflict_rules = config.get("conflict_resolution", [])
        self.explain_conflicts = config.get("explain_conflicts", True)
    
    def arbitrate(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Disposition:
        """
        Arbitrate between multiple validator results.
        """
        if len(validator_results) == 1:
            return self._single_validator_result(validator_results[0], claim, evidence)
        
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
            return self._weighted_voting(claim, validator_results, evidence)
        elif self.strategy == "unanimous":
            return self._unanimous(claim, validator_results, evidence)
        elif self.strategy == "majority":
            return self._majority(claim, validator_results, evidence)
        elif self.strategy == "first_wins":
            return self._first_wins(claim, validator_results, evidence)
        else:
            # Default: priority-based
            return self._priority_based(claim, validator_results, evidence)
    
    def _apply_conflict_rules(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Optional[Disposition]:
        """Apply config-driven conflict resolution rules."""
        for rule in self.conflict_rules:
            condition = rule.get("condition")
            
            # Check if condition matches
            if condition == "nli_refuted_and_hybrid_supported":
                nli_refuted = any(vr.validator == "nli_validator" and vr.verdict == "refuted" 
                                 for vr in validator_results)
                hybrid_supported = any(vr.validator == "hybrid_bm25_minilm_validator" and vr.verdict == "supported"
                                      for vr in validator_results)
                
                if nli_refuted and hybrid_supported:
                    # Check lexical overlap
                    if evidence:
                        overlap = self._lexical_overlap(claim.text, evidence[0].text)
                        threshold = rule.get("threshold", 0.6)
                        
                        if overlap >= threshold:
                            verdict = rule.get("result_if_above", "supported")
                            explanation = f"Conflict resolved: High lexical overlap ({overlap:.2f}) overrides NLI refutation"
                        else:
                            verdict = rule.get("result_if_below", "refuted")
                            explanation = f"Conflict resolved: Low lexical overlap ({overlap:.2f}) confirms NLI refutation"
                        
                        return Disposition(
                            claim=claim,
                            verdict=verdict,
                            evidence=evidence,
                            validator="arbitration_engine",
                            explanation=explanation,
                            validator_results=validator_results
                        )
        
        return None
    
    def _lexical_overlap(self, text1: str, text2: str) -> float:
        """Calculate lexical overlap between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _weighted_voting(
        self,
        claim: Claim,
        validator_results: List[ValidatorResult],
        evidence: List[EvidenceSpan]
    ) -> Disposition:
        """Aggregate using weighted voting."""
        verdict_scores = {"supported": 0.0, "refuted": 0.0, "insufficient_evidence": 0.0}
        
        for vr in validator_results:
            weight = self.weights.get(vr.validator, 1.0)
            verdict_scores[vr.verdict] += weight
        
        # Get verdict with highest score
        final_verdict = max(verdict_scores, key=verdict_scores.get)
        
        # Build explanation
        explanation = f"Weighted voting: {verdict_scores}. "
        if self.explain_conflicts:
            explanation += f"Validators: {[(vr.validator, vr.verdict) for vr in validator_results]}"
        
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
        """Use configured priority order."""
        for priority_verdict in self.priority:
            for vr in validator_results:
                if vr.verdict == priority_verdict:
                    return Disposition(
                        claim=claim,
                        verdict=vr.verdict,
                        evidence=evidence,
                        validator=vr.validator,
                        explanation=vr.explanation,
                        validator_results=validator_results
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
```

### 4. Updated Checker Integration

```python
# checker/checker.py

class Checker:
    def __init__(self, schema_path, policies_path, ...):
        # ... existing init ...
        
        # Load arbitration config
        aggregation_config = self.config.get_policy("aggregation", {})
        self.arbitration_engine = ArbitrationEngine(aggregation_config)
    
    def verify_summary(self, transcript, summary, meta=None):
        # ... existing code ...
        
        for claim in claims:
            # Retrieve evidence
            evidence = retriever.retrieve(claim.text, ...)
            
            # Run all validators
            validator_results = []
            for validator_config in validator_configs:
                validator = create_validator(...)
                disposition = validator.validate(claim, evidence, transcript)
                validator_results.append(ValidatorResult(
                    validator=validator.name,
                    verdict=disposition.verdict,
                    explanation=disposition.explanation,
                    score=disposition.confidence
                ))
            
            # Arbitrate between validators
            final_disposition = self.arbitration_engine.arbitrate(
                claim=claim,
                validator_results=validator_results,
                evidence=evidence
            )
            
            dispositions.append(final_disposition)
        
        # ... rest of method ...
```

## Benefits

### 1. **Configuration-Driven**
- No hardcoded logic in validators
- Easy to tune without code changes
- Domain-agnostic validators

### 2. **Flexible Arbitration**
- Weighted voting
- Conflict resolution rules
- Lexical overlap checks
- Confidence-based decisions

### 3. **Transparent**
- Explain conflicts in reports
- Show all validator results
- Clear arbitration reasoning

### 4. **Extensible**
- Add new arbitration strategies via config
- Custom conflict resolution rules
- Per-field overrides

## Implementation Plan

### Phase 1: Core Infrastructure
1. Create `ArbitrationEngine` class
2. Update `Validator` base class with config-driven thresholds
3. Add arbitration config to policies schema

### Phase 2: Conflict Resolution
1. Implement lexical overlap calculator
2. Add conflict resolution rules
3. Implement weighted voting

### Phase 3: Advanced Features
1. Add unanimous/majority strategies
2. Implement confidence boosting
3. Add conflict explanation to reports

### Phase 4: Testing & Documentation
1. Unit tests for arbitration engine
2. Integration tests with real data
3. Update documentation with examples

## Example Usage

```yaml
# policies/advanced_text_validation.yaml
version: "2.0"

validators:
  content:
    - nli_validator:
        support_threshold: 0.50
        refute_threshold: 0.96
        weight: 0.4
    - hybrid_bm25_minilm_validator:
        weight: 0.6

aggregation:
  strategy: "weighted_voting"
  default_weights:
    nli_validator: 0.4
    hybrid_bm25_minilm_validator: 0.6
  
  conflict_resolution:
    - condition: "nli_refuted_and_hybrid_supported"
      action: "check_lexical_overlap"
      threshold: 0.60
      result_if_above: "supported"
      result_if_below: "refuted"
```

## Migration Path

1. Keep existing hardcoded logic as default
2. Add arbitration engine as opt-in feature
3. Gradually migrate validators to config-driven approach
4. Deprecate hardcoded logic in future version

## Open Questions

1. Should we support custom Python arbitration functions?
2. How to handle validator errors in arbitration?
3. Should confidence scores be normalized before weighted voting?
4. How to version arbitration strategies?

## Related Work

- Ensemble methods in ML (voting, stacking)
- Multi-agent systems (conflict resolution)
- Expert systems (rule-based reasoning)
