"""
Base class for quality analysis modules.

Quality modules analyze dispositions to detect issues like omissions,
vagueness, or contradictions between claims and evidence.
"""
from abc import ABC, abstractmethod
from typing import List
from ..types import Disposition, QualityIssue


class QualityModule(ABC):
    """
    Base class for quality analysis modules.
    
    Quality modules run after validation and arbitration to detect
    quality issues in claims, even when claims are ultimately accepted.
    
    Pipeline: Retriever → Validators → Arbitration → QualityModules → Report
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize quality module with configuration.
        
        Args:
            config: Module-specific configuration from policies.yaml
        """
        self.config = config or {}
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Module name for configuration and logging.
        
        Returns:
            Unique module identifier (e.g., "semantic_quality")
        """
        pass
    
    @abstractmethod
    def analyze(
        self,
        disposition: Disposition,
        transcript: str
    ) -> List[QualityIssue]:
        """
        Analyze a disposition for quality issues.
        
        Args:
            disposition: Validation result containing:
                - claim: The claim text
                - evidence: Retrieved evidence spans
                - verdict: Final validation verdict
                - quality_score: Validator agreement score
                - validator_results: Individual validator results
            transcript: Full source transcript for additional context
        
        Returns:
            List of detected quality issues (may be empty)
        """
        pass
    
    def should_analyze(self, disposition: Disposition) -> bool:
        """
        Determine if this disposition should be analyzed.
        
        Override this method to add custom filtering logic.
        Default: analyze all dispositions.
        
        Args:
            disposition: The disposition to check
        
        Returns:
            True if analysis should run, False to skip
        """
        return True
