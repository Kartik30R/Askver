import os
import logging
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_embedding_engine() -> GoogleGenerativeAIEmbeddings:
    """
    Initializes and returns Google's free hosted text-embedding-004 engine.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is missing.")
    
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=GEMINI_API_KEY
    )


def embed_text_strings(texts: List[str]) -> List[List[float]]:
    """
    Utility function to embed a list of text strings.
    """
    try:
        embeddings_model = get_embedding_engine()
        return embeddings_model.embed_documents(texts)
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        raise e