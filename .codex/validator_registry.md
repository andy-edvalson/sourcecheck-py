# Validator Registry (Summary)
| Name | Purpose | Inputs | Typical Fields |
|------|---------|--------|----------------|
| `bm25_validator` | Lexical evidence match | claim, evidence | hpi, dx, medications, treatments |
| `context_aware_bm25_validator` | Lexical with context expansion | claim, evidence + context | hpi, dx |
| `hybrid_bm25_minilm_validator` | Hybrid lexical + semantic scoring | claim, evidence | chief_complaint, pmh, mode_of_transport |
| `minilm_validator` | Semantic similarity via MiniLM | claim, evidence embeddings | social, code_status, pmh |
| `clinical_nli_validator` | NLI-based support/refute | claim/text pairs | psh, assessment, dx |
| `negation_refuter` | Detects contradictions due to negation | claim, transcript | psh |
| `regex_validator` | Direct regex extraction | claim.text | identifiers, dispo, pt_family_discussion |
| `speaker_attribution_validator` | Historian/speaker consistency | transcript metadata | historians |

See implementations under `checker/validators/` and configuration examples in `checker/policies.yaml`.
