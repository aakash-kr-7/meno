"""
Singleton EmbeddingService using BAAI/bge-small-en-v1.5. Loads once at startup.
normalize_embeddings=True required for cosine similarity.
"""

import logging
from sentence_transformers import SentenceTransformer
from core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def embed(self, text: str) -> list[float]:
        """Encode a single string, normalize=True, .tolist()"""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch encode a list of strings."""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]

    @property
    def embedding_dim(self) -> int:
        """Return embedding dimension from settings."""
        return settings.EMBEDDING_DIM


# Singleton instance
embedding_service = EmbeddingService()

if __name__ == "__main__":
    import sys
    # Initialize basic logging to see model load status
    logging.basicConfig(level=logging.INFO)
    val = embedding_service.embed("hello world")
    print(len(val))
