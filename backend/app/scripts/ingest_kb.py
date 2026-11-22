#!/usr/bin/env python
"""
ingest_kb.py — Knowledge Base ingestion CLI for PrepGenius.

Loads trusted source documents, chunks them, embeds with sentence-transformers,
and upserts into TiDB kb_chunks with VECTOR(384) embeddings.

Usage:
    python -m app.scripts.ingest_kb --source-dir knowledge_base/
    python -m app.scripts.ingest_kb --file knowledge_base/python_basics.md --title "Python Basics" --url "https://example.com"
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.modules.learning.models import KBDocument, KBChunk


# Lazy import for heavy dependencies
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def get_text_splitter():
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of content for idempotent upsert."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_documents(source_dir: Path) -> List[Dict[str, Any]]:
    """Load all supported documents from source directory."""
    documents = []
    supported_extensions = {".md", ".txt", ".pdf", ".html", ".json"}

    for file_path in source_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            try:
                if file_path.suffix.lower() == ".pdf":
                    import pymupdf as fitz
                    doc = fitz.open(str(file_path))
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    doc.close()
                else:
                    text = file_path.read_text(encoding="utf-8")

                if text.strip():
                    documents.append({
                        "title": file_path.stem.replace("_", " ").replace("-", " ").title(),
                        "source_url": "",
                        "license": "internal",
                        "version": "1.0",
                        "content": text,
                        "file_path": str(file_path),
                    })
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}", file=sys.stderr)

    return documents


def chunk_document(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """Split document into overlapping chunks with metadata."""
    splitter = get_text_splitter()
    chunks = splitter.split_text(text)

    result = []
    for i, chunk_text in enumerate(chunks):
        result.append({
            "chunk_index": i,
            "page": None,  # Could be enhanced for PDFs
            "text": chunk_text.strip(),
            "metadata": {"chunk_size": len(chunk_text)},
        })
    return result


def embed_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate embeddings for all chunks."""
    embedder = get_embedder()
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    for i, embedding in enumerate(embeddings):
        chunks[i]["embedding"] = embedding.tolist()

    return chunks


def upsert_document(db: Session, doc_data: Dict[str, Any], chunks: List[Dict[str, Any]]) -> KBDocument:
    """Upsert document and its chunks idempotently by content hash."""
    full_text = " ".join(c["text"] for c in chunks)
    content_hash = compute_content_hash(full_text)

    # Check if document with same content hash exists
    existing_doc = db.query(KBDocument).filter(KBDocument.content_hash == content_hash).first()

    if existing_doc:
        print(f"Document '{doc_data['title']}' already exists (hash match), skipping...")
        return existing_doc

    # Create new document
    doc = KBDocument(
        title=doc_data["title"],
        source_url=doc_data.get("source_url", ""),
        license=doc_data.get("license", "internal"),
        version=doc_data.get("version", "1.0"),
        content_hash=content_hash,
    )
    db.add(doc)
    db.flush()  # Get doc.id

    # Create chunks with embeddings
    for chunk_data in chunks:
        chunk = KBChunk(
            document_id=doc.id,
            chunk_index=chunk_data["chunk_index"],
            page=chunk_data["page"],
            text=chunk_data["text"],
            metadata=chunk_data["metadata"],
            embedding=json.dumps(chunk_data["embedding"]),  # Store as JSON string
        )
        db.add(chunk)

    db.commit()
    db.refresh(doc)
    print(f"Inserted document: {doc.title} ({len(chunks)} chunks)")
    return doc


def create_vector_index(db: Session):
    """Create TiDB vector index on kb_chunks.embedding if not exists."""
    try:
        # TiDB-specific: Create vector index for cosine distance
        db.execute(text("""
            CREATE VECTOR INDEX IF NOT EXISTS idx_kb_chunk_embedding
            ON kb_chunks (embedding)
            USING HNSW
            WITH (distance_type = 'cosine', M = 16, ef_construction = 200)
        """))
        db.commit()
        print("Vector index created/verified on kb_chunks.embedding")
    except Exception as e:
        print(f"Note: Vector index creation skipped (may require TiDB 8.4+): {e}")
        db.rollback()


def ingest_directory(source_dir: str, recreate_index: bool = False):
    """Main ingestion pipeline."""
    source_path = Path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    engine = create_engine(
        settings.get_database_url(),
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        if recreate_index:
            create_vector_index(db)

        documents = load_documents(source_path)
        print(f"Found {len(documents)} documents to process")

        for doc_data in documents:
            print(f"Processing: {doc_data['title']}")
            chunks = chunk_document(doc_data["content"])
            chunks = embed_chunks(chunks)
            upsert_document(db, doc_data, chunks)

        print("Ingestion complete!")


def ingest_single_file(file_path: str, title: str, source_url: str = "", license: str = "internal", version: str = "1.0"):
    """Ingest a single file with metadata."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() == ".pdf":
        import pymupdf as fitz
        doc = fitz.open(str(path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
    else:
        text = path.read_text(encoding="utf-8")

    doc_data = {
        "title": title,
        "source_url": source_url,
        "license": license,
        "version": version,
        "content": text,
    }

    engine = create_engine(
        settings.get_database_url(),
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        chunks = chunk_document(text)
        chunks = embed_chunks(chunks)
        upsert_document(db, doc_data, chunks)
        print(f"Single file ingestion complete: {title} ({len(chunks)} chunks)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PrepGenius Knowledge Base Ingestion")
    parser.add_argument("--source-dir", type=str, help="Directory containing source documents")
    parser.add_argument("--file", type=str, help="Single file to ingest")
    parser.add_argument("--title", type=str, help="Document title (required with --file)")
    parser.add_argument("--url", type=str, default="", help="Source URL")
    parser.add_argument("--license", type=str, default="internal", help="License type")
    parser.add_argument("--version", type=str, default="1.0", help="Document version")
    parser.add_argument("--recreate-index", action="store_true", help="Create vector index")

    args = parser.parse_args()

    if args.source_dir:
        ingest_directory(args.source_dir, recreate_index=args.recreate_index)
    elif args.file and args.title:
        ingest_single_file(args.file, args.title, args.url, args.license, args.version)
    else:
        parser.print_help()
        sys.exit(1)