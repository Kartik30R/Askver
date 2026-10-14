import logging
from typing import List

from app.services.vector_service import get_embeddings_model

logger = logging.getLogger(__name__)


def get_embedding_engine():
    """Returns the project-standard Gemini embedding client for document indexing and retrieval."""
    return get_embeddings_model(is_query=False, task_type="retrieval_document")


def embed_text_strings(texts: List[str]) -> List[List[float]]:
    """Utility function to embed a list of text strings using the canonical project configuration."""
    try:
        embeddings_model = get_embedding_engine()
        return embeddings_model.embed_documents(texts)
    except Exception as exc:
        logger.error("Embedding generation failed: %s", exc)
        raise