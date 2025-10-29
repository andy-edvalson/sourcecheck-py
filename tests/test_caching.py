"""
Tests for retriever caching functionality.
"""
import pytest
from checker import Checker


@pytest.fixture
def sample_transcript():
    """Sample transcript for testing."""
    return "Patient presents with chest pain that started 2 days ago."


@pytest.fixture
def sample_summary():
    """Sample summary for testing."""
    return {
        'chief_complaint': 'Chest pain for 2 days'
    }


def test_caching_enabled_by_default():
    """Test that caching is enabled by default."""
    checker = Checker(
        schema_path='checker/schema.yaml',
        policies_path='checker/policies.yaml'
    )
    
    assert checker.cache_retrievers is True
    assert checker.max_cache_size == 100


def test_caching_can_be_disabled():
    """Test that caching can be disabled."""
    checker = Checker(
        schema_path='checker/schema.yaml',
        policies_path='checker/policies.yaml',
        cache_retrievers=False
    )
    
    assert checker.cache_retrievers is False


def test_cache_hit_on_repeated_verification(sample_transcript, sample_summary):
    """Test that cache is hit on repeated verifications."""
    checker = Checker(
        schema_path='checker/schema.yaml',
        policies_path='checker/policies.yaml',
        cache_retrievers=True
    )
    
    # First verification - should be cache miss
    checker.verify_summary(sample_transcript, sample_summary)
    stats1 = checker.get_cache_stats()
    
    assert stats1['cache_misses'] == 1
    assert stats1['cache_hits'] == 0
    
    # Second verification with same transcript - should be cache hit
    checker.verify_summary(sample_transcript, sample_summary)
    stats2 = checker.get_cache_stats()
    
    assert stats2['cache_hits'] == 1
    assert stats2['cache_misses'] == 1


def test_cache_miss_on_different_transcript(sample_summary):
    """Test that different transcripts cause cache misses."""
    checker = Checker(
        schema_path='checker/schema.yaml',
        policies_path='checker/policies.yaml',
        cache_retrievers=True
    )
    
    transcript1 = "Patient has chest pain."
    transcript2 = "Patient has abdominal pain."
    
    # First verification
    checker.verify_summary(transcript1, sample_summary)
    
    # Second verification with different transcript
    checker.verify_summary(transcript2, sample_summary)
    
    stats = checker.get_cache_stats()
    assert stats['cache_misses'] == 2
    assert stats['cache_hits'] == 0


def test_clear_cache(sample_transcript, sample_summary):
    """Test clearing the cache."""
    checker = Checker(
        schema_path='checker/schema.yaml',
        policies_path='checker/policies.yaml',
        cache_retrievers=True
    )
    
    # Verify to populate cache
    checker.verify_summary(sample_transcript, sample_summary)
    
    stats_before = checker.get_cache_stats()
    assert stats_before['cache_size'] > 0
    
    # Clear cache
    checker.clear_cache()
    
    stats_after = checker.get_cache_stats()
    assert stats_after['cache_size'] == 0
    assert stats_after['cache_hits'] == 0
    assert stats_after['cache_misses'] == 0


def test_cache_stats_structure():
    """Test that cache stats have expected structure."""
    checker = Checker(
        schema_path='checker/schema.yaml',
        policies_path='checker/policies.yaml'
    )
    
    stats = checker.get_cache_stats()
    
    assert 'cache_size' in stats
    assert 'max_cache_size' in stats
    assert 'cache_hits' in stats
    assert 'cache_misses' in stats
    assert 'hit_rate' in stats
    
    assert isinstance(stats['cache_size'], int)
    assert isinstance(stats['max_cache_size'], int)
    assert isinstance(stats['cache_hits'], int)
    assert isinstance(stats['cache_misses'], int)
    assert isinstance(stats['hit_rate'], float)


def test_cache_hit_rate_calculation(sample_transcript, sample_summary):
    """Test that hit rate is calculated correctly."""
    checker = Checker(
        schema_path='checker/schema.yaml',
        policies_path='checker/policies.yaml',
        cache_retrievers=True
    )
    
    # First verification - miss
    checker.verify_summary(sample_transcript, sample_summary)
    
    # Second verification - hit
    checker.verify_summary(sample_transcript, sample_summary)
    
    stats = checker.get_cache_stats()
    
    # Hit rate should be 1 hit / 2 total = 0.5
    assert stats['hit_rate'] == 0.5


def test_custom_cache_size():
    """Test setting custom cache size."""
    checker = Checker(
        schema_path='checker/schema.yaml',
        policies_path='checker/policies.yaml',
        cache_retrievers=True,
        max_cache_size=50
    )
    
    assert checker.max_cache_size == 50
    
    stats = checker.get_cache_stats()
    assert stats['max_cache_size'] == 50
