import logging
from pathlib import Path
from typing import Any, Dict, List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

TEXT_FILE_TYPES = {"txt", "md", "markdown", "csv", "json", "html", "htm", "rtf"}


def _load_text_with_encoding_detection(file_path: str) -> str:
    """Loads text files with a safe fallback chain for Windows and UTF-8 content."""
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1", "ascii"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as handle:
                return handle.read()
        except (UnicodeDecodeError, LookupError):
            continue

    logger.warning("Could not detect encoding for %s; falling back to utf-8 with replacement", file_path)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def _sanitize_document_text(text: str) -> str:
    if not text:
        return ""
    cleaned = "\n".join(line.rstrip() for line in text.splitlines())
    return "\n".join(part for part in cleaned.split("\n") if part.strip())


def _safe_langchain_document(page_content: str, file_path: str, metadata: Dict[str, Any]) -> Document:
    return Document(page_content=_sanitize_document_text(page_content), metadata={"source": file_path, **metadata})


def _chunk_documents(raw_documents: List[Document], *, chunk_size: int = 1000, chunk_overlap: int = 180) -> List[Document]:
    """Uses a recursive chunker tuned for enterprise documents with natural-language overlap."""
    if not raw_documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=False,
    )
    chunks = splitter.split_documents(raw_documents)
    cleaned_chunks = [
        Document(page_content=_sanitize_document_text(chunk.page_content), metadata=chunk.metadata)
        for chunk in chunks
        if _sanitize_document_text(chunk.page_content).strip()
    ]
    logger.info("Split %s raw document(s) into %s chunks", len(raw_documents), len(cleaned_chunks))
    return cleaned_chunks


def parse_and_chunk_document(file_path: str, file_type: str, metadata: Dict[str, Any] = None) -> List[Document]:
    """Parses text-based and structured document files and splits them into overlapping semantic chunks."""
    if metadata is None:
        metadata = {}

    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = (file_type or "").lower().strip(".")
    raw_documents: List[Document] = []

    try:
        if ext in {"pdf"}:
            raw_documents = [
                _safe_langchain_document(page.page_content, str(file_path_obj), metadata)
                for page in PyPDFLoader(str(file_path_obj)).load()
            ]
            logger.info("Loaded PDF document %s", file_path)

        elif ext in {"docx", "doc"}:
            from docx import Document as DocxDocument

            doc = DocxDocument(str(file_path_obj))
            full_text = "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())
            raw_documents = [_safe_langchain_document(full_text, str(file_path_obj), metadata)]
            logger.info("Loaded DOCX document %s", file_path)

        elif ext in {"pptx"}:
            from pptx import Presentation

            presentation = Presentation(str(file_path_obj))
            full_text = "\n".join(
                shape.text for slide in presentation.slides for shape in slide.shapes if getattr(shape, "text", "").strip()
            )
            raw_documents = [_safe_langchain_document(full_text, str(file_path_obj), metadata)]
            logger.info("Loaded PPTX document %s", file_path)

        elif ext in TEXT_FILE_TYPES:
            text_content = _load_text_with_encoding_detection(str(file_path_obj))
            raw_documents = [_safe_langchain_document(text_content, str(file_path_obj), metadata)]
            logger.info("Loaded text document %s (%s)", file_path, ext)

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        chunked = _chunk_documents(raw_documents)
        logger.info("Successfully parsed %s into %s chunks.", file_path, len(chunked))
        return chunked

    except Exception as exc:
        logger.error("Error parsing document %s: %s", file_path, exc)
        raise