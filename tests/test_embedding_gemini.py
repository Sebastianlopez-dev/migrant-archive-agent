"""Tests for Gemini embedding provider.

Uses mocks for the google-genai client so no real API calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.core.embedding_gemini import GeminiEmbeddingProvider


class TestGeminiEmbeddingProvider:
    """RED → GREEN → REFACTOR for Gemini embedding provider."""

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("backend.core.embedding_gemini.genai")
    def test_embed_batch(self, mock_genai):
        """RED: embed() should return vectors for each input text."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # gemini-embedding-2 requires one call per text.
        # side_effect returns one embedding per call.
        def embed_side_effect(model, contents, **kwargs):
            m = MagicMock()
            if contents == "hello":
                m.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
            else:
                m.embeddings = [MagicMock(values=[0.4, 0.5, 0.6])]
            return m

        mock_client.models.embed_content.side_effect = embed_side_effect

        provider = GeminiEmbeddingProvider()
        result = provider.embed(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]

        # Two calls — one per text with gemini-embedding-2
        assert mock_client.models.embed_content.call_count == 2
        first_call = mock_client.models.embed_content.call_args_list[0]
        assert first_call.kwargs["model"] == "models/gemini-embedding-2"
        assert first_call.kwargs["contents"] == "hello"

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("backend.core.embedding_gemini.genai")
    def test_embed_query(self, mock_genai):
        """RED: embed_query() should return a single vector."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.embeddings = [MagicMock(values=[0.7, 0.8, 0.9])]
        mock_client.models.embed_content.return_value = mock_response

        provider = GeminiEmbeddingProvider()
        result = provider.embed_query("hello")

        assert result == [0.7, 0.8, 0.9]

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_dimension_is_3072(self):
        """RED: dimension should be 3072 (Gemini Matryoshka)."""
        # We can test dimension without mocking the client
        with patch("backend.core.embedding_gemini.genai"):
            provider = GeminiEmbeddingProvider()
            assert provider.dimension == 3072

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("backend.core.embedding_gemini.genai")
    def test_missing_api_key_raises(self, mock_genai):
        """RED: Missing GEMINI_API_KEY should raise ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                GeminiEmbeddingProvider()

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("backend.core.embedding_gemini.genai")
    def test_embed_empty_list(self, mock_genai):
        """RED: embed([]) should return [] without calling API."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        provider = GeminiEmbeddingProvider()
        result = provider.embed([])

        assert result == []
        mock_client.models.embed_content.assert_not_called()
