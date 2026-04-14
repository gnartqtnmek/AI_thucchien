import os
import re
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from index import CHROMA_DB_DIR, get_embedding

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Preset để bật/tắt từng kỹ thuật cho A/B testing.
PIPELINE_PRESETS: Dict[str, Dict[str, Any]] = {
    "baseline_dense": {
        "retrieval_mode": "dense",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": False,
        "use_query_transform": False,
        "query_transform_strategy": "expansion",
    },
    "variant_hybrid": {
        "retrieval_mode": "hybrid",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": False,
        "use_query_transform": False,
        "query_transform_strategy": "expansion",
    },
    "variant_rerank": {
        "retrieval_mode": "dense",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": True,
        "use_query_transform": False,
        "query_transform_strategy": "expansion",
    },
    "variant_query_transform": {
        "retrieval_mode": "dense",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": False,
        "use_query_transform": True,
        "query_transform_strategy": "expansion",
    },
}


def get_pipeline_presets() -> Dict[str, Dict[str, Any]]:
    """Trả về bản copy để Eval Owner có thể chỉnh config mà không sửa hằng số gốc."""
    return {name: config.copy() for name, config in PIPELINE_PRESETS.items()}


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================


@lru_cache(maxsize=1)
def _get_chroma_collection():
    """Lấy collection rag_lab và tái sử dụng trong cùng phiên chạy."""
    try:
        import chromadb
    except ImportError as exc:
        raise ImportError("Chưa cài chromadb. Hãy chạy: pip install chromadb") from exc

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    try:
        return client.get_collection("rag_lab")
    except Exception as exc:
        raise RuntimeError(
            "Không tìm thấy collection 'rag_lab'. Hãy chạy build_index() trong index.py trước."
        ) from exc


def _chunk_key(chunk: Dict[str, Any]) -> str:
    """Sinh key ổn định để merge/deduplicate chunk giữa nhiều chiến lược retrieval."""
    meta = chunk.get("metadata", {}) or {}
    source = str(meta.get("source", ""))
    section = str(meta.get("section", ""))
    text = str(chunk.get("text", ""))
    return f"{source}|{section}|{text[:180]}"


