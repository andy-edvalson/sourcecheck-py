# Development Guide

## Package Overview

The `chart-checker` library verifies clinical summaries by comparing claims against source transcripts. The architecture is modular, extensible, and production-ready with multiple validators, retrievers, and quality analysis modules.

## Core Components

### 1. Main Orchestrator (`checker.py`)

The `Checker` class coordinates the entire verification pipeline:

```python
checker = Checker(
    schema_path="schemas/sayvant_hpi.yaml",
    policies_path="policies/sayvant_hpi.yaml",
    cache_retrievers=True,
    debug=False
)
report = checker.verify_summary(transcript, summary, meta)
```

**Pipeline Steps:**
1. Extract claims from summary fields (configurable extraction)
2. Retrieve evidence from transcript for each claim (cached retrievers)
3. Run configured validators on each claim (multiple validators per field)
4. Arbitrate conflicts between validators (weighted voting)
5. Run quality modules to detect drift and issues
6. Audit for missing information
7. Generate comprehensive report with quality scores

### 2. Configuration System (`config.py`)

Manages agent-specific YAML configuration pairs:

**Schema Files** (`schemas/`):
- `sayvant_hpi.yaml`: Structured field definitions (HPI, medications, dx, etc.)
- `text_output.yaml`: Free-form text field definition
- Defines field types, extraction methods, delimiters, criticality

**Policy Files** (`policies/`):
- `sayvant_hpi.yaml`: Validator mappings for structured summaries
- `text_output.yaml`: Validator mappings for free-form text
- Includes aggregation strategy, quality modules, scoring method

### 3. Type System (`types.py`)

Core data structures using Pydantic:
- `Claim`: Extracted claim with field reference and metadata
- `EvidenceSpan`: Text span from transcript with location and score
- `ValidatorResult`: Individual validator verdict with explanation
- `Disposition`: Final validation result with quality metrics
- `QualityIssue`: Detected quality problem (drift, omission, fabrication)
- `VerificationReport`: Complete report with dispositions, scores, and issues

### 4. Arbitration Engine (`arbitration.py`)

Resolves conflicts when multiple validators disagree:

**Strategies:**
- `weighted_voting`: Weighted average of validator verdicts
- `unanimous`: All validators must agree
- `majority`: Simple majority wins
- `priority`: First validator wins

**Configuration:**
```yaml
aggregation:
  strategy: "weighted_voting"
  default_weights:
    bm25_validator: 0.6
    nli_validator: 0.3
    negation_refuter: 0.8
  explain_conflicts: true
```

**Verdict Priority:**
1. `refuted` (highest - any refutation fails the claim)
2. `supported` (middle)
3. `insufficient_evidence` (lowest)

### 5. Validators (`validators/`)

**Base Class** (`base.py`):
```python
class Validator(ABC):
    @abstractmethod
    def validate(self, claim, evidence, transcript) -> Disposition:
        pass
```

**Registry** (`registry.py`):
- Decorator-based registration: `@register_validator("name")`
- Factory pattern: `create_validator("name", config)`

**Production Validators:**

| Validator | Purpose | Use Case |
|-----------|---------|----------|
| `bm25_validator` | Keyword matching with BM25 scoring | General claims, factual statements |
| `hybrid_bm25_minilm_validator` | BM25 + semantic similarity | Balanced approach |
| `nli_validator` | Natural Language Inference | Entailment checking |
| `minilm_validator` | Semantic similarity with MiniLM | Paraphrased claims |
| `negation_refuter` | Detects negated claims | "No prior surgeries" |
| `regex_validator` | Pattern matching | Structured data (codes, IDs) |
| `speaker_attribution_validator` | Validates speaker/historian | "Daughter reports..." |
| `temporal_drift_validator` | Detects temporal inconsistencies | Time-sensitive claims |
| `lexical_coverage_validator` | Measures claim coverage in evidence | Comprehensive validation |
| `context_aware_bm25_validator` | BM25 with context expansion | Terse claims needing context |

### 6. Quality Modules (`quality/`)

Post-validation analysis to detect issues even in "supported" claims:

**Base Class** (`base.py`):
```python
class QualityModule(ABC):
    @abstractmethod
    def analyze(self, disposition, transcript) -> dict:
        # Returns {"issues": [...], "quality_score": 0.8}
        pass
```

**Production Modules:**

| Module | Detects | Severity | Penalty |
|--------|---------|----------|---------|
| `temporal_numeric_drift` | Time/number mismatches | High/Medium | 50%/20% |
| `semantic_quality` | Omissions/fabrications | High/Low | 50%/10% |

**Configuration:**
```yaml
quality_modules:
  - name: temporal_numeric_drift
    tolerance_percent: 10
    check_temporal: true
    check_numeric: true
  
  - name: semantic_quality
    min_quality_score: 0.95
    analyze_insufficient: true

quality_confidence_penalty: 0.9

scoring:
  method: "quality_weighted"  # Weight claims by quality_score
```

