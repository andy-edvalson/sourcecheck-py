"""
Retrieval package for evidence extraction from transcripts.
"""
from .base import Retriever
from .registry import (
    register_retriever,
    get_retriever,
    create_retriever,
    list_retrievers
)
from .keyword_retriever import KeywordRetriever
from .dummy_retriever import DummyRetriever
from .bm25_retriever import BM25Retriever
from .context_aware_bm25_retriever import ContextAwareBM25Retriever
from .semantic_retriever import SemanticRetriever

__all__ = [
    'Retriever',
    'register_retriever',
    'get_retriever',
    'create_retriever',
    'list_retrievers',
    'KeywordRetriever',
    'DummyRetriever',
    'BM25Retriever',
    'ContextAwareBM25Retriever',
]