def _dedupe_chunks_by_best_score(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Giữ lại bản ghi có score cao nhất cho mỗi chunk key."""
    merged: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks:
        key = _chunk_key(chunk)
        score = float(chunk.get("score", 0.0) or 0.0)
        if key not in merged or score > float(merged[key].get("score", 0.0) or 0.0):
            merged[key] = chunk

    return sorted(
        merged.values(),
        key=lambda x: float(x.get("score", 0.0) or 0.0),
        reverse=True,
    )


def _tokenize_for_bm25(text: str) -> List[str]:
    """Tokenizer đơn giản cho BM25, giữ được keyword dạng mã lỗi như ERR-403-AUTH."""
    return re.findall(r"[\w-]+", text.lower())


@lru_cache(maxsize=1)
def _load_sparse_index() -> Tuple[List[str], List[Any], Any]:
    """Load toàn bộ chunks từ Chroma và build BM25 index (cache cho nhiều query)."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        raise ImportError("Chưa cài rank-bm25. Hãy chạy: pip install rank-bm25") from exc

    collection = _get_chroma_collection()
    results = collection.get(include=["documents", "metadatas"])
    documents = [str(doc) for doc in (results.get("documents") or [])]
    metadatas = list(results.get("metadatas") or [])

    tokenized_corpus = [_tokenize_for_bm25(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
    return documents, metadatas, bm25

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    
    if top_k <= 0:
        return []

    normalized_query = query.strip()
    if not normalized_query:
        return []

    collection = _get_chroma_collection()

    query_embedding = get_embedding(normalized_query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    retrieved_chunks = []
    for i, text in enumerate(documents):
        metadata = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
        distance = distances[i] if i < len(distances) and distances[i] is not None else 1.0
        score = 1.0 - float(distance)

        retrieved_chunks.append({
            "text": text or "",
            "metadata": metadata,
            "score": score,
        })

    retrieved_chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return retrieved_chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    
    if top_k <= 0:
        return []

    normalized_query = query.strip()
    if not normalized_query:
        return []

    documents, metadatas, bm25 = _load_sparse_index()
    if not documents or bm25 is None:
        return []

    tokenized_query = _tokenize_for_bm25(normalized_query)
    if not tokenized_query:
        return []

    scores = bm25.get_scores(tokenized_query)
    if len(scores) == 0:
        return []

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: float(scores[i]),
        reverse=True,
    )[:top_k]

    top_raw_scores = [float(scores[i]) for i in top_indices]
    max_score = max(top_raw_scores) if top_raw_scores else 0.0

    results: List[Dict[str, Any]] = []
    for idx in top_indices:
        raw_score = float(scores[idx])
        norm_score = (raw_score / max_score) if max_score > 0 else raw_score
        metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}

        results.append({
            "text": documents[idx],
            "metadata": metadata,
            "score": norm_score,
            "sparse_score": raw_score,
        })

    return results


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    
    if top_k <= 0:
        return []

    pool_k = max(top_k * 2, 10)
    rrf_k = int(os.getenv("RRF_K", "60"))

    dense_results = retrieve_dense(query, top_k=pool_k)
    sparse_results = retrieve_sparse(query, top_k=pool_k)

    if not dense_results:
        return sparse_results[:top_k]
    if not sparse_results:
        return dense_results[:top_k]

    fused: Dict[str, Dict[str, Any]] = {}

    for rank, chunk in enumerate(dense_results, 1):
        key = _chunk_key(chunk)
        entry = fused.setdefault(
            key,
            {
                "text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}),
                "score": 0.0,
                "dense_score": 0.0,
                "sparse_score": 0.0,
            },
        )
        entry["score"] += dense_weight * (1.0 / (rrf_k + rank))
        entry["dense_score"] = float(chunk.get("score", 0.0) or 0.0)

    for rank, chunk in enumerate(sparse_results, 1):
        key = _chunk_key(chunk)
        entry = fused.setdefault(
            key,
            {
                "text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}),
                "score": 0.0,
                "dense_score": 0.0,
                "sparse_score": 0.0,
            },
        )
        entry["score"] += sparse_weight * (1.0 / (rrf_k + rank))
        entry["sparse_score"] = float(chunk.get("score", 0.0) or 0.0)

    fused_results = sorted(
        fused.values(),
        key=lambda x: float(x.get("score", 0.0) or 0.0),
        reverse=True,
    )
    return fused_results[:top_k]


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================


@lru_cache(maxsize=1)
def _get_cross_encoder_model():
    """Load cross-encoder một lần để giảm thời gian rerank cho các query sau."""
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise ImportError(
            "Chưa cài sentence-transformers. Hãy chạy: pip install sentence-transformers"
        ) from exc

    model_name = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    return CrossEncoder(model_name)

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    
    if top_k <= 0 or not candidates:
        return []

    try:
        model = _get_cross_encoder_model()
    except Exception as exc:
        # Fallback mềm để pipeline vẫn chạy khi môi trường chưa tải được model rerank.
        print(f"[rerank] Không thể load cross-encoder ({exc}). Fallback top-k mặc định.")
        return candidates[:top_k]

    pairs = [[query, chunk.get("text", "")] for chunk in candidates]
    scores = model.predict(pairs)

    ranked = sorted(
        zip(candidates, scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )

    output: List[Dict[str, Any]] = []
    for chunk, score in ranked[:top_k]:
        reranked_chunk = {
            **chunk,
            "score": float(score),
            "rerank_score": float(score),
        }
        output.append(reranked_chunk)

    return output


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================


def _dedupe_queries(queries: List[str]) -> List[str]:
    """Loại bỏ query trùng lặp nhưng giữ nguyên thứ tự xuất hiện."""
    seen = set()
    output = []
    for q in queries:
        normalized = re.sub(r"\s+", " ", (q or "")).strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        output.append(normalized)
    return output

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    
    base_query = query.strip()
    if not base_query:
        return []

    strategy = strategy.lower().strip()

    if strategy == "expansion":
        expansions = [base_query]
        ql = base_query.lower()

        # Alias map cho domain policy/helpdesk của lab.
        alias_map = {
            "approval matrix": ["access control sop", "phê duyệt cấp quyền", "level 3 approval"],
            "sla": ["service level agreement", "thời gian xử lý ticket"],
            "p1": ["priority 1", "mức ưu tiên p1"],
            "refund": ["hoàn tiền", "chính sách hoàn tiền"],
            "leave": ["nghỉ phép", "chính sách nghỉ phép"],
            "access": ["quyền truy cập", "access control"],
            "helpdesk": ["it helpdesk", "hỗ trợ kỹ thuật"],
        }

        for trigger, variants in alias_map.items():
            if trigger in ql:
                expansions.extend([f"{base_query} {variant}" for variant in variants])

        # Giữ nguyên mã lỗi/mã điều khoản như token riêng.
        code_tokens = re.findall(r"[A-Z]{2,}-?\d+(?:-[A-Z]+)?", base_query)
        expansions.extend(code_tokens)

        return _dedupe_queries(expansions)[:5]

    if strategy == "decomposition":
        parts = re.split(r"\s+(?:và|hoặc)\s+|[,;]", base_query, flags=re.IGNORECASE)
        decomposed = [base_query]
        for part in parts:
            candidate = part.strip(" .?\t\n\r")
            if len(candidate) >= 4:
                decomposed.append(candidate)
        return _dedupe_queries(decomposed)[:5]

    if strategy == "hyde":
        hypothetical = (
            f"Tài liệu chính sách nội bộ trả lời câu hỏi: {base_query}. "
            "Nội dung cần nêu rõ điều khoản, điều kiện áp dụng, thời hạn và nguồn tài liệu."
        )
        return _dedupe_queries([base_query, hypothetical])

    raise ValueError(f"query transform strategy không hợp lệ: {strategy}")


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    
    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    
    client = _get_openai_client()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "512"))

    system_prompt = (
        "Bạn là trợ lý RAG có ràng buộc nghiêm ngặt.\n"
        "BẮT BUỘC tuân thủ cả 2 quy tắc sau:\n"
        "1) Nếu context đủ thông tin, câu trả lời phải có citation dạng [1], [2], ...\n"
        "2) Nếu context không đủ hoặc không chắc chắn, trả lời đúng duy nhất: Không đủ dữ liệu\n"
        "Không được dùng kiến thức bên ngoài context và không được bịa thông tin."
    )

    request_kwargs = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }

    try:
        response = client.chat.completions.create(
            **request_kwargs,
            max_tokens=max_tokens,
        )
    except Exception as e:
        # Một số model mới không hỗ trợ max_tokens và yêu cầu max_completion_tokens.
        if "Unsupported parameter" in str(e) and "max_tokens" in str(e):
            response = client.chat.completions.create(
                **request_kwargs,
                max_completion_tokens=max_tokens,
            )
        else:
            raise

    content = response.choices[0].message.content if response.choices else ""
    answer = (content or "").strip()

    if not answer:
        return "Không đủ dữ liệu"

    if answer == "Không đủ dữ liệu":
        return answer

    # Chấp nhận output có trích dẫn [n]. Nếu không có citation thì ép abstain.
    if re.search(r"\[\d+\]", answer):
        return answer

    if "không đủ dữ liệu" in answer.lower():
        return "Không đủ dữ liệu"

    return "Không đủ dữ liệu"