**Quality Score:**
- `1.0` = Perfect quality (no issues)
- `0.8` = Minor issue (20% penalty)
- `0.5` = Major issue (50% penalty)
- Multiplied across all quality modules

### 7. Retrieval System (`retrieval/`)

**Base Class** (`base.py`):
```python
class Retriever(ABC):
    @abstractmethod
    def retrieve(self, claim, top_k, metadata) -> List[EvidenceSpan]:
        pass
```

**Production Retrievers:**

| Retriever | Method | Best For |
|-----------|--------|----------|
| `bm25_retriever` | BM25 keyword scoring | Factual claims with specific terms |
| `semantic_retriever` | Dense embeddings (MiniLM) | Paraphrased/semantic claims |
| `context_aware_bm25_retriever` | BM25 + context expansion | Terse claims needing context |
| `keyword_retriever` | Simple keyword matching | Fast, basic retrieval |
| `dummy_retriever` | Returns empty results | Testing only |

**Caching:**
- Retrievers are cached by transcript hash + config
- Avoids rebuilding expensive indexes (BM25, embeddings)
- Configurable cache size (default: 100)
- See `PERFORMANCE_OPTIMIZATION.md` for details

### 8. Claim Extraction (`claimextractor/`)

**Configurable Extraction** (`configurable.py`):
- YAML-driven extraction based on schema
- Supports multiple extraction methods per field type

**Extraction Methods:**
- `single_value`: Extract entire field value as one claim
- `delimited`: Split by delimiter (pipes, commas, semicolons, newlines)
- `bullet_list`: Split by bullet points or numbered lists
- `structured`: Extract from nested JSON structures
- `skip`: Don't extract claims from this field

**Example Schema:**
```yaml
fields:
  medications:
    type: list
    extraction_method: delimited
    delimiter: "|"
  
  hpi:
    type: text
    extraction_method: delimited
    delimiter: "\n"
```

### 9. Rubric System (`rubric/`)

**Auditor** (`auditor.py`):
- Detects information in transcript missing from summary
- Keyword-based detection

**Completeness** (`completeness.py`):
- Checks for required fields
- Calculates completeness score

## Adding New Validators

1. Create a new file in `checker/validators/`
2. Inherit from `Validator` base class
3. Register with decorator:

```python
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition

@register_validator("my_validator")
class MyValidator(Validator):
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.threshold = self.config.get("threshold", 0.5)
    
    @property
    def name(self) -> str:
        return "my_validator"
    
    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        # Your validation logic here
        if not evidence:
            verdict = "insufficient_evidence"
        elif self._check_claim(claim, evidence):
            verdict = "supported"
        else:
            verdict = "refuted"
        
        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=evidence,
            validator=self.name,
            explanation="Why this verdict was reached",
            validator_results=[],
            confidence=0.9
        )
    
    def _check_claim(self, claim, evidence):
        # Implementation here
        return True
```

4. Import in `validators/__init__.py`:
```python
from . import my_validator
```

5. Add to policy file:
```yaml
validators:
  field_name:
    - my_validator:
        threshold: 0.7
```

## Adding New Quality Modules

1. Create a new file in `checker/quality/`
2. Inherit from `QualityModule` base class
3. Register with decorator:

```python
from .base import QualityModule
from .registry import register_quality_module
from ..types import Disposition, QualityIssue

@register_quality_module("my_quality_module")
class MyQualityModule(QualityModule):
    @property
    def name(self) -> str:
        return "my_quality_module"
    
    def analyze(
        self,
        disposition: Disposition,
        transcript: str
    ) -> dict:
        issues = []
        
        # Detect quality issues
        if self._has_issue(disposition):
            issues.append(QualityIssue(
                type="my_issue_type",
                severity="high",
                detail="Description of the issue",
                evidence_snippet="...",
                claim_snippet="...",
                suggestion="How to fix it"
            ))
        
        # Calculate quality score
        quality_score = 1.0
        for issue in issues:
            if issue.severity == "high":
                quality_score *= 0.5
            elif issue.severity == "medium":
                quality_score *= 0.8
        
        return {
            "issues": issues,
            "quality_score": quality_score
        }
```

4. Import in `quality/__init__.py`
5. Add to policy file:
```yaml
quality_modules:
  - name: my_quality_module
    config_param: value
```

## Testing Strategy

### Unit Tests
- `test_config.py`: Configuration loading and access
- `test_validators.py`: Validator registration and execution
- `test_retrieval.py`: Retriever functionality
- `test_extraction.py`: Claim extraction
- `test_caching.py`: Retriever caching
- `test_checker.py`: End-to-end verification pipeline

### Integration Tests
- `examples/run_example.py`: Structured summary validation
- `examples/run_real_example.py`: Real clinical data

### Running Tests
```bash
source venv/bin/activate
pytest tests/ -v
```

**Note:** Some tests require user interaction due to PTY limitations. See `.clinerules` for details.

