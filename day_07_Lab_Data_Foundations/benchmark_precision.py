from __future__ import annotations

import argparse
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from dotenv import load_dotenv

from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
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

DEFAULT_SAMPLE_FILES = [
    "data/co-quan-quan-ly-se-giam-sat-gia-dich-vu-starlink-tai-viet-nam.txt",
    "data/cuoc-dau-cua-hai-cong-cu-ai-tai-cong-so-trung-quoc.txt",
    "data/doi_moi_sang_tao_khoi_nghiep.txt",
    "data/nen-tang-ho-tro-tim-nha-thau.txt",
    "data/phi-hanh-doan-artemis-ii-vuot-nua-duong-ve-trai-dat.txt",
    "data/phong-thanh-cong-ve-tinh-tu-nhan.txt",
    "data/vn-thi-diem-doanh-nghiep-mot-nguoi.txt",
    "data/vu_tru_co_my.txt",
]

TOPIC_BY_BASENAME = {
    "co-quan-quan-ly-se-giam-sat-gia-dich-vu-starlink-tai-viet-nam.txt": "vien-thong",
    "cuoc-dau-cua-hai-cong-cu-ai-tai-cong-so-trung-quoc.txt": "ai",
    "doi_moi_sang_tao_khoi_nghiep.txt": "khoi-nghiep",
    "nen-tang-ho-tro-tim-nha-thau.txt": "xay-dung",
    "phi-hanh-doan-artemis-ii-vuot-nua-duong-ve-trai-dat.txt": "vu-tru",
    "phong-thanh-cong-ve-tinh-tu-nhan.txt": "vu-tru",
    "vn-thi-diem-doanh-nghiep-mot-nguoi.txt": "khoi-nghiep",
    "vu_tru_co_my.txt": "vu-tru",
}

KEYWORD_OVERRIDES = {
    "Q1": ("600.000", "85 usd", "2,2 triệu", "435 usd"),
    "Q2": ("thanh kim loại", "vươn ra", "rủ xuống", "gợn sóng"),
    "Q3": ("colleague.skill", "anti-distillation", "ai agent"),
    "Q4": ("falcon 9", "transporter-16", "vandenberg", "spacex", "slovenia"),
    "Q5": ("10.000", "300", "10%", "10 tỷ", "doanh nghiệp một người"),
}


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    question: str
    expected_sources: tuple[str, ...]
    relevance_keywords: tuple[str, ...]
    min_keyword_hits: int = 1
    metadata_filter: dict[str, str] | None = None
    required_source_count: int = 1


