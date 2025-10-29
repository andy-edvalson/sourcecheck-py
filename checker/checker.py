"""
Main orchestrator for summary verification.
"""
from typing import Dict, Any, Optional, List
from pathlib import Path

from .config import Config
from .types import VerificationReport, Disposition, Claim, ValidatorResult
from .claimextractor import extract_claims_configurable
from .retrieval import create_retriever
from .validators import create_validator
from .rubric import detect_missing_claims, calculate_completeness_score
from .arbitration import ArbitrationEngine


class Checker:
    """
    Main orchestrator for verifying clinical summaries.
    
    The Checker coordinates the entire verification pipeline:
    1. Extract claims from summary fields
    2. Retrieve evidence from transcript for each claim
    3. Run configured validators on each claim
    4. Audit for missing information
    5. Generate comprehensive report
    """
    
    def __init__(
        self,
        schema_path: str = "checker/schema.yaml",
        policies_path: str = "checker/policies.yaml",
        cache_retrievers: bool = True,
        max_cache_size: int = 100,
        debug: bool = False
    ):
        """
        Initialize the Checker with configuration files.
        
        Args:
            schema_path: Path to schema.yaml
            policies_path: Path to policies.yaml
            cache_retrievers: Whether to cache retriever instances (default: True)
            max_cache_size: Maximum number of retrievers to cache (default: 100)
            debug: Enable debug output (default: False)
        """
        self.config = Config(schema_path, policies_path)
        self.cache_retrievers = cache_retrievers
        self.max_cache_size = max_cache_size
        self.debug = debug
        self._retriever_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Initialize arbitration engine
        aggregation_config = self.config.get_policy("aggregation", {})
        self.arbitration_engine = ArbitrationEngine(aggregation_config)
    
    def verify_summary(
        self,
        transcript: str,
        summary: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None
    ) -> VerificationReport:
        """
        Verify a structured document against source material.
        
        Args:
            transcript: Full source material text
            summary: Structured document dictionary with field values
            meta: Optional metadata
        
        Returns:
            VerificationReport with verification results
        """
        # Extract claims from summary
        claims = extract_claims_configurable(
            summary=summary,
            schema=self.config.schema,
            meta=meta,
            debug=self.debug
        )
        
        # Add summary to each claim's metadata for context-aware validation
        for claim in claims:
            if not claim.metadata:
                claim.metadata = {}
            claim.metadata['summary'] = summary
        
        # Get or create retriever for this transcript
        retriever_name = self.config.get_policy('retriever', 'bm25')
        retriever_config = self.config.get_policy('retriever_config', {})
        
        retriever = self._get_or_create_retriever(
            transcript=transcript,
            retriever_name=retriever_name,
            retriever_config=retriever_config
        )
        
        # Process each claim
        dispositions: List[Disposition] = []
        
        for claim in claims:
            # Retrieve evidence for this claim using configured retriever
            # Pass claim metadata for context-aware retrieval
            evidence = retriever.retrieve(
                claim=claim.text,
                top_k=self.config.get_setting('max_evidence_spans', 5),
                metadata=claim.metadata
            )
            
            # Get validators for this field
            validator_configs = self.config.get_validators_for_field(claim.field)
            
            # Collect results from ALL validators
            validator_results: List[ValidatorResult] = []
            
            for validator_config in validator_configs:
                try:
                    # Parse validator name and config
                    if isinstance(validator_config, dict):
                        # Format: {validator_name: {config}}
                        validator_name = list(validator_config.keys())[0]
                        config = validator_config[validator_name]
                    else:
                        # Format: validator_name (string)
                        validator_name = validator_config
                        config = None
                    
                    validator = create_validator(validator_name, config, debug=self.debug)
                    disposition = validator.validate(
                        claim=claim,
                        evidence=evidence,
                        transcript=transcript
                    )
                    
                    # Collect this validator's result
                    validator_results.append(ValidatorResult(
                        validator=validator_name,
                        verdict=disposition.verdict,
                        explanation=disposition.explanation,
                        score=None  # Could extract from explanation if needed
                    ))
                            
                except Exception as e:
                    # Log error and continue
                    if self.debug:
                        print(f"DEBUG: Error running validator {validator_name}: {e}")
                    validator_results.append(ValidatorResult(
                        validator=validator_name,
                        verdict="insufficient_evidence",
                        explanation=f"Validator error: {str(e)}",
                        score=None
                    ))
            
            # Use arbitration engine to resolve conflicts between validators
            if validator_results:
                final_disposition = self.arbitration_engine.arbitrate(
                    claim=claim,
                    validator_results=validator_results,
                    evidence=evidence
                )
                dispositions.append(final_disposition)
        
        # Audit for missing claims
        missing_claims = detect_missing_claims(
            transcript=transcript,
            summary=summary,
            schema=self.config.schema
        )
        
        # Calculate overall score (pass/fail)
        overall_score = self._calculate_overall_score(
            dispositions=dispositions,
            summary=summary
        )
        
        # Calculate quality score (validator agreement)
        quality_score = self._calculate_quality_score(dispositions)
        
        # Build report
        report = VerificationReport(
            dispositions=dispositions,
            source_fields=summary,
            overall_score=overall_score,
            quality_score=quality_score,
            missing_claims=missing_claims,
            issues=[],  # Will be populated by rubric/auditor
            metadata=meta
        )
        
        return report
    
    def _calculate_overall_score(
        self,
        dispositions: List[Disposition],
        summary: Dict[str, Any]
    ) -> float:
        """
        Calculate overall verification score (pass/fail).
        
        Args:
            dispositions: List of claim dispositions
            summary: Summary dictionary
        
        Returns:
            Score between 0.0 and 1.0
        """
        if not dispositions:
            return 0.0
        
        # Count supported vs total claims
        supported_count = sum(
            1 for d in dispositions
            if d.verdict == "supported"
        )
        
        # Base score on claim support rate
        claim_score = supported_count / len(dispositions)
        
        # Factor in completeness
        completeness_score = calculate_completeness_score(
            summary=summary,
            schema=self.config.schema
        )
        
        # Weighted average (70% claims, 30% completeness)
        overall = (0.7 * claim_score) + (0.3 * completeness_score)
        
        return round(overall, 3)
    
    def _calculate_quality_score(self, dispositions: List[Disposition]) -> float:
        """
        Calculate overall quality score based on validator agreement.
        
        Quality score reflects how confident we are in the results:
        - 1.0: All validators agreed on all claims
        - 0.5-0.9: Some disagreement but generally consistent
        - 0.0-0.5: Significant disagreement across validators
        
        Args:
            dispositions: List of claim dispositions with quality scores
        
        Returns:
            Average quality score between 0.0 and 1.0
        """
        if not dispositions:
            return 1.0
        
        # Calculate average quality score across all dispositions
        quality_scores = [
            d.quality_score for d in dispositions
            if d.quality_score is not None
        ]
        
        if not quality_scores:
            # No quality scores available (single validator per claim)
            return 1.0
        
        avg_quality = sum(quality_scores) / len(quality_scores)
        return round(avg_quality, 3)
    
    def _get_or_create_retriever(
        self,
        transcript: str,
        retriever_name: str,
        retriever_config: dict
    ):
        """
        Get cached retriever or create new one.
        
        Caches retrievers by (transcript_hash, retriever_name, config) to avoid
        rebuilding expensive indexes (e.g., BM25) on repeated validations.
        
        Args:
            transcript: Full transcript text
            retriever_name: Name of retriever to use
            retriever_config: Retriever configuration dict
        
        Returns:
            Retriever instance (cached or newly created)
        """
        if not self.cache_retrievers:
            # Caching disabled, always create new retriever
            return create_retriever(
                name=retriever_name,
                transcript=transcript,
                config=retriever_config
            )
        
        # Create cache key from transcript hash + retriever config
        transcript_hash = hash(transcript)
        config_key = str(sorted(retriever_config.items())) if retriever_config else ""
        cache_key = (transcript_hash, retriever_name, config_key)
        
        # Check cache
        if cache_key in self._retriever_cache:
            self._cache_hits += 1
            return self._retriever_cache[cache_key]
        
        # Cache miss - create new retriever
        self._cache_misses += 1
        retriever = create_retriever(
            name=retriever_name,
            transcript=transcript,
            config=retriever_config
        )
        
        # Add to cache (with size limit)
        if len(self._retriever_cache) >= self.max_cache_size:
            # Simple FIFO eviction - remove oldest entry
            oldest_key = next(iter(self._retriever_cache))
            del self._retriever_cache[oldest_key]
        
        self._retriever_cache[cache_key] = retriever
        return retriever
    
    def clear_cache(self):
        """Clear the retriever cache and reset statistics."""
        self._retriever_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_cache_stats(self) -> dict:
        """
        Get cache performance statistics.
        
        Returns:
            Dict with cache_size, hits, misses, and hit_rate
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'cache_size': len(self._retriever_cache),
            'max_cache_size': self.max_cache_size,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': round(hit_rate, 3)
        }
