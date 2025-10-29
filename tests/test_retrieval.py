"""
Tests for evidence retrieval functionality.
"""
import pytest
from checker.retrieval import create_retriever
from checker.retrieval.bm25_retriever import BM25Retriever
from checker.retrieval.semantic_retriever import SemanticRetriever


@pytest.fixture
def sample_transcript():
    """Sample transcript for testing."""
    return """
    Patient presents with chest pain that started 2 days ago.
    The pain is described as sharp and radiating to the left arm.
    Patient has a history of hypertension and takes Lisinopril 10mg daily.
    No known drug allergies reported.
    Vital signs are stable with BP 140/90.
    """


def test_create_bm25_retriever(sample_transcript):
    """Test creating BM25 retriever."""
    retriever = create_retriever(
        name='bm25',
        transcript=sample_transcript
    )
    
    assert isinstance(retriever, BM25Retriever)
    assert retriever.transcript == sample_transcript


def test_bm25_retrieval(sample_transcript):
    """Test BM25 evidence retrieval."""
    retriever = create_retriever(
        name='bm25',
        transcript=sample_transcript
    )
    
    # Search for chest pain
    evidence = retriever.retrieve(claim='chest pain', top_k=3)
    
    assert len(evidence) > 0
    assert any('chest pain' in e.text.lower() for e in evidence)
    assert all(e.score > 0 for e in evidence)


def test_bm25_retrieval_no_match(sample_transcript):
    """Test BM25 retrieval with no matches."""
    retriever = create_retriever(
        name='bm25',
        transcript=sample_transcript
    )
    
    # Search for something not in transcript
    evidence = retriever.retrieve(claim='diabetes mellitus', top_k=3)
    
    # Should return empty or low-scoring results
    assert len(evidence) == 0 or all(e.score < 0.1 for e in evidence)


def test_bm25_retrieval_top_k(sample_transcript):
    """Test BM25 retrieval respects top_k parameter."""
    retriever = create_retriever(
        name='bm25',
        transcript=sample_transcript
    )
    
    evidence = retriever.retrieve(claim='patient', top_k=2)
    
    assert len(evidence) <= 2


def test_retriever_config(sample_transcript):
    """Test retriever with custom configuration."""
    config = {
        'context_window': 100,
        'min_score': 0.5
    }
    
    retriever = create_retriever(
        name='bm25',
        transcript=sample_transcript,
        config=config
    )
    
    assert retriever.config == config


def test_keyword_retriever(sample_transcript):
    """Test keyword retriever."""
    retriever = create_retriever(
        name='keyword',
        transcript=sample_transcript
    )
    
    evidence = retriever.retrieve(claim='chest pain', top_k=3)
    
    assert len(evidence) > 0
    assert any('chest pain' in e.text.lower() for e in evidence)


def test_context_aware_retrieval(sample_transcript):
    """Test context-aware BM25 retrieval."""
    retriever = create_retriever(
        name='context_aware_bm25',
        transcript=sample_transcript
    )
    
    # Provide metadata with summary context
    metadata = {
        'summary': {
            'chief_complaint': 'Chest pain',
            'medications': 'Lisinopril'
        }
    }
    
    evidence = retriever.retrieve(
        claim='chest pain',
        top_k=3,
        metadata=metadata
    )
    
    assert len(evidence) > 0


def test_evidence_span_properties(sample_transcript):
    """Test evidence span has required properties."""
    retriever = create_retriever(
        name='bm25',
        transcript=sample_transcript
    )
    
    evidence = retriever.retrieve(claim='chest pain', top_k=1)
    
    if evidence:
        span = evidence[0]
        assert hasattr(span, 'text')
        assert hasattr(span, 'score')
        assert hasattr(span, 'start')
        assert hasattr(span, 'end')
        assert isinstance(span.text, str)
        assert isinstance(span.score, (int, float))