DEFAULT_BENCHMARK_CASES = [
    BenchmarkCase(
        case_id="Q1",
        question=(
            "Số lượng thuê bao Starlink tối đa được phép tại Việt Nam là bao nhiêu "
            "và mức phí duy trì hàng tháng là bao nhiêu?"
        ),
        expected_sources=("data/co-quan-quan-ly-se-giam-sat-gia-dich-vu-starlink-tai-viet-nam.txt",),
        relevance_keywords=("600.000", "85 usd", "2,2 triệu"),
    ),
    BenchmarkCase(
        case_id="Q2",
        question=(
            "Kỹ sư NASA đã thiết kế lá cờ Mỹ như thế nào để nó trông như đang bay "
            "trên Mặt Trăng dù không có gió?"
        ),
        expected_sources=("data/vu_tru_co_my.txt",),
        relevance_keywords=("thanh kim loại", "vươn ra", "gợn sóng"),
    ),
    BenchmarkCase(
        case_id="Q3",
        question=(
            "Công cụ colleague.skill và anti-distillation skill ở Trung Quốc hoạt động "
            "như thế nào và đối lập ra sao?"
        ),
        expected_sources=("data/cuoc-dau-cua-hai-cong-cu-ai-tai-cong-so-trung-quoc.txt",),
        relevance_keywords=("titanwings",),
    ),
    BenchmarkCase(
        case_id="Q4",
        question=(
            "Trong các tin tức về vũ trụ và không gian, VEGAFLY-1 được phóng bằng phương tiện gì, "
            "từ đâu và ai vận hành sứ mệnh?"
        ),
        expected_sources=("data/phong-thanh-cong-ve-tinh-tu-nhan.txt",),
        relevance_keywords=("falcon 9", "transporter-16", "vandenberg"),
        metadata_filter={"topic": "vu-tru"},
    ),
    BenchmarkCase(
        case_id="Q5",
        question=(
            "Việt Nam có những chính sách và mục tiêu cụ thể gì để hỗ trợ khởi nghiệp "
            "sáng tạo đến năm 2030 và 2045?"
        ),
        expected_sources=(
            "data/doi_moi_sang_tao_khoi_nghiep.txt",
            "data/vn-thi-diem-doanh-nghiep-mot-nguoi.txt",
        ),
        relevance_keywords=("10.000", "300", "10%", "10 tỷ", "doanh nghiệp một người"),
        required_source_count=2,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Precision@k for chunking strategies.")
    parser.add_argument("--top-k", type=int, default=3, help="Compute Precision@k with this k value.")
    parser.add_argument(
        "--provider",
        choices=["auto", "mock", "local", "openai"],
        default="auto",
        help="Embedding provider. 'auto' reads EMBEDDING_PROVIDER from env.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional markdown output path, e.g. report/precision_benchmark.md",
    )
    parser.add_argument(
        "--cases-file",
        default="question.txt",
        help="Path to a benchmark query spec text file. Defaults to question.txt.",
    )
    return parser.parse_args()


def load_documents(file_paths: list[str]) -> list[Document]:
    docs: list[Document] = []
    for raw_path in file_paths:
        path = Path(raw_path)
        if not path.exists() or not path.is_file() or path.suffix.lower() not in {".txt", ".md"}:
            continue
        docs.append(
            Document(
                id=path.stem,
                content=path.read_text(encoding="utf-8"),
                metadata={
                    "source": str(path).replace("\\", "/"),
                    "topic": TOPIC_BY_BASENAME.get(path.name, "general"),
                },
            )
        )
    return docs


def choose_embedder(provider_arg: str):
    load_dotenv(override=False)
    provider = provider_arg
    if provider == "auto":
        provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()

    if provider == "local":
        try:
            return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            return _mock_embed

    if provider == "openai":
        try:
            return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            return _mock_embed

    return _mock_embed


def build_chunked_documents(documents: list[Document], strategy_name: str) -> list[Document]:
    if strategy_name == "fixed_size":
        chunker = FixedSizeChunker(chunk_size=380, overlap=80)
    elif strategy_name == "sentence":
        chunker = SentenceChunker(max_sentences_per_chunk=2)
    elif strategy_name == "recursive":
        chunker = RecursiveChunker(chunk_size=420)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    chunked_docs: list[Document] = []
    for doc in documents:
        chunks = chunker.chunk(doc.content)
        for index, chunk_text in enumerate(chunks):
            metadata = doc.metadata.copy()
            metadata["doc_id"] = doc.id
            metadata["chunk_index"] = index
            metadata["chunker"] = strategy_name
            chunked_docs.append(
                Document(
                    id=f"{doc.id}_chunk_{index}",
                    content=chunk_text,
                    metadata=metadata,
                )
            )

    return chunked_docs


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def normalize_match_text(value: str) -> str:
    lowered = value.lower().strip()
    without_accents = (
        unicodedata.normalize("NFKD", lowered).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()


def overlap_score(text_a: str, text_b: str) -> int:
    tokens_a = set(token for token in text_a.split() if token)
    tokens_b = set(token for token in text_b.split() if token)
    return len(tokens_a & tokens_b)


def resolve_source_hint(hint: str, available_sources: list[str]) -> str:
    hint_match = normalize_match_text(hint)
    if not hint_match:
        return ""

    best_source = ""
    best_score = 0
    for source in available_sources:
        source_match = normalize_match_text(source)
        basename_match = normalize_match_text(Path(source).name)

        if hint_match in source_match or hint_match in basename_match:
            return source
        if basename_match in hint_match:
            return source

        current_score = max(overlap_score(hint_match, source_match), overlap_score(hint_match, basename_match))
        if current_score > best_score:
            best_score = current_score
            best_source = source

    return best_source if best_score >= 2 else ""


def extract_source_hints(raw_source_text: str) -> list[str]:
    cleaned = re.sub(r"\([^)]*\)", " ", raw_source_text)
    parts = re.split(r"\+|,|\bvà\b", cleaned, flags=re.IGNORECASE)
    hints: list[str] = []
    for part in parts:
        candidate = part.strip(" .;-\t")
        if not candidate:
            continue
        if ".txt" not in candidate.lower() and ".md" not in candidate.lower():
            continue
        hints.append(candidate)
    return hints


def extract_keywords_from_gold(gold_text: str) -> tuple[str, ...]:
    quoted = re.findall(r'"([^"]+)"', gold_text)
    numeric = re.findall(
        r"\d[\d\.,]*\s*(?:usd|triệu|tỷ|%|m|h\d{2}|gii|kỳ lân|falcon|transporter)?",
        gold_text.lower(),
    )

    candidates: list[str] = []
    for value in quoted + numeric:
        cleaned = " ".join(value.split())
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    return tuple(candidates[:8])


def parse_metadata_filter(filter_text: str) -> dict[str, str] | None:
    if not filter_text:
        return None

    normalized = normalize_match_text(filter_text)
    if "vu tru" in normalized or "space" in normalized:
        return {"topic": "vu-tru"}

    return None


def parse_cases_file(cases_file: str, available_sources: list[str]) -> list[BenchmarkCase]:
    path = Path(cases_file)
    if not path.exists() or not path.is_file():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    cases: list[BenchmarkCase] = []
    index = 0

    while index < len(lines):
        match = re.match(r"QUERY\s+(\d+)", lines[index].strip(), flags=re.IGNORECASE)
        if not match:
            index += 1
            continue

        case_id = f"Q{int(match.group(1))}"
        question_lines: list[str] = []
        gold_lines: list[str] = []
        source_lines: list[str] = []
        filter_lines: list[str] = []

        section = ""
        index += 1
        while index < len(lines):
            stripped = lines[index].strip()
            if re.match(r"QUERY\s+\d+", stripped, flags=re.IGNORECASE):
                break
            if stripped.startswith("BẢNG TÓM TẮT") or stripped.startswith("GHI CHÚ KHI CHẠY BENCHMARK"):
                break

            if stripped.startswith("Câu hỏi:"):
                section = "question"
                index += 1
                continue
            if stripped.startswith("Gold Answer:"):
                section = "gold"
                index += 1
                continue
            if stripped.startswith("Nguồn chunk:"):
                section = "source"
                index += 1
                continue
            if stripped.startswith("Metadata filter gợi ý:"):
                section = "filter"
                index += 1
                continue
            if stripped.startswith("Lý do chọn câu này:"):
                section = ""
                index += 1
                continue

            if stripped:
                if section == "question":
                    question_lines.append(stripped)
                elif section == "gold":
                    gold_lines.append(stripped)
                elif section == "source":
                    source_lines.append(stripped)
                elif section == "filter":
                    filter_lines.append(stripped)

            index += 1

        question = " ".join(question_lines)
        gold_answer = " ".join(gold_lines)
        source_hints = extract_source_hints(" ".join(source_lines))
        resolved_sources = [
            resolve_source_hint(hint, available_sources)
            for hint in source_hints
        ]
        expected_sources = tuple(source for source in resolved_sources if source)

        if not question:
            continue

        default_keywords = extract_keywords_from_gold(gold_answer)
        relevance_keywords = KEYWORD_OVERRIDES.get(case_id, default_keywords)

        metadata_filter = parse_metadata_filter(" ".join(filter_lines))
        required_source_count = max(1, len(expected_sources))

        cases.append(
            BenchmarkCase(
                case_id=case_id,
                question=question,
                expected_sources=expected_sources,
                relevance_keywords=relevance_keywords,
                metadata_filter=metadata_filter,
                required_source_count=required_source_count,
            )
        )

    return cases


def tokenize(value: str) -> set[str]:
    return set(re.findall(r"\d+[\d\.,]*|[\wÀ-ỹà-ỹ]+", value.lower(), flags=re.UNICODE))


def rank_hits_for_query(
    store: EmbeddingStore,
    query: str,
    top_k: int,
    metadata_filter: dict[str, str] | None = None,
) -> list[dict]:
    # Pull all chunks then rerank with lexical overlap so benchmark remains useful with mock embeddings.
    if metadata_filter:
        all_hits = store.search_with_filter(
            query,
            top_k=store.get_collection_size(),
            metadata_filter=metadata_filter,
        )
    else:
        all_hits = store.search(query, top_k=store.get_collection_size())

    query_tokens = tokenize(query)
    expects_number = any(
        cue in query.lower() for cue in ["bao nhiêu", "mức", "giá", "số", "how many", "price", "cost"]
    )

    rescored: list[dict] = []
    for hit in all_hits:
        content = str(hit.get("content", ""))
        content_tokens = tokenize(content)
        lexical_score = len(query_tokens & content_tokens) / max(1, len(query_tokens))
        semantic_score = float(hit.get("score", 0.0))

        number_bonus = 0.0
        if expects_number and re.search(r"\d", content):
            number_bonus += 0.05

        hybrid_score = 0.30 * semantic_score + 0.70 * lexical_score + number_bonus
        new_hit = hit.copy()
        new_hit["hybrid_score"] = hybrid_score
        rescored.append(new_hit)

    rescored.sort(key=lambda item: item["hybrid_score"], reverse=True)
    return rescored[:top_k]


def match_expected_source(case: BenchmarkCase, hit: dict) -> str:
    if not case.expected_sources:
        return ""

    source = str(hit.get("metadata", {}).get("source", "")).replace("\\", "/")
    source_match = normalize_match_text(source)
    basename_match = normalize_match_text(Path(source).name)

    for expected in case.expected_sources:
        expected_match = normalize_match_text(expected)
        expected_basename = normalize_match_text(Path(expected).name)
        if expected_match in source_match or expected_basename in basename_match:
            return expected

    return ""


def is_relevant_hit(case: BenchmarkCase, hit: dict) -> bool:
    if case.expected_sources and not match_expected_source(case, hit):
        return False

    if not case.relevance_keywords:
        return True

    content = normalize_text(str(hit.get("content", "")))
    keyword_hits = sum(1 for keyword in case.relevance_keywords if normalize_text(keyword) in content)
    return keyword_hits >= case.min_keyword_hits


def evaluate_strategy(
    strategy_name: str,
    base_docs: list[Document],
    embedding_fn,
    top_k: int,
    cases: list[BenchmarkCase],
) -> dict:
    chunked_docs = build_chunked_documents(base_docs, strategy_name)
    store = EmbeddingStore(collection_name=f"benchmark_{strategy_name}", embedding_fn=embedding_fn)
    store.add_documents(chunked_docs)

    case_rows = []
    for case in cases:
        hits = rank_hits_for_query(
            store,
            case.question,
            top_k=top_k,
            metadata_filter=case.metadata_filter,
        )
        relevant_hits = [hit for hit in hits if is_relevant_hit(case, hit)]
        matched_sources = {
            matched
            for hit in relevant_hits
            for matched in [match_expected_source(case, hit)]
            if matched
        }

        base_precision = len(relevant_hits) / float(top_k)
        coverage_ratio = min(1.0, len(matched_sources) / float(case.required_source_count))
        precision_at_k = base_precision * coverage_ratio

        case_rows.append(
            {
                "case_id": case.case_id,
                "question": case.question,
                "precision": precision_at_k,
                "relevant_hits": len(relevant_hits),
                "top_k": top_k,
                "source_coverage": len(matched_sources),
                "required_source_count": case.required_source_count,
            }
        )

    avg_precision = mean(row["precision"] for row in case_rows)
    hit_rate = mean(1.0 if row["relevant_hits"] > 0 else 0.0 for row in case_rows)
    avg_source_coverage = mean(
        min(1.0, row["source_coverage"] / float(row["required_source_count"])) for row in case_rows
    )

    return {
        "strategy": strategy_name,
        "total_chunks": len(chunked_docs),
        "avg_precision": avg_precision,
        "hit_rate": hit_rate,
        "avg_source_coverage": avg_source_coverage,
        "cases": case_rows,
    }


def render_console(results: list[dict[str, Any]], top_k: int, cases: list[BenchmarkCase]) -> None:
    print("=" * 78)
    print(f"Precision@{top_k} benchmark for {len(cases)} standard queries")
    print("=" * 78)

    for result in results:
        print(
            f"- {result['strategy']}: avg_precision={result['avg_precision']:.3f} "
            f"hit_rate={result['hit_rate']:.3f} "
            f"source_coverage={result['avg_source_coverage']:.3f} "
            f"total_chunks={result['total_chunks']}"
        )
        for row in result["cases"]:
            print(
                f"  {row['case_id']}: precision={row['precision']:.3f} "
                f"({row['relevant_hits']}/{row['top_k']}), "
                f"source_coverage={row['source_coverage']}/{row['required_source_count']}"
            )

    best = max(
        results,
        key=lambda item: (
            item["avg_precision"],
            item["avg_source_coverage"],
            item["hit_rate"],
            -item["total_chunks"],
        ),
    )
    print("-" * 78)
    print(
        f"Best strategy: {best['strategy']} "
        f"(avg_precision={best['avg_precision']:.3f}, "
        f"source_coverage={best['avg_source_coverage']:.3f}, "
        f"hit_rate={best['hit_rate']:.3f})"
    )


def build_markdown(results: list[dict[str, Any]], top_k: int, cases: list[BenchmarkCase]) -> str:
    headers = ["Strategy", f"Avg Precision@{top_k}", "Hit Rate", "Total Chunks"] + [
        case.case_id for case in cases
    ]

    lines = [
        "# Precision@k Benchmark",
        "",
        f"- k: **{top_k}**",
        f"- Number of benchmark queries: **{len(cases)}**",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for result in results:
        per_case = {row["case_id"]: row["precision"] for row in result["cases"]}
        row_values = [
            result["strategy"],
            f"{result['avg_precision']:.3f}",
            f"{result['hit_rate']:.3f}",
            str(result["total_chunks"]),
        ] + [f"{per_case.get(case.case_id, 0.0):.3f}" for case in cases]
        lines.append("| " + " | ".join(row_values) + " |")

    best = max(
        results,
        key=lambda item: (
            item["avg_precision"],
            item["avg_source_coverage"],
            item["hit_rate"],
            -item["total_chunks"],
        ),
    )
    lines.extend(
        [
            "",
            f"**Best strategy:** {best['strategy']} "
            f"(Avg Precision@{top_k} = {best['avg_precision']:.3f}, "
            f"Source Coverage = {best['avg_source_coverage']:.3f}, "
            f"Hit Rate = {best['hit_rate']:.3f})",
        ]
    )

    return "\n".join(lines)


def load_benchmark_cases(cases_file: str, available_sources: list[str]) -> list[BenchmarkCase]:
    parsed_cases = parse_cases_file(cases_file, available_sources)
    if parsed_cases:
        return parsed_cases
    return DEFAULT_BENCHMARK_CASES


def main() -> int:
    args = parse_args()
    if args.top_k <= 0:
        raise ValueError("--top-k must be greater than 0")

    documents = load_documents(DEFAULT_SAMPLE_FILES)
    if not documents:
        print("No valid documents loaded from DEFAULT_SAMPLE_FILES. Check data paths.")
        return 1

    available_sources = [str(doc.metadata.get("source", "")) for doc in documents]
    benchmark_cases = load_benchmark_cases(args.cases_file, available_sources)
    if not benchmark_cases:
        print("No benchmark cases available.")
        return 1

    embedding_fn = choose_embedder(args.provider)
    backend_name = getattr(embedding_fn, "_backend_name", embedding_fn.__class__.__name__)
    print(f"Embedding backend: {backend_name}")
    print(f"Loaded benchmark cases: {len(benchmark_cases)}")

    strategy_names = ["fixed_size", "sentence", "recursive"]
    results = [
        evaluate_strategy(strategy_name, documents, embedding_fn, args.top_k, benchmark_cases)
        for strategy_name in strategy_names
    ]
    results.sort(
        key=lambda item: (
            item["avg_precision"],
            item["avg_source_coverage"],
            item["hit_rate"],
            -item["total_chunks"],
        ),
        reverse=True,
    )

    render_console(results, args.top_k, benchmark_cases)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_markdown(results, args.top_k, benchmark_cases), encoding="utf-8")
        print(f"Markdown report written to: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
