"""
retrieval.py — TiDB vector retrieval for knowledge base.

Implements cosine similarity search over kb_chunks embeddings.
"""

import json
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.learning.models import KBChunk, KBDocument
from app.core.config import settings


def get_embedder():
    """Lazy load sentence transformer."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_query(query: str) -> List[float]:
    """Embed a query string."""
    embedder = get_embedder()
    embedding = embedder.encode(query, normalize_embeddings=True)
    return embedding.tolist()


def vector_search(
    db: Session,
    query_embedding: List[float],
    top_k: int = 5,
    distance_threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Perform cosine similarity search on kb_chunks using TiDB vector index.

    Args:
        db: Database session
        query_embedding: 384-dim normalized embedding
        top_k: Number of results to return
        distance_threshold: Maximum cosine distance (0-1), lower = more similar

    Returns:
        List of dicts with chunk data and similarity score
    """
    # Convert embedding to JSON array string for TiDB
    embedding_json = json.dumps(query_embedding)

    # TiDB vector search query using cosine distance
    # Distance = 1 - cosine_similarity, so we want distance < threshold
    sql = text("""
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.page,
            c.text,
            c.metadata,
            c.embedding,
            d.title as document_title,
            d.source_url,
            d.license,
            d.version,
            VEC_COSINE_DISTANCE(c.embedding, :embedding) as distance
        FROM kb_chunks c
        JOIN kb_documents d ON c.document_id = d.id
        WHERE VEC_COSINE_DISTANCE(c.embedding, :embedding) < :threshold
        ORDER BY VEC_COSINE_DISTANCE(c.embedding, :embedding)
        LIMIT :top_k
    """)

    try:
        result = db.execute(sql, {
            "embedding": embedding_json,
            "threshold": distance_threshold,
            "top_k": top_k,
        })

        rows = []
        for row in result:
            rows.append({
                "id": row.id,
                "document_id": row.document_id,
                "chunk_index": row.chunk_index,
                "page": row.page,
                "text": row.text,
                "metadata": row.chunk_metadata,
                "embedding": row.embedding,
                "document_title": row.document_title,
                "source_url": row.source_url,
                "license": row.license,
                "version": row.version,
                "distance": float(row.distance),
                "similarity": 1.0 - float(row.distance),
            })
        return rows
    except Exception as e:
        # Fallback for TiDB versions without VEC_COSINE_DISTANCE
        print(f"Vector search failed, falling back to manual computation: {e}")
        return fallback_vector_search(db, query_embedding, top_k, distance_threshold)


def fallback_vector_search(
    db: Session,
    query_embedding: List[float],
    top_k: int = 5,
    distance_threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """Fallback: fetch all embeddings and compute cosine similarity in Python."""
    import numpy as np

    chunks = db.query(KBChunk).join(KBDocument).all()
    query_vec = np.array(query_embedding)

    results = []
    for chunk in chunks:
        try:
            chunk_embedding = json.loads(chunk.embedding) if isinstance(chunk.embedding, str) else chunk.embedding
            chunk_vec = np.array(chunk_embedding)

            # Cosine similarity (vectors are normalized)
            similarity = float(np.dot(query_vec, chunk_vec))
            distance = 1.0 - similarity

            if distance < distance_threshold:
                doc = chunk.document
                results.append({
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "page": chunk.page,
                    "text": chunk.text,
                    "metadata": chunk.chunk_metadata,
                    "embedding": chunk.embedding,
                    "document_title": doc.title if doc else "",
                    "source_url": doc.source_url if doc else "",
                    "license": doc.license if doc else "",
                    "version": doc.version if doc else "",
                    "distance": distance,
                    "similarity": similarity,
                })
        except Exception:
            continue

    # Sort by distance (ascending = most similar first)
    results.sort(key=lambda x: x["distance"])
    return results[:top_k]


def retrieve_for_question(
    db: Session,
    question: str,
    top_k: int = 5,
    distance_threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """High-level retrieval for a student question."""
    query_embedding = embed_query(question)
    return vector_search(db, query_embedding, top_k, distance_threshold)