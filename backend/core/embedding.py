"""Embedding provider contract.

Defines the interface that all embedding implementations must satisfy.
Processor receives an EmbeddingProvider via constructor (dependency
injection) and does not care which implementation is wired in.
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base for all embedding strategies.

    Implementations:
      - GeminiEmbeddingProvider  → cloud API, 3072-dim
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors, one per input string.
        """
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text.

        Args:
            text: A single string (typically a user query).

        Returns:
            A single embedding vector.
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors.

        Used by downstream consumers (e.g. vector store) to initialise
        collection schemas.
        """
        ...
