from __future__ import annotations

from typing import Any, Callable

from .chunking import compute_similarity
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

    def _make_record(self, doc: Document) -> dict[str, Any]:
        embedding = self._embedding_fn(doc.content)
        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": doc.metadata.copy() if doc.metadata else {},
            "embedding": embedding
        }

    def _search_records(
        self,
        query: str,
        records: list[dict[str, Any]],
        top_k: int,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        if not records:
            return []
        if top_k <= 0:
            return []
            
        query_embedding = self._embedding_fn(query)
        scored_records = []
        
        for record in records:
            score = compute_similarity(query_embedding, record["embedding"])
            if min_score is not None and score < min_score:
                continue
            result_record = record.copy()
            result_record["score"] = score
            scored_records.append(result_record)
            
        scored_records.sort(key=lambda x: x["score"], reverse=True)
        return scored_records[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        # TỐI ƯU: Sử dụng extend và list comprehension để thêm nhanh hơn
        new_records = [self._make_record(doc) for doc in docs]
        self._store.extend(new_records)

    def search(self, query: str, top_k: int = 5, min_score: float | None = None) -> list[dict[str, Any]]:
        return self._search_records(query, self._store, top_k, min_score=min_score)

    def get_collection_size(self) -> int:
        return len(self._store)

    def search_with_filter(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
        min_score: float | None = None,
    ) -> list[dict]:
        if not metadata_filter:
            return self.search(query, top_k, min_score=min_score)
            
        # TỐI ƯU: Viết lại logic filter gọn gàng và tốc độ bằng all()
        filtered_records = [
            record for record in self._store
            if all(record["metadata"].get(k) == v for k, v in metadata_filter.items())
        ]
                
        return self._search_records(query, filtered_records, top_k, min_score=min_score)

    def delete_document(self, doc_id: str) -> bool:
        initial_size = len(self._store)
        self._store = [
            record for record in self._store 
            if record["id"] != doc_id and record["metadata"].get("doc_id") != doc_id
        ]
        return len(self._store) < initial_size