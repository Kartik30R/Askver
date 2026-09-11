import os
import logging
from typing import List, Dict, Any

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredPowerPointLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

def parse_and_chunk_document(file_path: str, file_type: str, metadata: Dict[str, Any] = None) -> List[Document]:
    """
    Parses PDF, DOCX, PPTX, or TXT files and splits them into semantic chunks for vector indexing.
    """
    if metadata is None:
        metadata = {}

    try:
        # 1. Load Document based on file extension
        loader = None
        if file_type == 'pdf':
            loader = PyPDFLoader(file_path)
        elif file_type == 'docx':
            loader = Docx2txtLoader(file_path)
        elif file_type == 'txt':
            loader = TextLoader(file_path)
        elif file_type == 'pptx':
            loader = UnstructuredPowerPointLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        raw_documents = loader.load()

        # 2. Add custom metadata to all pages/sections
        for doc in raw_documents:
            doc.metadata.update(metadata)

        # 3. Chunk Document
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunked_documents = text_splitter.split_documents(raw_documents)
        logger.info(f"Successfully parsed {file_path} into {len(chunked_documents)} chunks.")
        
        return chunked_documents

    except Exception as e:
        logger.error(f"Error parsing document {file_path}: {str(e)}")
        raise e