## Example Workflows

### Structured Summary Validation

```python
from checker import Checker

# Initialize with agent-specific configs
checker = Checker(
    schema_path="schemas/sayvant_hpi.yaml",
    policies_path="policies/sayvant_hpi.yaml",
    cache_retrievers=True
)

# Prepare data
transcript = "Patient reports chest pain..."
summary = {
    "chief_complaint": "Chest pain",
    "hpi": "56yo F with sudden onset chest pain",
    "medications": "Aspirin|Lisinopril",
    "dx": "Possible MI"
}

# Verify
report = checker.verify_summary(transcript, summary)

# Access results
print(f"Overall Score: {report.overall_score}")
print(f"Quality Score: {report.quality_score}")

for disp in report.dispositions:
    print(f"{disp.claim.field}: {disp.claim.text}")
    print(f"  Verdict: {disp.verdict}")
    print(f"  Quality: {disp.quality_score}")
    if disp.quality_issues:
        for issue in disp.quality_issues:
            print(f"  Issue: {issue.detail}")
```

### Free-Form Text Validation

```python
checker = Checker(
    schema_path="schemas/text_output.yaml",
    policies_path="policies/text_output.yaml"
)

# Text is treated as single "content" field
summary = {
    "content": "The patient is a 56-year-old woman who..."
}

report = checker.verify_summary(transcript, summary)
```

## CLI Usage

```bash
# Structured summary
chart-checker \
  -t transcript.txt \
  -s summary.json \
  --schema schemas/sayvant_hpi.yaml \
  --policies policies/sayvant_hpi.yaml \
  -o report.json

# Free-form text
chart-checker \
  -t transcript.txt \
  -s agent_output.txt \
  --schema schemas/text_output.yaml \
  --policies policies/text_output.yaml

# With debug output
chart-checker -t transcript.txt -s summary.json --debug
```

## Configuration Patterns

### Agent-Specific Configs

Each AI agent gets its own schema + policies pair:

```
Agent 1 (Sayvant HPI)
├── schemas/sayvant_hpi.yaml      # Structured fields
└── policies/sayvant_hpi.yaml     # Field-specific validators

Agent 2 (Text Output)
├── schemas/text_output.yaml      # Single "content" field
└── policies/text_output.yaml     # Text-focused validators
```

### Policy Structure

```yaml
version: "2.0"
retriever: semantic

validators:
  field_name:
    - validator1
    - validator2:
        param: value

aggregation:
  strategy: "weighted_voting"
  default_weights:
    validator1: 0.7
    validator2: 0.3

quality_modules:
  - name: temporal_numeric_drift
    tolerance_percent: 10
  - name: semantic_quality
    min_quality_score: 0.95

scoring:
  method: "quality_weighted"

quality_confidence_penalty: 0.9
```

## Architecture Decisions

1. **Agent-specific configs**: Each AI agent has its own schema + policies
2. **Modular design**: Easy to swap components (validators, retrievers, quality modules)
3. **Configuration-driven**: Behavior controlled by YAML files, not code
4. **Extensible validators**: Plugin-style architecture with registry
5. **Type safety**: Comprehensive Pydantic models with validation
6. **Arbitration**: Weighted voting resolves validator conflicts
7. **Quality analysis**: Post-validation drift and issue detection
8. **Performance**: Retriever caching, lazy loading of ML models

## Performance Considerations

- **Retriever caching**: Enabled by default, avoids rebuilding indexes
- **Lazy loading**: ML models loaded on first use
- **Synchronous**: Current implementation (async planned)
- **Batch processing**: Not yet implemented
- See `PERFORMANCE_OPTIMIZATION.md` for details

## Production Features

✅ **Multiple validators per field** - Arbitration resolves conflicts  
✅ **Quality analysis** - Detects drift even in "supported" claims  
✅ **Retriever caching** - Performance optimization  
✅ **Agent-specific configs** - Easy to add new AI agents  
✅ **CLI with warnings** - Quality concerns prominently displayed  
✅ **Comprehensive logging** - Debug mode available  

## Next Steps

1. **Async support** for API-based validators
2. **Batch processing** for multiple summaries
3. **Enhanced semantic_quality** with better stopword filtering
4. **Monitoring and metrics** for production deployment
5. **Additional validators** for specific medical domains
6. **LLM-based validators** for complex reasoning

## Security Notes

- Input validation needed for production use
- Sanitize transcript and summary inputs
- Validate YAML configuration files
- Consider rate limiting for API-based validators
- Audit quality module outputs for sensitive information

## Documentation

- `README.md`: Overview and quick start
- `DEVELOPMENT.md`: This file - architecture and development guide
- `CONFIGURATION_GUIDE.md`: Detailed configuration reference
- `PERFORMANCE_OPTIMIZATION.md`: Caching and performance details
- `VALIDATOR_ARBITRATION_DESIGN.md`: Arbitration system design
- `CLI_USAGE.md`: Command-line interface guide
