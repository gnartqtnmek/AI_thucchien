from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent import KnowledgeBaseAgent
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

SEARCH_TOP_K = 8
ANSWER_TOP_K = 6

SAMPLE_FILES = [
    "data/co-quan-quan-ly-se-giam-sat-gia-dich-vu-starlink-tai-viet-nam.txt",
    "data/cuoc-dau-cua-hai-cong-cu-ai-tai-cong-so-trung-quoc.txt",
    "data/doi_moi_sang_tao_khoi_nghiep.txt",
    "data/nen-tang-ho-tro-tim-nha-thau.txt",
    "data/phi-hanh-doan-artemis-ii-vuot-nua-duong-ve-trai-dat.txt",
    "data/phong-thanh-cong-ve-tinh-tu-nhan.txt",
    "data/vn-thi-diem-doanh-nghiep-mot-nguoi.txt",
    "data/vu_tru_co_my.txt"
]


def load_documents_from_files(file_paths: list[str]) -> list[Document]:
    """Load documents from file paths for the manual demo."""
    allowed_extensions = {".md", ".txt"}
    documents: list[Document] = []

    for raw_path in file_paths:
        path = Path(raw_path)

        if path.suffix.lower() not in allowed_extensions:
            print(f"Skipping unsupported file type: {path} (allowed: .md, .txt)")
            continue

        if not path.exists() or not path.is_file():
            print(f"Skipping missing file: {path}")
            continue

        content = path.read_text(encoding="utf-8")
        documents.append(
            Document(
                id=path.stem,
                content=content,
                metadata={"source": str(path), "extension": path.suffix.lower()},
            )
        )

    return documents


def demo_llm(prompt: str) -> str:
    """A simple mock LLM for manual RAG testing."""
    return f"\n[DEMO LLM] === TOÀN BỘ PROMPT SẼ GỬI CHO LLM ===\n{prompt}\n============================================="

def real_llm(prompt: str) -> str:
    """Gọi API thật của OpenAI để trả lời câu hỏi"""
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return "\n[LỖI API]: Chưa tìm thấy OPENAI_API_KEY. Không thể gọi OpenAI để tổng hợp câu trả lời."

    try:
        from openai import OpenAI

        client = OpenAI(timeout=45.0, max_retries=1)
        print("\n[HỆ THỐNG] Đang gửi Context và Câu hỏi cho OpenAI suy nghĩ...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý AI thông minh. Hãy trả lời câu hỏi ĐÚNG, NGẮN GỌN và TRỰC TIẾP dựa trên phần Context được cung cấp."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2 
        )
        return f"\n[OPENAI TRẢ LỜI]:\n{response.choices[0].message.content}"
    except Exception as e:
        return f"\n[LỖI API]: {str(e)}\nBạn đã cấu hình OPENAI_API_KEY trong file .env chưa?"


def run_manual_demo(question: str | None = None, sample_files: list[str] | None = None) -> int:
    files = sample_files or SAMPLE_FILES
    query = question or "Summarize the key information from the loaded files."

    print("=== Manual File Test ===")
    print("Accepted file types: .md, .txt")
    print("Input file list:")
    for file_path in files:
        print(f"  - {file_path}")

    docs = load_documents_from_files(files)
    if not docs:
        print("\nNo valid input files were loaded.")
        return 1

    print(f"\nLoaded {len(docs)} documents")

    load_dotenv(override=False)
    
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            embedder = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "openai":
        try:
            embedder = OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    else:
        embedder = _mock_embed

    print(f"\nEmbedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")

    # Khởi tạo chiến lược chia chunk Fixed Size (đúng với tên file script)
    from src.chunking import FixedSizeChunker
    chunker = FixedSizeChunker(chunk_size=500, overlap=100)
    
    chunked_docs = []
    for doc in docs:
        chunks = chunker.chunk(doc.content)
        for i, text_chunk in enumerate(chunks):
            chunked_docs.append(
                Document(id=f"{doc.id}_chunk_{i}", content=text_chunk, metadata=doc.metadata)
            )

    store = EmbeddingStore(collection_name="manual_test_store", embedding_fn=embedder)
    store.add_documents(chunked_docs)

    print(f"\nStored {store.get_collection_size()} documents in EmbeddingStore")
    print("\n=== EmbeddingStore Search Test ===")
    print(f"Query: {query}")
    search_results = store.search(query, top_k=SEARCH_TOP_K)
    for index, result in enumerate(search_results, start=1):
        print(f"{index}. score={result['score']:.3f} source={result['metadata'].get('source')}")
        print(f"   content preview: {result['content'][:120].replace(chr(10), ' ')}...")

    print("\n=== KnowledgeBaseAgent Test ===")
    
    agent = KnowledgeBaseAgent(store=store, llm_fn=real_llm) 
    
    print(f"Question: {query}")
    print(agent.answer(query, top_k=ANSWER_TOP_K))
    return 0


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else None
    return run_manual_demo(question=question)


if __name__ == "__main__":
    raise SystemExit(main())