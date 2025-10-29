"""
Validators package for claim verification.
"""
from .base import Validator
from .registry import (
    register_validator,
    get_validator,
    create_validator,
    list_validators
)

# Import validators to trigger registration
from . import always_true
from . import bm25_validator
from . import context_aware_bm25_validator
from . import minilm_validator
from . import hybrid_bm25_minilm_validator
from . import regex_validator
from . import speaker_attribution_validator
from . import nli_validator
from . import negation_refuter

__all__ = [
    'Validator',
    'register_validator',
    'get_validator',
    'create_validator',
    'list_validators',
]
