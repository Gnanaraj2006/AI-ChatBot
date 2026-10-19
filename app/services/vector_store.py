import os
import json
import math
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from app.config import settings
from app.models.schemas import DocumentChunk, ChunkMetadata, DocumentInfo


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore:
    """
    Hybrid Vector Store:
    Uses ChromaDB if installed; otherwise transparently utilizes a persistent
    high-speed in-memory vector index with cosine similarity search.
    """

    def __init__(self):
        self.persist_dir = Path(settings.CHROMA_PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.fallback_file = self.persist_dir / "index_store.json"

        self._use_chroma = False
        self._chroma_client = None
        self._collection = None
        self._memory_chunks: Dict[str, Dict[str, Any]] = {}
        self._documents_meta: Dict[str, Dict[str, Any]] = {}

        self._init_backend()

    def _init_backend(self):
        # Try to initialize ChromaDB
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._chroma_client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name="studymaterials_collection",
                metadata={"hnsw:space": "cosine"}
            )
            self._use_chroma = True
            print("[VectorStore] Successfully initialized ChromaDB persistent backend.")
        except Exception as e:
            print(f"[VectorStore] ChromaDB not available ({e}). Using native embedded vector store.")
            self._use_chroma = False
            self._load_fallback_index()

    def get_backend_name(self) -> str:
        return "ChromaDB (Persistent)" if self._use_chroma else "Embedded Native Vector Store"

    def _load_fallback_index(self):
        if self.fallback_file.exists():
            try:
                with open(self.fallback_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._memory_chunks = data.get("chunks", {})
                    self._documents_meta = data.get("docs", {})
                print(f"[VectorStore] Loaded {len(self._memory_chunks)} chunks from fallback store.")
            except Exception as e:
                print(f"[VectorStore] Error loading fallback store: {e}")
                self._memory_chunks = {}
                self._documents_meta = {}

    def _save_fallback_index(self):
        try:
            with open(self.fallback_file, "w", encoding="utf-8") as f:
                json.dump({
                    "chunks": self._memory_chunks,
                    "docs": self._documents_meta
                }, f, indent=2)
        except Exception as e:
            print(f"[VectorStore] Error saving fallback store: {e}")

    def add_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        doc_info: DocumentInfo
    ):
        if not chunks:
            return

        # Record doc metadata
        self._documents_meta[doc_info.id] = doc_info.model_dump()

        if self._use_chroma and self._collection is not None:
            try:
                ids = [c.id for c in chunks]
                texts = [c.text for c in chunks]
                metadatas = [c.metadata.model_dump() for c in chunks]

                self._collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
                return
            except Exception as e:
                print(f"[VectorStore] Chroma upsert failed ({e}), saving to fallback.")

        # Fallback storage
        for chunk, emb in zip(chunks, embeddings):
            self._memory_chunks[chunk.id] = {
                "id": chunk.id,
                "text": chunk.text,
                "metadata": chunk.metadata.model_dump(),
                "embedding": emb
            }
        self._save_fallback_index()

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        doc_ids: Optional[List[str]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Returns list of (DocumentChunk, similarity_score) sorted by similarity desc.
        """
        results: List[Tuple[DocumentChunk, float]] = []

        if self._use_chroma and self._collection is not None:
            try:
                where_clause = None
                if doc_ids and len(doc_ids) == 1:
                    where_clause = {"doc_id": doc_ids[0]}
                elif doc_ids and len(doc_ids) > 1:
                    where_clause = {"doc_id": {"$in": doc_ids}}

                query_params = {
                    "query_embeddings": [query_embedding],
                    "n_results": min(top_k, self._collection.count() or 1),
                }
                if where_clause:
                    query_params["where"] = where_clause

                chroma_res = self._collection.query(**query_params)

                if chroma_res and chroma_res["ids"] and len(chroma_res["ids"][0]) > 0:
                    for i in range(len(chroma_res["ids"][0])):
                        cid = chroma_res["ids"][0][i]
                        text = chroma_res["documents"][0][i]
                        meta = chroma_res["metadatas"][0][i]
                        # Chroma cosine distance is in [0, 2], score = 1 - (dist / 2)
                        dist = chroma_res["distances"][0][i] if "distances" in chroma_res and chroma_res["distances"] else 0.5
                        score = max(0.0, 1.0 - (dist / 2.0))

                        chunk = DocumentChunk(
                            id=cid,
                            text=text,
                            metadata=ChunkMetadata(**meta),
                            score=score
                        )
                        results.append((chunk, score))
                    return results
            except Exception as e:
                print(f"[VectorStore] Chroma search failed ({e}), searching fallback.")

        # Fallback memory search
        scored_items = []
        for cid, data in self._memory_chunks.items():
            meta = data["metadata"]
            if doc_ids and meta.get("doc_id") not in doc_ids:
                continue

            emb = data.get("embedding", [])
            score = cosine_similarity(query_embedding, emb)
            chunk = DocumentChunk(
                id=cid,
                text=data["text"],
                metadata=ChunkMetadata(**meta),
                score=score
            )
            scored_items.append((chunk, score))

        scored_items.sort(key=lambda x: x[1], reverse=True)
        return scored_items[:top_k]

    def get_all_chunks_for_docs(self, doc_ids: Optional[List[str]] = None) -> List[DocumentChunk]:
        """Returns all chunks for given docs (or all) for summaries/flashcards."""
        chunks: List[DocumentChunk] = []

        if self._use_chroma and self._collection is not None:
            try:
                where_clause = None
                if doc_ids and len(doc_ids) == 1:
                    where_clause = {"doc_id": doc_ids[0]}
                elif doc_ids and len(doc_ids) > 1:
                    where_clause = {"doc_id": {"$in": doc_ids}}

                res = self._collection.get(where=where_clause)
                for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
                    chunks.append(DocumentChunk(
                        id=cid,
                        text=doc,
                        metadata=ChunkMetadata(**meta)
                    ))
                if chunks:
                    return chunks
            except Exception as e:
                print(f"[VectorStore] Chroma get failed ({e}), using fallback.")

        for cid, data in self._memory_chunks.items():
            meta = data["metadata"]
            if doc_ids and meta.get("doc_id") not in doc_ids:
                continue
            chunks.append(DocumentChunk(
                id=cid,
                text=data["text"],
                metadata=ChunkMetadata(**meta)
            ))
        return chunks

    def list_documents(self) -> List[DocumentInfo]:
        docs = []
        for doc_id, meta in self._documents_meta.items():
            docs.append(DocumentInfo(**meta))
        return sorted(docs, key=lambda d: d.uploaded_at, reverse=True)

    def delete_document(self, doc_id: str):
        if doc_id in self._documents_meta:
            del self._documents_meta[doc_id]

        if self._use_chroma and self._collection is not None:
            try:
                self._collection.delete(where={"doc_id": doc_id})
            except Exception as e:
                print(f"[VectorStore] Chroma delete error: {e}")

        # Delete from fallback
        keys_to_del = [k for k, v in self._memory_chunks.items() if v["metadata"].get("doc_id") == doc_id]
        for k in keys_to_del:
            del self._memory_chunks[k]

        self._save_fallback_index()

    def get_stats(self) -> Dict[str, Any]:
        count = len(self._memory_chunks)
        if self._use_chroma and self._collection is not None:
            try:
                count = self._collection.count()
            except Exception:
                pass
        return {
            "documents_count": len(self._documents_meta),
            "chunks_count": count,
            "backend": self.get_backend_name()
        }


vector_store = VectorStore()
