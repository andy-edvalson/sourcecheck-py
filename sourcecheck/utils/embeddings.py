"""
Embedding service for semantic similarity using sentence transformers.
"""
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingService:
    """
    Singleton service for generating text embeddings.
    
    Uses sentence-transformers with MiniLM model for fast CPU inference.
    No caching for POC - can be added later if needed.
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern - only one instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name of sentence-transformers model to use
                       Default: 'all-MiniLM-L6-v2' (fast, good quality)
        """
        if self._model is None:
            print(f"Loading embedding model: {model_name}")
            self._model = SentenceTransformer(model_name)
            print("Model loaded successfully")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get normalized embedding vector for text.
        
        Args:
            text: Input text to embed
        
        Returns:
            Normalized embedding vector (unit length)
        """
        # Get embedding from model
        embedding = self._model.encode(text, convert_to_numpy=True)
        
        # Normalize to unit vector for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        
        For normalized vectors, this is simply the dot product.
        
        Args:
            vec1: First embedding vector (normalized)
            vec2: Second embedding vector (normalized)
        
        Returns:
            Cosine similarity score between -1 and 1
        """
        return float(np.dot(vec1, vec2))
