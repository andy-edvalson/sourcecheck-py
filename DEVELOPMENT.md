# Development Guide

## Package Overview

The `chart-checker` library is designed to verify clinical summaries by comparing claims against source transcripts. The architecture is modular and extensible.

## Core Components

### 1. Main Orchestrator (`checker.py`)

The `Checker` class coordinates the entire verification pipeline:

```python
checker = Checker(schema_path="...", policies_path="...")
report = checker.verify_summary(transcript, summary, meta)
```

**Pipeline Steps:**
1. Extract claims from summary fields
2. Retrieve evidence from transcript for each claim
3. Run configured validators on each claim
4. Audit for missing information
5. Generate comprehensive report

### 2. Configuration System (`config.py`)

Manages two YAML configuration files:

- **schema.yaml**: Defines summary field structure, types, required fields, and criticality levels
- **policies.yaml**: Maps validators to fields and sets global validation settings

### 3. Type System (`types.py`)

Core data structures:
- `Claim`: Extracted claim with field reference
- `EvidenceSpan`: Text span from transcript with location and score
- `Disposition`: Validation result for a claim (supported/refuted/insufficient_evidence)
- `Report`: Complete verification report with all dispositions and scores

### 4. Validators (`validators/`)

**Base Class** (`base.py`):
```python
class Validator(ABC):
    @abstractmethod
    def validate(self, claim, evidence, transcript) -> Disposition:
        pass
```

**Registry** (`registry.py`):
- Decorator-based registration: `@register_validator("name")`
- Factory pattern: `create_validator("name")`

**Current Validators**:
- `always_true`: Placeholder that always returns "supported"

### 5. Retrieval System (`retrieval/`)

**Current Implementation** (`retriever.py`):
- Keyword-based evidence retrieval
- Extracts context windows around keyword matches
- Scores evidence by keyword density

**Future Enhancement** (`embedding_stub.py`):
- Dense retrieval with embeddings
- Semantic similarity matching

### 6. Claim Extraction (`claimextractor/`)

**Current Implementation** (`stub.py`):
- Simple sentence-based splitting
- One claim per sentence

**Future Enhancement**:
- Integration with Claimify
- Sophisticated claim decomposition

### 7. Rubric System (`rubric/`)

**Auditor** (`auditor.py`):
- Detects information in transcript missing from summary
- Keyword-based detection (stub)

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
    @property
    def name(self) -> str:
        return "my_validator"
    
    def validate(self, claim, evidence, transcript) -> Disposition:
        # Your validation logic here
        verdict = "supported"  # or "refuted" or "insufficient_evidence"
        
        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=evidence,
            validator=self.name,
            explanation="Why this verdict was reached"
        )
```

4. Import in `validators/__init__.py`:
```python
from . import my_validator
```

5. Add to `policies.yaml`:
```yaml
validators:
  chief_complaint:
    - my_validator
```

## Testing Strategy

### Unit Tests
- `test_config.py`: Configuration loading and access
- `test_validators.py`: Validator registration and execution
- `test_checker.py`: End-to-end verification pipeline

### Integration Tests
- `examples/run_example.py`: Full workflow with fake clinical data

### Running Tests
```bash
source venv/bin/activate
pytest tests/ -v
```

## Example Workflow

```python
from checker import Checker

# Initialize
checker = Checker(
    schema_path="checker/schema.yaml",
    policies_path="checker/policies.yaml"
)

# Prepare data
transcript = "Patient reports chest pain..."
summary = {
    "chief_complaint": "Chest pain",
    "assessment": "Possible MI"
}

# Verify
report = checker.verify_summary(transcript, summary)

# Access results
print(f"Score: {report.overall_score}")
for disp in report.dispositions:
    print(f"{disp.claim.text}: {disp.verdict}")
```

## Next Steps for Production

1. **Replace `always_true` validator** with real validation logic:
   - Evidence-based validation
   - LLM-based verification
   - Medical knowledge base integration

2. **Enhance claim extraction**:
   - Integrate Claimify
   - Handle complex medical statements
   - Extract structured entities

3. **Improve retrieval**:
   - Implement dense retrieval with embeddings
   - Add semantic search
   - Optimize for medical terminology

4. **Add more validators**:
   - Temporal consistency checker
   - Medication dosage validator
   - Diagnosis code validator

5. **Production features**:
   - Logging and monitoring
   - Async support for API calls
   - Batch processing
   - Caching for repeated validations

## Configuration Customization

### Adding New Fields

Edit `schema.yaml`:
```yaml
fields:
  new_field:
    type: string
    required: false
    criticality: medium
    description: "Description of the field"
```

### Configuring Validators

Edit `policies.yaml`:
```yaml
validators:
  new_field:
    - validator1
    - validator2

settings:
  fail_fast: false
  max_evidence_spans: 5
```

## Architecture Decisions

1. **No external dependencies**: Only stdlib + PyYAML for core functionality
2. **Modular design**: Easy to swap components (e.g., claim extractor, retriever)
3. **Configuration-driven**: Behavior controlled by YAML files, not code
4. **Extensible validators**: Plugin-style architecture with registry
5. **Type safety**: Comprehensive dataclasses with type hints

## Performance Considerations

- Current implementation is synchronous
- Evidence retrieval is O(n) keyword search
- Consider async/await for future API integrations
- Batch processing not yet implemented
- No caching of evidence retrieval results

## Security Notes

- Input validation needed for production use
- Sanitize transcript and summary inputs
- Validate YAML configuration files
- Consider rate limiting for API-based validators
