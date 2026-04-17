import os
import json
import csv
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Optional, cast
from datetime import datetime
from rag_answer import rag_answer, rag_answer_with_preset, get_pipeline_presets

# =============================================================================
# CẤU HÌNH
# =============================================================================

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"
AVAILABLE_PRESETS = get_pipeline_presets()

JUDGE_MODEL = os.getenv("JUDGE_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))
JUDGE_MAX_TOKENS = int(os.getenv("JUDGE_MAX_TOKENS", "300"))

# Cấu hình baseline (Sprint 2)
BASELINE_CONFIG = {
    "preset_name": "baseline_dense",
    "label": "baseline_dense",
}

VARIANT_CONFIG = {
    "preset_name": "variant_hybrid",
    "label": "variant_hybrid",
}


def _resolve_eval_config(config: Dict[str, Any]) -> Dict[str, Any]:
    
    resolved = dict(config or {})
    preset_name = resolved.get("preset_name")

    if not preset_name:
        return resolved

    presets = get_pipeline_presets()
    if preset_name not in presets:
        raise ValueError(
            f"Preset không tồn tại: {preset_name}. Available: {list(presets.keys())}"
        )

    preset_cfg = presets[preset_name].copy()
    override_cfg = {
        k: v
        for k, v in resolved.items()
        if k not in ("preset_name", "label")
    }
    merged = {
        **preset_cfg,
        **override_cfg,
        "preset_name": preset_name,
        "label": resolved.get("label", preset_name),
    }
    return merged


@lru_cache(maxsize=1)
def _get_judge_client():
    """Khởi tạo OpenAI client cho LLM-as-Judge (cache để tái sử dụng)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Thiếu OPENAI_API_KEY. Không thể chạy LLM-as-Judge.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("Chưa cài openai. Hãy chạy: pip install openai") from exc

    return OpenAI(api_key=api_key)


def _truncate_text(text: str, max_chars: int = 1200) -> str:
    """Giới hạn độ dài text để prompt judge ổn định và tiết kiệm token."""
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars] + "..."


def _build_judge_context(chunks_used: List[Dict[str, Any]], max_chunks: int = 5) -> str:
    """Build context rút gọn từ chunks để đưa vào judge prompt."""
    if not chunks_used:
        return "(no retrieved chunks)"

    parts = []
    for i, chunk in enumerate(chunks_used[:max_chunks], 1):
        meta = chunk.get("metadata", {}) or {}
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        text = _truncate_text(str(chunk.get("text", "")), max_chars=350)
        parts.append(f"[{i}] source={source} | section={section}\n{text}")
    return "\n\n".join(parts)


def _safe_score(score_value: Any) -> Optional[int]:
    """Chuẩn hóa score về int 1..5, hoặc None nếu parse không hợp lệ."""
    try:
        score = int(score_value)
    except (TypeError, ValueError):
        return None

    if score < 1:
        return 1
    if score > 5:
        return 5
    return score


def _judge_with_llm(task: str, payload: str) -> Dict[str, Any]:
    """Gọi LLM để chấm điểm, bắt buộc trả JSON {score, reason}."""
    try:
        client = _get_judge_client()
    except Exception as e:
        return {"score": None, "notes": f"LLM judge unavailable: {e}"}

    system_prompt = (
        "You are an evaluation judge for RAG outputs. "
        "Return ONLY valid JSON with keys: score (integer 1-5) and reason (short text)."
    )

    user_prompt = (
        f"Task: {task}\n"
        "Scoring scale: 1 (worst) to 5 (best).\n"
        "Output strictly JSON: {\"score\": <1-5>, \"reason\": \"...\"}.\n\n"
        f"Data:\n{payload}"
    )

    request_kwargs = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }

    try:
        try:
            response = client.chat.completions.create(
                **request_kwargs,
                max_tokens=JUDGE_MAX_TOKENS,
            )
        except Exception as e:
            if "Unsupported parameter" in str(e) and "max_tokens" in str(e):
                response = client.chat.completions.create(
                    **request_kwargs,
                    max_completion_tokens=JUDGE_MAX_TOKENS,
                )
            else:
                raise

        content = response.choices[0].message.content if response.choices else "{}"
        data = json.loads(content or "{}")
        score = _safe_score(data.get("score"))
        reason = str(data.get("reason") or data.get("notes") or "")

        if score is None:
            return {"score": None, "notes": f"LLM judge parse error: {content}"}

        return {"score": score, "notes": _truncate_text(reason, max_chars=240)}

    except Exception as e:
        return {"score": None, "notes": f"LLM judge error: {e}"}


# =============================================================================
# SCORING FUNCTIONS
# 4 metrics từ slide: Faithfulness, Answer Relevance, Context Recall, Completeness
# =============================================================================

def score_faithfulness(
    answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Any]:
    
    normalized_answer = (answer or "").strip()

    if normalized_answer.startswith("ERROR:"):
        return {"score": 1, "notes": "Pipeline error output"}

    if normalized_answer == "PIPELINE_NOT_IMPLEMENTED":
        return {"score": 1, "notes": "Pipeline not implemented"}

    if not chunks_used and "không đủ dữ liệu" in normalized_answer.lower():
        return {"score": 5, "notes": "Abstain correctly with empty context"}

    context_text = _build_judge_context(chunks_used)
    payload = (
        f"Retrieved Context:\n{context_text}\n\n"
        f"Answer:\n{_truncate_text(normalized_answer, max_chars=900)}\n\n"
        "Question: Is the answer fully grounded in the retrieved context only?"
    )
    return _judge_with_llm("Faithfulness", payload)


def score_answer_relevance(
    query: str,
    answer: str,
) -> Dict[str, Any]:
    
    normalized_answer = (answer or "").strip()

    if normalized_answer.startswith("ERROR:"):
        return {"score": 1, "notes": "Pipeline error output"}

    if normalized_answer == "PIPELINE_NOT_IMPLEMENTED":
        return {"score": 1, "notes": "Pipeline not implemented"}

    payload = (
        f"User Question:\n{_truncate_text(query, max_chars=500)}\n\n"
        f"Model Answer:\n{_truncate_text(normalized_answer, max_chars=900)}\n\n"
        "Question: How directly and correctly does the answer address the user's question?"
    )
    return _judge_with_llm("Answer Relevance", payload)


def score_context_recall(
    chunks_used: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Dict[str, Any]:
    
    if not expected_sources:
        # Câu hỏi không có expected source (ví dụ: "Không đủ dữ liệu" cases)
        return {"score": None, "recall": None, "notes": "No expected sources"}

    retrieved_sources = {
        c.get("metadata", {}).get("source", "")
        for c in chunks_used
    }

    found = 0
    missing = []
    for expected in expected_sources:
        # Kiểm tra partial match (tên file)
        expected_name = expected.split("/")[-1].replace(".pdf", "").replace(".md", "")
        matched = any(expected_name.lower() in r.lower() for r in retrieved_sources)
        if matched:
            found += 1
        else:
            missing.append(expected)

    recall = found / len(expected_sources) if expected_sources else 0

    return {
        "score": round(recall * 5),  # Convert to 1-5 scale
        "recall": recall,
        "found": found,
        "missing": missing,
        "notes": f"Retrieved: {found}/{len(expected_sources)} expected sources" +
                 (f". Missing: {missing}" if missing else ""),
    }


def score_completeness(
    query: str,
    answer: str,
    expected_answer: str,
) -> Dict[str, Any]:
    
    normalized_answer = (answer or "").strip()
    normalized_expected = (expected_answer or "").strip()

    if not normalized_expected:
        return {"score": None, "notes": "No expected answer for completeness scoring"}

    if normalized_answer.startswith("ERROR:"):
        return {"score": 1, "notes": "Pipeline error output"}

    if normalized_answer == "PIPELINE_NOT_IMPLEMENTED":
        return {"score": 1, "notes": "Pipeline not implemented"}

    payload = (
        f"User Question:\n{_truncate_text(query, max_chars=400)}\n\n"
        f"Expected Answer (reference):\n{_truncate_text(normalized_expected, max_chars=900)}\n\n"
        f"Model Answer:\n{_truncate_text(normalized_answer, max_chars=900)}\n\n"
        "Question: Compared to the expected answer, how complete is the model answer?"
    )
    return _judge_with_llm("Completeness", payload)


# =============================================================================
# SCORECARD RUNNER
# =============================================================================

def run_scorecard(
    config: Dict[str, Any],
    test_questions: Optional[List[Dict]] = None,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    
    if test_questions is None:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)

    questions = cast(List[Dict[str, Any]], test_questions or [])

    resolved_config = _resolve_eval_config(config)
    results = []
    label = resolved_config.get("label", "unnamed")

    print(f"\n{'='*70}")
    print(f"Chạy scorecard: {label}")
    print(f"Config: {resolved_config}")
    print('='*70)

    for q in questions:
        question_id = q["id"]
        query = q["question"]
        expected_answer = q.get("expected_answer", "")
        expected_sources = q.get("expected_sources", [])
        category = q.get("category", "")

        if verbose:
            print(f"\n[{question_id}] {query}")

        # --- Gọi pipeline ---
        try:
            preset_name = resolved_config.get("preset_name")
            if preset_name:
                overrides = {
                    k: v
                    for k, v in resolved_config.items()
                    if k not in ("preset_name", "label")
                }
                result = rag_answer_with_preset(
                    query=query,
                    preset_name=preset_name,
                    overrides=overrides,
                    verbose=False,
                )
            else:
                result = rag_answer(
                    query=query,
                    retrieval_mode=resolved_config.get("retrieval_mode", "dense"),
                    top_k_search=resolved_config.get("top_k_search", 10),
                    top_k_select=resolved_config.get("top_k_select", 3),
                    use_rerank=resolved_config.get("use_rerank", False),
                    use_query_transform=resolved_config.get("use_query_transform", False),
                    query_transform_strategy=resolved_config.get("query_transform_strategy", "expansion"),
                    hybrid_dense_weight=resolved_config.get("hybrid_dense_weight", 0.6),
                    hybrid_sparse_weight=resolved_config.get("hybrid_sparse_weight", 0.4),
                    verbose=False,
                )

            answer = result["answer"]
            chunks_used = result["chunks_used"]

        except NotImplementedError:
            answer = "PIPELINE_NOT_IMPLEMENTED"
            chunks_used = []
        except Exception as e:
            answer = f"ERROR: {e}"
            chunks_used = []

        # --- Chấm điểm ---
        faith = score_faithfulness(answer, chunks_used)
        relevance = score_answer_relevance(query, answer)
        recall = score_context_recall(chunks_used, expected_sources)
        complete = score_completeness(query, answer, expected_answer)

        row = {
            "id": question_id,
            "category": category,
            "query": query,
            "answer": answer,
            "expected_answer": expected_answer,
            "faithfulness": faith["score"],
            "faithfulness_notes": faith["notes"],
            "relevance": relevance["score"],
            "relevance_notes": relevance["notes"],
            "context_recall": recall["score"],
            "context_recall_notes": recall["notes"],
            "completeness": complete["score"],
            "completeness_notes": complete["notes"],
            "config_label": label,
        }
        results.append(row)

        if verbose:
            print(f"  Answer: {answer[:100]}...")
            print(f"  Faithful: {faith['score']} | Relevant: {relevance['score']} | "
                  f"Recall: {recall['score']} | Complete: {complete['score']}")

    # Tính averages (bỏ qua None)
    for metric in ["faithfulness", "relevance", "context_recall", "completeness"]:
        scores = [r[metric] for r in results if r[metric] is not None]
        avg = sum(scores) / len(scores) if scores else None
        print(f"\nAverage {metric}: {avg:.2f}" if avg else f"\nAverage {metric}: N/A (chưa chấm)")

    return results


# =============================================================================
# A/B COMPARISON
# =============================================================================

def compare_ab(
    baseline_results: List[Dict],
    variant_results: List[Dict],
    output_csv: Optional[str] = None,
) -> None:
    
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]

    print(f"\n{'='*70}")
    print("A/B Comparison: Baseline vs Variant")
    print('='*70)
    print(f"{'Metric':<20} {'Baseline':>10} {'Variant':>10} {'Delta':>8}")
    print("-" * 55)

    for metric in metrics:
        b_scores = [r[metric] for r in baseline_results if r[metric] is not None]
        v_scores = [r[metric] for r in variant_results if r[metric] is not None]

        b_avg = sum(b_scores) / len(b_scores) if b_scores else None
        v_avg = sum(v_scores) / len(v_scores) if v_scores else None
        delta = (v_avg - b_avg) if (b_avg and v_avg) else None

        b_str = f"{b_avg:.2f}" if b_avg else "N/A"
        v_str = f"{v_avg:.2f}" if v_avg else "N/A"
        d_str = f"{delta:+.2f}" if delta else "N/A"

        print(f"{metric:<20} {b_str:>10} {v_str:>10} {d_str:>8}")

    # Per-question comparison
    print(f"\n{'Câu':<6} {'Baseline F/R/Rc/C':<22} {'Variant F/R/Rc/C':<22} {'Better?':<10}")
    print("-" * 65)

    b_by_id = {r["id"]: r for r in baseline_results}
    for v_row in variant_results:
        qid = v_row["id"]
        b_row = b_by_id.get(qid, {})

        b_scores_str = "/".join([
            str(b_row.get(m, "?")) for m in metrics
        ])
        v_scores_str = "/".join([
            str(v_row.get(m, "?")) for m in metrics
        ])

        # So sánh đơn giản
        b_total = sum(b_row.get(m, 0) or 0 for m in metrics)
        v_total = sum(v_row.get(m, 0) or 0 for m in metrics)
        better = "Variant" if v_total > b_total else ("Baseline" if b_total > v_total else "Tie")

        print(f"{qid:<6} {b_scores_str:<22} {v_scores_str:<22} {better:<10}")

    # Export to CSV
    if output_csv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = RESULTS_DIR / output_csv
        combined = baseline_results + variant_results
        if combined:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=combined[0].keys())
                writer.writeheader()
                writer.writerows(combined)
            print(f"\nKết quả đã lưu vào: {csv_path}")


# =============================================================================
# REPORT GENERATOR
# =============================================================================

def generate_scorecard_summary(results: List[Dict], label: str) -> str:
    
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
    averages = {}
    for metric in metrics:
        scores = [r[metric] for r in results if r[metric] is not None]
        averages[metric] = sum(scores) / len(scores) if scores else None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"""# Scorecard: {label}
Generated: {timestamp}

## Summary

| Metric | Average Score |
|--------|--------------|
"""
    for metric, avg in averages.items():
        avg_str = f"{avg:.2f}/5" if avg else "N/A"
        md += f"| {metric.replace('_', ' ').title()} | {avg_str} |\n"

    md += "\n## Per-Question Results\n\n"
    md += "| ID | Category | Faithful | Relevant | Recall | Complete | Notes |\n"
    md += "|----|----------|----------|----------|--------|----------|-------|\n"

    for r in results:
        md += (f"| {r['id']} | {r['category']} | {r.get('faithfulness', 'N/A')} | "
               f"{r.get('relevance', 'N/A')} | {r.get('context_recall', 'N/A')} | "
               f"{r.get('completeness', 'N/A')} | {r.get('faithfulness_notes', '')[:50]} |\n")

    return md


# =============================================================================
# MAIN — Chạy evaluation
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)
    print(f"Preset khả dụng từ rag_answer: {list(AVAILABLE_PRESETS.keys())}")

    # Kiểm tra test questions
    print(f"\nLoading test questions từ: {TEST_QUESTIONS_PATH}")
    try:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)
        print(f"Tìm thấy {len(test_questions)} câu hỏi")

        # In preview
        for q in test_questions[:3]:
            print(f"  [{q['id']}] {q['question']} ({q['category']})")
        print("  ...")

    except FileNotFoundError:
        print("Không tìm thấy file test_questions.json!")
        test_questions = []

    # --- Chạy Baseline ---
    print("\n--- Chạy Baseline ---")
    print("Lưu ý: Cần hoàn thành Sprint 2 trước khi chạy scorecard!")
    try:
        baseline_results = run_scorecard(
            config=BASELINE_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )

        # Save scorecard
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        baseline_md = generate_scorecard_summary(baseline_results, "baseline_dense")
        scorecard_path = RESULTS_DIR / "scorecard_baseline.md"
        scorecard_path.write_text(baseline_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {scorecard_path}")

    except NotImplementedError:
        print("Pipeline chưa implement. Hoàn thành Sprint 2 trước.")
        baseline_results = []

    # --- Chạy Variant ---
    print("\n--- Chạy Variant ---")
    try:
        variant_results = run_scorecard(
            config=VARIANT_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )
        variant_md = generate_scorecard_summary(variant_results, VARIANT_CONFIG["label"])
        variant_path = RESULTS_DIR / "scorecard_variant.md"
        variant_path.write_text(variant_md, encoding="utf-8")
        print(f"\nScorecard variant lưu tại: {variant_path}")
    except NotImplementedError:
        print("Variant chưa implement xong.")
        variant_results = []

    # --- A/B Comparison ---
    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv="ab_comparison.csv"
        )

    print("\n\nViệc cần làm Sprint 4:")
    print("  1. Hoàn thành Sprint 2 + 3 trước")
    print("  2. LLM-as-Judge đã bật cho faithfulness/relevance/completeness")
    print("  3. Chạy run_scorecard(BASELINE_CONFIG) hoặc config có preset_name")
    print("  4. Chạy run_scorecard(VARIANT_CONFIG) hoặc preset khác (hybrid/rerank/query_transform)")
    print("  5. Gọi compare_ab() để thấy delta")
    print("  6. Cập nhật docs/tuning-log.md với kết quả và nhận xét")