@lru_cache(maxsize=1)
def _get_openai_client():
    """Khởi tạo OpenAI client một lần để tái sử dụng trong các lần gọi rag_answer."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("Chưa cài package 'openai'. Hãy chạy: pip install openai") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "Thiếu OPENAI_API_KEY trong môi trường. Hãy thêm key vào file .env trước khi gọi rag_answer()."
        )

    return OpenAI(api_key=api_key)


def _retrieve_by_mode(
    query: str,
    retrieval_mode: str,
    top_k: int,
    hybrid_dense_weight: float = 0.6,
    hybrid_sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """Dispatcher retrieval theo mode để tái sử dụng cho query transform và baseline."""
    if retrieval_mode == "dense":
        return retrieve_dense(query, top_k=top_k)
    if retrieval_mode == "sparse":
        return retrieve_sparse(query, top_k=top_k)
    if retrieval_mode == "hybrid":
        return retrieve_hybrid(
            query,
            top_k=top_k,
            dense_weight=hybrid_dense_weight,
            sparse_weight=hybrid_sparse_weight,
        )
    raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")


def rag_answer_with_preset(
    query: str,
    preset_name: str = "baseline_dense",
    overrides: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Chạy pipeline theo preset để bật/tắt kỹ thuật nhanh khi A/B test."""
    presets = get_pipeline_presets()
    if preset_name not in presets:
        raise ValueError(
            f"Preset không tồn tại: {preset_name}. Available: {list(presets.keys())}"
        )

    config = presets[preset_name]
    if overrides:
        config.update(overrides)

    return rag_answer(
        query=query,
        retrieval_mode=config.get("retrieval_mode", "dense"),
        top_k_search=config.get("top_k_search", TOP_K_SEARCH),
        top_k_select=config.get("top_k_select", TOP_K_SELECT),
        use_rerank=config.get("use_rerank", False),
        use_query_transform=config.get("use_query_transform", False),
        query_transform_strategy=config.get("query_transform_strategy", "expansion"),
        verbose=verbose,
    )


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    use_query_transform: bool = False,
    query_transform_strategy: str = "expansion",
    hybrid_dense_weight: float = 0.6,
    hybrid_sparse_weight: float = 0.4,
    verbose: bool = False,
) -> Dict[str, Any]:
    
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "use_query_transform": use_query_transform,
        "query_transform_strategy": query_transform_strategy,
        "hybrid_dense_weight": hybrid_dense_weight,
        "hybrid_sparse_weight": hybrid_sparse_weight,
    }

    if top_k_search <= 0 or top_k_select <= 0:
        return {
            "query": query,
            "query_variants": [query],
            "answer": "Không đủ dữ liệu để trả lời từ tài liệu hiện có.",
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

    # --- Bước 1: Retrieve ---
    transformed_queries = [query]
    if use_query_transform:
        transformed_queries = transform_query(query, strategy=query_transform_strategy) or [query]

    if use_query_transform:
        candidates_all: List[Dict[str, Any]] = []
        per_query_k = max(top_k_search, 8)
        for q_variant in transformed_queries:
            variant_results = _retrieve_by_mode(
                query=q_variant,
                retrieval_mode=retrieval_mode,
                top_k=per_query_k,
                hybrid_dense_weight=hybrid_dense_weight,
                hybrid_sparse_weight=hybrid_sparse_weight,
            )
            for chunk in variant_results:
                enriched_chunk = {**chunk, "query_variant": q_variant}
                candidates_all.append(enriched_chunk)

        candidates = _dedupe_chunks_by_best_score(candidates_all)[:top_k_search]
    else:
        candidates = _retrieve_by_mode(
            query=query,
            retrieval_mode=retrieval_mode,
            top_k=top_k_search,
            hybrid_dense_weight=hybrid_dense_weight,
            hybrid_sparse_weight=hybrid_sparse_weight,
        )

    if verbose:
        print(f"\n[RAG] Query: {query}")
        if use_query_transform:
            print(f"[RAG] Query variants: {transformed_queries}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    if not candidates:
        return {
            "query": query,
            "answer": "Không đủ dữ liệu để trả lời từ tài liệu hiện có.",
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "query_variants": transformed_queries,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    presets_to_compare = [
        "baseline_dense",
        "variant_hybrid",
        "variant_rerank",
        "variant_query_transform",
    ]

    for preset_name in presets_to_compare:
        preset = PIPELINE_PRESETS[preset_name]
        print(f"\n--- Preset: {preset_name} ---")
        print(f"Config: {preset}")
        try:
            result = rag_answer_with_preset(query, preset_name=preset_name, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    ]

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=True)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    # print("\n--- Sprint 3: So sánh strategies ---")
    # compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    # compare_retrieval_strategies("ERR-403-AUTH")

    print("\n\nViệc cần làm Sprint 2:")
    print("  1. Đảm bảo đã chạy build_index() trong index.py")
    print("  2. Thiết lập OPENAI_API_KEY trong .env")
    print("  3. Chạy rag_answer() với 3+ test queries")
    print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    print("\nViệc cần làm Sprint 3:")
    print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    print("  2. Implement variant đó")
    print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")

    print("\nPreset configs sẵn sàng cho Eval Owner:")
    for preset_name, preset_cfg in get_pipeline_presets().items():
        print(f"  - {preset_name}: {preset_cfg}")
