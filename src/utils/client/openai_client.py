"""OpenAI client module for embedding operations."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from openai import OpenAI

from src.config import OPENAI_API_KEY, OPENAI_API_BASE
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    pass

logger = setup_logger("openai_client")

EMBED_MODEL = "text-embedding-ada-002"

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    """Get singleton OpenAI client instance."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE if OPENAI_API_BASE else None,
        )
        logger.info("OpenAI client initialized")
    return _client


async def embed(text: str) -> list[float]:
    """
    Generate embedding vector for text using OpenAI API.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats (1536 dimensions for ada-002)
    """
    try:
        client = get_openai_client()
        response = await asyncio.to_thread(
            client.embeddings.create,
            model=EMBED_MODEL,
            input=text,
        )
        embedding = response.data[0].embedding
        logger.debug(f"Generated embedding for text: {text[:50]}...")
        return embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in a single API call.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    try:
        client = get_openai_client()
        response = await asyncio.to_thread(
            client.embeddings.create,
            model=EMBED_MODEL,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        logger.debug(f"Generated {len(embeddings)} embeddings in batch")
        return embeddings
    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        raise
