"""OpenAI client module for embedding operations."""

from __future__ import annotations

from openai import AsyncOpenAI, RateLimitError, APIError
from openai.types.chat import ChatCompletionUserMessageParam, ChatCompletionSystemMessageParam
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import OPENAI_API_KEY, OPENAI_API_BASE, EMBED_MODEL, CHAT_MODEL
from src.utils.logger import setup_logger

logger = setup_logger("openai_client")

_client: AsyncOpenAI | None = None


class EmbeddingError(Exception):
    """Custom exception for embedding errors."""
    pass


def get_openai_client() -> AsyncOpenAI:
    """Get singleton AsyncOpenAI client instance."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE if OPENAI_API_BASE else None,
        )
        logger.info(f"AsyncOpenAI client initialized with model: {EMBED_MODEL}")
    return _client


def _validate_text(text: str) -> str:
    """Validate and clean input text."""
    if not text:
        raise EmbeddingError("Text cannot be empty")

    cleaned = text.strip()
    if not cleaned:
        raise EmbeddingError("Text cannot be only whitespace")

    return cleaned


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((RateLimitError, APIError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Retry attempt {retry_state.attempt_number} after error"
    ),
)
async def _create_embedding(client: AsyncOpenAI, text: str | list[str]):
    """Async embedding creation with retry logic."""
    return await client.embeddings.create(model=EMBED_MODEL, input=text)


async def embed(text: str) -> list[float]:
    """
    Generate embedding vector for text using OpenAI API.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats (1536 dimensions for ada-002)

    Raises:
        EmbeddingError: If text is empty or API call fails after retries
    """
    try:
        cleaned_text = _validate_text(text)
        client = get_openai_client()

        response = await _create_embedding(client, cleaned_text)
        embedding = response.data[0].embedding

        logger.debug(f"Generated embedding for text: {cleaned_text[:50]}...")
        return embedding
    except EmbeddingError:
        raise
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise EmbeddingError(f"Embedding generation failed: {e}") from e


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in a single API call.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors

    Raises:
        EmbeddingError: If any text is empty or API call fails after retries
    """
    if not texts:
        return []

    try:
        cleaned_texts = [_validate_text(t) for t in texts]
        client = get_openai_client()

        response = await _create_embedding(client, cleaned_texts)
        embeddings = [item.embedding for item in response.data]

        logger.debug(f"Generated {len(embeddings)} embeddings in batch")
        return embeddings
    except EmbeddingError:
        raise
    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        raise EmbeddingError(f"Batch embedding generation failed: {e}") from e


class ChatCompletionError(Exception):
    """Custom exception for chat completion errors."""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((RateLimitError, APIError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Chat completion retry attempt {retry_state.attempt_number} after error"
    ),
)
async def summarize_to_title(text: str, max_words: int = 10) -> str:
    """
    Summarize text into a short title using chat completion.

    Args:
        text: Text to summarize (usually first user message)
        max_words: Maximum words in title (default 10)

    Returns:
        Short title string

    Raises:
        ChatCompletionError: If API call fails after retries
    """
    try:
        client = get_openai_client()

        system_prompt = (f"Summarize the user's message into a short title of maximum {max_words} words. "
                         f"Only return the title, no quotes or extra text. Use the same language as the user's message.")

        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ChatCompletionUserMessageParam(role="user", content=text)
            ],
            max_tokens=50,
            temperature=0
        )

        title = response.choices[0].message.content.strip()
        logger.debug(f"Generated title: {title}")
        return title

    except Exception as e:
        logger.error(f"Failed to generate title: {e}")
        raise ChatCompletionError(f"Title generation failed: {e}") from e
