import os
import logging
from typing import List, Dict, Any, Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/deal_db")


def get_embeddings_model():
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=GEMINI_API_KEY
    )


def index_client_deal_chunks(deal_id: str, chunks: List[Document]):
    """
    Indexes client RFP/BRD document chunks into a deal-isolated collection.
    """
    collection_name = f"deal_{deal_id}_docs"
    embeddings = get_embeddings_model()
    
    vector_store = PGVector.from_documents(
        embedding=embeddings,
        documents=chunks,
        collection_name=collection_name,
        connection_string=DATABASE_URL,
        pre_delete_collection=False
    )
    logger.info(f"Successfully indexed {len(chunks)} client doc chunks for deal: {deal_id}")
    return collection_name


def query_client_deal_docs(deal_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Searches client RFP/BRD documents uploaded for a specific deal.
    """
    collection_name = f"deal_{deal_id}_docs"
    embeddings = get_embeddings_model()
    
    try:
        vector_store = PGVector(
            collection_name=collection_name,
            connection_string=DATABASE_URL,
            embedding_function=embeddings
        )
        results = vector_store.similarity_search_with_score(query, k=top_k)
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            }
            for doc, score in results
        ]
    except Exception as e:
        logger.warning(f"No client document collection found or error querying deal {deal_id}: {str(e)}")
        return []


def query_internal_knowledge_base(
    query: str, 
    industry_filter: Optional[str] = None, 
    asset_type_filter: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Queries global company IP (Case Studies, Proposals, SoWs, Accelerators).
    """
    collection_name = "internal_company_knowledgebase"
    embeddings = get_embeddings_model()
    
    try:
        vector_store = PGVector(
            collection_name=collection_name,
            connection_string=DATABASE_URL,
            embedding_function=embeddings
        )
        
        filter_dict = {}
        if industry_filter:
            filter_dict["industry"] = industry_filter
        if asset_type_filter:
            filter_dict["asset_type"] = asset_type_filter

        results = vector_store.similarity_search_with_score(
            query, 
            k=top_k,
            filter=filter_dict if filter_dict else None
        )
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            }
            for doc, score in results
        ]
    except Exception as e:
        logger.error(f"Error querying internal knowledge base: {str(e)}")
        return []