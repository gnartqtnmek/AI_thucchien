from __future__ import annotations

import re
from typing import Callable
from .store import EmbeddingStore

class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.
    Đã được tối ưu hóa Prompt Engineering cho RAG.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def _tokenize(self, text: str) -> set[str]:
        # Keep both words and numbers so queries with prices/subscriber counts are ranked better.
        return set(re.findall(r"\d+[\d\.,]*|[\wÀ-ỹà-ỹ]+", text.lower(), flags=re.UNICODE))

    def _expand_queries(self, question: str) -> list[str]:
        normalized = " ".join(question.split())
        parts = [normalized]

        for segment in re.split(r"\s+(?:và|and|or|hoặc)\s+", normalized, flags=re.IGNORECASE):
            cleaned = segment.strip(" ,.;:!?")
            if cleaned and cleaned not in parts:
                parts.append(cleaned)

        return parts

    def _is_numeric_question(self, question: str) -> bool:
        lowered = question.lower()
        numeric_cues = [
            "bao nhiêu",
            "mức giá",
            "giá",
            "chi phí",
            "số lượng",
            "price",
            "cost",
            "how many",
            "usd",
            "vnđ",
            "đồng",
        ]
        return any(cue in lowered for cue in numeric_cues)

    def _hybrid_retrieve(self, question: str, top_k: int) -> list[dict]:
        expanded_queries = self._expand_queries(question)
        candidate_k = max(top_k * 4, 12)

        merged: dict[str, dict] = {}
        clause_priority_ids: list[str] = []

        for query_index, query in enumerate(expanded_queries):
            hits = self.store.search(query, top_k=candidate_k)
            if query_index > 0 and hits:
                top_hit_id = str(hits[0].get("id") or "")
                if top_hit_id:
                    clause_priority_ids.append(top_hit_id)

            for hit in hits:
                hit_id = str(hit.get("id") or f"{len(merged)}")
                existing = merged.get(hit_id)
                if existing is None or hit.get("score", 0.0) > existing.get("score", 0.0):
                    merged[hit_id] = hit.copy()

        if not merged:
            return []

        question_tokens = self._tokenize(question)
        expects_number = self._is_numeric_question(question)
        rescored: list[dict] = []

        for hit in merged.values():
            hit_id = str(hit.get("id") or "")
            content = hit.get("content", "")
            content_tokens = self._tokenize(content)
            lexical_score = len(question_tokens & content_tokens) / max(1, len(question_tokens))

            number_bonus = 0.0
            if expects_number and re.search(r"\d", content):
                number_bonus += 0.06
            if expects_number and re.search(r"(usd|vnđ|đồng|triệu|nghìn|thuê bao|%)", content.lower()):
                number_bonus += 0.04

            hybrid_score = 0.75 * float(hit.get("score", 0.0)) + 0.25 * lexical_score + number_bonus

            scored_hit = hit.copy()
            scored_hit["_id"] = hit_id
            scored_hit["hybrid_score"] = hybrid_score
            rescored.append(scored_hit)

        rescored.sort(key=lambda item: item["hybrid_score"], reverse=True)

        scored_by_id = {str(item.get("_id", "")): item for item in rescored}
        selected: list[dict] = []
        selected_ids: set[str] = set()

        for priority_id in clause_priority_ids:
            prioritized = scored_by_id.get(priority_id)
            if prioritized and priority_id not in selected_ids:
                selected.append(prioritized)
                selected_ids.add(priority_id)

        for item in rescored:
            current_id = str(item.get("_id", ""))
            if current_id in selected_ids:
                continue
            selected.append(item)
            selected_ids.add(current_id)
            if len(selected) >= top_k:
                break

        return selected[:top_k]

    def answer(self, question: str, top_k: int = 3) -> str:
        retrieved_chunks = self._hybrid_retrieve(question, top_k=top_k)
        
        # TỐI ƯU 1: Xử lý trường hợp không tìm thấy tài liệu nào
        if not retrieved_chunks:
            return "Xin lỗi, hiện tại tôi không có dữ liệu nào liên quan đến câu hỏi của bạn."

        # TỐI ƯU 2: Đưa tên file/nguồn (source) vào Context để LLM biết thông tin lấy từ đâu
        context_texts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            source = chunk['metadata'].get('source', 'Tài liệu nội bộ')
            context_texts.append(f"[Tài liệu {i} | Nguồn: {source}]:\n{chunk['content']}\n")
            
        context_block = "\n".join(context_texts)
        
        prompt = (
            "Bạn là một trợ lý AI thông minh, chuyên gia phân tích tài liệu nội bộ.\n"
            "Nhiệm vụ của bạn là trả lời câu hỏi của người dùng một cách NGẮN GỌN và CHÍNH XÁC.\n"
            "Ưu tiên trích xuất đúng số liệu, đơn vị, mốc thời gian và không tự suy diễn.\n\n"
            "QUY TẮC TUYỆT ĐỐI:\n"
            "1. CHỈ dựa vào phần 'NGỮ CẢNH' bên dưới để trả lời.\n"
            "2. Nếu 'NGỮ CẢNH' không chứa thông tin để trả lời, BẮT BUỘC phải nói: 'Dựa trên tài liệu hiện tại, tôi không có thông tin về vấn đề này.' Không được tự suy diễn.\n"
            "3. Nếu câu hỏi có nhiều ý, trả lời theo từng ý để không bỏ sót.\n"
            "4. Nếu tài liệu có cả phí một lần và phí định kỳ, phải tách rõ 2 loại phí, không gộp lẫn.\n"
            "5. Nếu câu hỏi có cụm 'hàng tháng' hoặc 'mỗi tháng', ưu tiên mức phí duy trì định kỳ ở các tháng tiếp theo; không dùng tổng phí tháng đầu trừ khi người dùng hỏi riêng.\n"
            "6. Nếu có thể, hãy trích dẫn ngắn gọn nguồn (Ví dụ: Theo tài liệu X...).\n\n"
            f"--- BẮT ĐẦU NGỮ CẢNH ---\n{context_block}--- KẾT THÚC NGỮ CẢNH ---\n\n"
            f"Câu hỏi: {question}\n\n"
            f"Câu trả lời:"
        )
        
        return self.llm_fn(prompt)