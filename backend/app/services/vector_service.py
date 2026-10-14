import asyncio
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from langchain_community.vectorstores import PGVector
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings

logger = logging.getLogger(__name__)

def _to_sync_psycopg2_url(url: str) -> str:
    """
    LangChain's PGVector uses a *synchronous* SQLAlchemy engine. Passing the app's
    `postgresql+asyncpg://` URL to it triggers
    "greenlet_spawn has not been called; can't call await_only() here".

    For local Docker Postgres instances with no TLS configured, force `sslmode=disable`
    so psycopg2 does not attempt an SSL handshake that the container cannot satisfy.
    """
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            converted = "postgresql+psycopg2://" + url[len(prefix):]
            if "sslmode=" not in converted:
                separator = "&" if "?" in converted else "?"
                converted = f"{converted}{separator}sslmode=disable"
            return converted
    return url


# Async URL stays in app.core.database; PGVector gets its own sync URL.
PGVECTOR_CONNECTION_STRING = _to_sync_psycopg2_url(settings.DATABASE_URL)
GEMINI_API_KEY = settings.GEMINI_API_KEY
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"


@lru_cache(maxsize=8)
def get_embeddings_model(is_query: bool = False, *, task_type: Optional[str] = None):
    """
    Returns a Google Gemini embedding model configured for either document indexing or query-time retrieval.
    `task_type` follows the Gemini embeddings contract used by the Google GenAI SDK and improves retrieval quality.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required for embeddings")

    resolved_task_type = task_type or ("retrieval_query" if is_query else "retrieval_document")
    logger.info(
        "Using Google Generative AI Embeddings model=%s task_type=%s",
        DEFAULT_EMBEDDING_MODEL,
        resolved_task_type,
    )

    return GoogleGenerativeAIEmbeddings(
        model=DEFAULT_EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY,
        task_type=resolved_task_type,
    )


def _sync_index_documents(embeddings, documents: List[Document], collection_name: str, *, pre_delete_collection: bool = False):
    """Synchronous helper to index documents into PGVector in a worker thread.

    Use JSONB metadata to stay compatible with the current PGVector upstream contract.
    JSONB also enables efficient metadata filtering instead of the deprecated JSON path.
    """
    PGVector.from_documents(
        embedding=embeddings,
        documents=documents,
        collection_name=collection_name,
        connection_string=PGVECTOR_CONNECTION_STRING,
        pre_delete_collection=pre_delete_collection,
        use_jsonb=True,
    )
    return collection_name


def index_documents_to_collection(collection_name: str, documents: List[Document], *, pre_delete_collection: bool = False) -> str:
    """Indexes a chunk list into the given PGVector collection without changing the app contract or schema."""
    if not documents:
        logger.warning("Skipping vector indexing for empty document list in collection %s", collection_name)
        return collection_name

    embeddings = get_embeddings_model(is_query=False, task_type="retrieval_document")
    return _sync_index_documents(
        embeddings,
        documents,
        collection_name,
        pre_delete_collection=pre_delete_collection,
    )


async def index_client_deal_chunks(deal_id: str, chunks: List[Document]):
    """Async version for deal-scoped client documents."""
    collection_name = f"deal_{deal_id}_docs"
    result = await asyncio.to_thread(
        index_documents_to_collection, collection_name, chunks, pre_delete_collection=False
    )
    logger.info("Successfully indexed %s client doc chunks for deal: %s", len(chunks), deal_id)
    return result


async def index_internal_knowledge_chunks(collection_name: str, chunks: List[Document], *, pre_delete_collection: bool = False):
    """Async version for company knowledge assets."""
    return await asyncio.to_thread(
        index_documents_to_collection,
        collection_name,
        chunks,
        pre_delete_collection=pre_delete_collection,
    )


def _normalize_vector_results(results: List[tuple[Document, float]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for doc, score in results:
        normalized.append(
            {
                "content": getattr(doc, "page_content", ""),
                "metadata": getattr(doc, "metadata", {}) or {},
                "score": float(score),
            }
        )
    return normalized


def query_client_deal_docs(deal_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Searches the deal-isolated vector store for the most relevant client document chunks."""
    collection_name = f"deal_{deal_id}_docs"
    try:
        vector_store = PGVector(
            collection_name=collection_name,
            connection_string=PGVECTOR_CONNECTION_STRING,
            embedding_function=get_embeddings_model(is_query=True, task_type="retrieval_query"),
            use_jsonb=True,
        )
        results = vector_store.similarity_search_with_score(query, k=top_k)
        return _normalize_vector_results(results)
    except Exception as exc:
        logger.warning("No client document collection found or error querying deal %s: %s", deal_id, exc)
        return []


def query_internal_knowledge_base(
    query: str,
    industry_filter: Optional[str] = None,
    asset_type_filter: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Queries the global knowledge base using metadata filters and embedding-based retrieval."""
    collection_name = "internal_company_knowledgebase"
    try:
        vector_store = PGVector(
            collection_name=collection_name,
            connection_string=PGVECTOR_CONNECTION_STRING,
            embedding_function=get_embeddings_model(is_query=True, task_type="retrieval_query"),
            use_jsonb=True,
        )

        filter_dict: Dict[str, str] = {}
        if industry_filter:
            filter_dict["industry"] = industry_filter
        if asset_type_filter:
            filter_dict["asset_type"] = asset_type_filter

        results = vector_store.similarity_search_with_score(
            query,
            k=top_k,
            filter=filter_dict if filter_dict else None,
        )
        return _normalize_vector_results(results)
    except Exception as exc:
        logger.error("Error querying internal knowledge base: %s", exc)
        return []