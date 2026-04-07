import json
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.tools import (
    ITEMS,
    check_freeship,
    get_best_five,
    get_best_seller,
    get_combo,
    get_item,
)
from src.telemetry.logger import logger

ITEM_ALIAS_PATTERN = r"\b(GA\d+|BURGER|FRIES|PEPSI|SALAD|NUGGETS|CHEESE_BALLS)\b"


class RestaurantChatbot:
    """
    Baseline chatbot WITHOUT tools.
    Dùng để minh họa hạn chế của LLM thuần so với ReAct Agent:
    - Không tính toán chính xác được
    - Không kiểm tra tồn kho / trạng thái thực tế
    - Không phát hiện cross-city
    - Dễ hallucinate giá sai
    """

    SYSTEM_PROMPT = """Bạn là chatbot của nhà hàng gà rán tại Hà Nội.

Khi có dữ liệu tool trong hội thoại, bắt buộc ưu tiên dữ liệu đó để trả lời chính xác.
Không bịa thêm món, giá hoặc combo ngoài dữ liệu tool.

Trả lời ngắn gọn, đúng trọng tâm, lịch sự bằng tiếng Việt."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.history: List[Dict[str, str]] = []
        self.last_tokens = 0
        self.last_latency = 0
        self.last_cost = 0.0
        self.last_ratio = 0.0

    @staticmethod
    def _is_menu_list_query(user_message: str) -> bool:
        lower = user_message.lower()
        list_phrases = [
            "co nhung mon nao",
            "có những món nào",
            "co mon nao",
            "có món nào",
            "thực đơn",
            "thuc don",
            "menu",
            "liệt kê món",
            "liet ke mon",
        ]
        return any(phrase in lower for phrase in list_phrases)

    def _extract_query_target(self, user_message: str, tool_name: str) -> str:
        text = user_message.strip()

        if tool_name == "get_combo":
            match = re.search(r"combo\s+([\w\sÀ-ỹ]+)", text, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip(" ?!.,")
                generic_words = {"nao", "nào", "gi", "gì", "khong", "không"}
                if candidate.lower() in generic_words:
                    return ""
                return candidate
            if "combo" in text.lower():
                return ""

        if tool_name == "get_item":
            # Capture common forms: "món X", "kiểm tra X", "giá X".
            patterns = [
                r"món\s+([\w\sÀ-ỹ]+)",
                r"kiem tra\s+([\w\sÀ-ỹ]+)",
                r"kiểm tra\s+([\w\sÀ-ỹ]+)",
                r"gia\s+([\w\sÀ-ỹ]+)",
                r"giá\s+([\w\sÀ-ỹ]+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    candidate = match.group(1).strip(" ?!.,")
                    candidate = re.sub(
                        r"\b(còn không|con khong|còn ko|con ko|bao nhiêu|bao nhieu|không|khong|ko)\b.*$",
                        "",
                        candidate,
                        flags=re.IGNORECASE,
                    ).strip(" ?!.,")
                    generic_words = {"nao", "nào", "gi", "gì", "khong", "không"}
                    if candidate.lower() not in generic_words:
                        embedded_alias = re.search(r"\b([A-Z]{2,}(?:_[A-Z]+)?\d*)\b", candidate)
                        if embedded_alias:
                            return embedded_alias.group(1)
                        return candidate

            # Fallback: if text contains an uppercase item alias like GA2, FF2, etc.
            alias_match = re.search(ITEM_ALIAS_PATTERN, text, flags=re.IGNORECASE)
            if alias_match:
                return alias_match.group(1).upper()

        return ""

    @staticmethod
    def _is_best_seller_query(user_message: str) -> bool:
        lower = user_message.lower()
        keywords = [
            "best seller",
            "bán chạy nhất",
            "ban chay nhat",
            "món hot",
            "mon hot",
            "món nổi bật",
            "mon noi bat",
        ]
        return any(k in lower for k in keywords)

    @staticmethod
    def _is_best_five_query(user_message: str) -> bool:
        lower = user_message.lower()
        keywords = [
            "top 5",
            "top năm",
            "top nam",
            "năm món bán chạy",
            "nam mon ban chay",
            "5 món bán chạy",
            "5 mon ban chay",
        ]
        return any(k in lower for k in keywords)

    @staticmethod
    def _extract_amount_and_city(user_message: str) -> Optional[Dict[str, Any]]:
        # Examples:
        # - "đơn 190000 ở Hà Nội có freeship không"
        # - "freeship cho 250.000 tại TP.HCM không"
        amount_match = re.search(r"(\d[\d\._]{4,})", user_message)
        if not amount_match:
            return None

        amount_raw = amount_match.group(1).replace(".", "").replace("_", "")
        if not amount_raw.isdigit():
            return None

        city = "Ha Noi"
        lower = user_message.lower()
        if any(s in lower for s in ["tp.hcm", "hcm", "sài gòn", "sai gon", "ho chi minh"]):
            city = "TP.HCM"
        elif any(s in lower for s in ["hà nội", "ha noi", "hanoi"]):
            city = "Ha Noi"

        return {
            "total_amount": int(amount_raw),
            "city": city,
        }

    def _maybe_get_tool_context(self, user_message: str) -> Dict[str, Any]:
        lower = user_message.lower()
        context: Dict[str, Any] = {}

        is_best_seller_query = self._is_best_seller_query(user_message)
        is_best_five_query = self._is_best_five_query(user_message)

        if self._is_menu_list_query(user_message):
            context["menu_items"] = {
                "ok": True,
                "items": [item for item in ITEMS.values() if item.get("available")],
            }

        combo_list_phrases = [
            "co combo nao",
            "có combo nào",
            "co nhung combo nao",
            "có những combo nào",
            "danh sach combo",
            "danh sách combo",
        ]
        is_combo_list_query = any(phrase in lower for phrase in combo_list_phrases)

        if "combo" in lower:
            combo_arg = self._extract_query_target(user_message, "get_combo")
            if is_combo_list_query:
                context["get_combo"] = get_combo(None)
            else:
                context["get_combo"] = get_combo(combo_arg if combo_arg else None)

        if is_best_seller_query:
            context["get_best_seller"] = get_best_seller()

        if is_best_five_query:
            context["get_best_five"] = get_best_five()

        # Only run get_item when the sentence likely asks about a specific item.
        item_intent = bool(
            re.search(r"\b(món|mon|kiểm tra|kiem tra|giá|gia|còn|con)\b", lower)
            or re.search(ITEM_ALIAS_PATTERN, user_message, flags=re.IGNORECASE)
        )
        if item_intent and not (is_best_seller_query or is_best_five_query):
            item_arg = self._extract_query_target(user_message, "get_item")
            if item_arg:
                context["get_item"] = get_item(item_arg)

        freeship_keywords = ["freeship", "miễn phí ship", "mien phi ship", "giao hàng", "giao hang"]
        if any(k in lower for k in freeship_keywords):
            parsed = self._extract_amount_and_city(user_message)
            if parsed:
                context["check_freeship"] = check_freeship(
                    total_amount=parsed["total_amount"],
                    city=parsed["city"],
                )

        return context

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})

        tool_context = self._maybe_get_tool_context(user_message)

        # Build single-turn prompt from history
        history_text = "\n".join(
            f"{'Người dùng' if m['role'] == 'user' else 'Chatbot'}: {m['content']}"
            for m in self.history
        )

        if tool_context:
            history_text += "\n\nTool data (JSON):\n" + json.dumps(
                tool_context,
                ensure_ascii=False,
                indent=2,
            )

        result = self.llm.generate(history_text, system_prompt=self.SYSTEM_PROMPT)
        response = result["content"]

        self.last_tokens = result.get("usage", {}).get("total_tokens", 0)
        self.last_latency = result.get("latency_ms", 0)
        self.last_cost = result.get("cost", 0.0)
        self.last_ratio = result.get("token_ratio", 0.0)

        self.history.append({"role": "assistant", "content": response})
        logger.log_event("CHATBOT_RESPONSE", {
            "input": user_message,
            "output": response,
            "tool_context": tool_context,
            "usage": result["usage"],
            "latency_ms": result["latency_ms"],
        })
        return response

    def reset(self):
        self.history = []
