## Policy Schema Overview

Each `policies.yaml` includes:
- `version`: schema version (string)
- `retriever`: retrieval engine type (e.g., `semantic`, `bm25`, `context_aware_bm25`)
- `retriever_config`: chunking/overlap, context window, and optional field relationships for context expansion
- `validators`: mapping of summary field → ordered list of validator specs
- `settings`: global thresholds and limits (e.g., `min_evidence_score`, `max_evidence_spans`, `context_boost`, `embedding_threshold`)

Validator spec forms:
- String: `validator_name`
- Object: `{ validator_name: { config } }`

Examples:
```yaml
version: "1.0"
retriever: semantic
retriever_config:
  chunk_size: 200
  overlap: 50
  context_window: 150
validators:
  chief_complaint:
    - hybrid_bm25_minilm_validator
  psh:
    - negation_refuter:
        match_threshold: 0.6
        semantic_threshold: 0.6
    - clinical_nli_validator
settings:
  min_evidence_score: 0.3
  max_evidence_spans: 5
```

Refer to `checker/config.py` for required keys and access helpers.
