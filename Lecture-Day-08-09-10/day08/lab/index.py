"""
index.py — Sprint 1: Build RAG Index
====================================
Mục tiêu Sprint 1 (60 phút):
  - Đọc và preprocess tài liệu từ data/docs/
  - Chunk tài liệu theo cấu trúc tự nhiên (heading/section)
  - Gắn metadata: source, section, department, effective_date, access
  - Embed và lưu vào vector store (ChromaDB)

Definition of Done Sprint 1:
  ✓ Script chạy được và index đủ docs
  ✓ Có ít nhất 3 metadata fields hữu ích cho retrieval
  ✓ Có thể kiểm tra chunk bằng list_chunks()
"""

import os
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

# Tinh chỉnh cho 5 tài liệu policy hiện tại:
# - Section trung bình khoảng 286 ký tự, p90 ~489 ký tự
# - Chunk 320 tokens giữ đủ ngữ cảnh theo điều khoản mà không làm prompt quá dài
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap để giữ ngữ cảnh giữa các chunk dài


# =============================================================================
# STEP 1: PREPROCESS
# Làm sạch text trước khi chunk và embed
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines = []
    header_done = False

    for line in lines:
        if not header_done:
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif line.startswith("==="):
                header_done = True
                content_lines.append(line)
            elif line.strip() == "" or line.isupper():
                continue
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)

    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return {
        "text": cleaned_text,
        "metadata": metadata,
    }


# =============================================================================
# STEP 2: CHUNK
# Chia tài liệu thành các đoạn nhỏ theo cấu trúc tự nhiên
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    # Bước 1: Split theo heading pattern "=== ... ==="
    sections = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            if current_section_text.strip():
                section_chunks = _split_by_size(
                    current_section_text.strip(),
                    base_metadata=base_metadata,
                    section=current_section,
                )
                chunks.extend(section_chunks)
            current_section = part.strip("= ").strip()
            current_section_text = ""
        else:
            current_section_text += part

    if current_section_text.strip():
        section_chunks = _split_by_size(
            current_section_text.strip(),
            base_metadata=base_metadata,
            section=current_section,
        )
        chunks.extend(section_chunks)

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    
    if len(text) <= chunk_chars:
        return [{
            "text": text,
            "metadata": {**base_metadata, "section": section},
        }]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        chunk_text = text[start:end]

        chunks.append({
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        })
        start = end - overlap_chars

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================


def _normalize_chunk_metadata(
    metadata: Dict[str, Any],
    fallback_source: str,
    fallback_section: str = "General",
) -> Dict[str, Any]:
    
    meta = dict(metadata or {})
    meta["source"] = str(meta.get("source") or fallback_source)
    meta["section"] = str(meta.get("section") or fallback_section)
    meta["effective_date"] = str(meta.get("effective_date") or "unknown")
    return meta


@lru_cache(maxsize=1)
def _get_openai_client():
    """Khởi tạo OpenAI client một lần để tái sử dụng trong suốt quá trình index."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "Chưa cài package 'openai'. Hãy chạy: pip install openai"
        ) from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "Thiếu OPENAI_API_KEY trong môi trường. Hãy thêm key vào file .env trước khi build index."
        )

    return OpenAI(api_key=api_key)

def get_embedding(text: str) -> List[float]:
    
    client = _get_openai_client()
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # Tránh gửi chuỗi rỗng vì API embeddings yêu cầu input hợp lệ.
    normalized_text = re.sub(r"\s+", " ", text).strip() or "N/A"

    response = client.embeddings.create(
        input=normalized_text,
        model=model_name,
    )
    return response.data[0].embedding


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    
    import chromadb

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)
        indexed_in_file = 0

        for i, chunk in enumerate(chunks):
            chunk_text = chunk["text"].strip()
            if not chunk_text:
                continue

            chunk_id = f"{filepath.stem}_{i}"
            embedding = get_embedding(chunk_text)
            chunk_metadata = _normalize_chunk_metadata(
                metadata=chunk.get("metadata", {}),
                fallback_source=str(filepath),
            )

            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk_text],
                metadatas=[chunk_metadata],
            )
            indexed_in_file += 1

        print(f"    → {indexed_in_file} chunks đã index")
        total_chunks += indexed_in_file

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")
    print(f"Index đã lưu tại: {db_dir}")


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])
        documents: List[str] = list(results.get("documents") or [])
        metadatas = list(results.get("metadatas") or [])

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            print(f"[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Text preview: {doc[:120]}...")
            print()
    except Exception as e:
        print(f"Lỗi khi đọc index: {e}")
        print("Hãy chạy build_index() trước.")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])
        metadatas = list(results.get("metadatas") or [])

        print(f"\nTổng chunks: {len(metadatas)}")

        departments = {}
        missing_date = 0
        for meta in metadatas:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Phân bố theo department:")
        for dept, count in departments.items():
            print(f"  {dept}: {count} chunks")
        print(f"Chunks thiếu effective_date: {missing_date}")

    except Exception as e:
        print(f"Lỗi: {e}. Hãy chạy build_index() trước.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    # Bước 1: Kiểm tra docs
    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\nTìm thấy {len(doc_files)} tài liệu:")
    for f in doc_files:
        print(f"  - {f.name}")

    # Bước 2: Test preprocess và chunking (không cần API key)
    print("\n--- Test preprocess + chunking ---")
    for filepath in doc_files[:1]:  # Test với 1 file đầu
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        print(f"\nFile: {filepath.name}")
        print(f"  Metadata: {doc['metadata']}")
        print(f"  Số chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  [Chunk {i+1}] Section: {chunk['metadata']['section']}")
            print(f"  Text: {chunk['text'][:150]}...")

    # Bước 3: Build index (yêu cầu implement get_embedding)
    print("\n--- Build Full Index ---")
    print("Lưu ý: OpenAI embedding đã sẵn sàng. Cần có OPENAI_API_KEY trong .env để chạy bước này.")
    # Uncomment dòng dưới để build index thật:
    # build_index()

    # Bước 4: Kiểm tra index
    # Uncomment sau khi build_index() thành công:
    # list_chunks()
    # inspect_metadata_coverage()

    print("\nSprint 1 setup hoàn thành!")
    print("Việc cần làm:")
    print("  1. Thiết lập OPENAI_API_KEY trong .env")
    print("  2. Uncomment build_index() để index toàn bộ tài liệu")
    print("  3. Kiểm tra chất lượng bằng list_chunks() và inspect_metadata_coverage()")
    print("  4. Nếu chunking chưa tốt: cải thiện _split_by_size() để split theo paragraph")
