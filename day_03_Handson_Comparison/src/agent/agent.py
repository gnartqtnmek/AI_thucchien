import json
import re
from typing import List, Dict, Any, Optional, Tuple
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 5,
        version: str = "v1",
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.version = version
        self.history = []
        self.last_trace = []
        self.last_tokens = 0
        self.last_latency = 0
        self.last_cost = 0.0
        self.last_ratio = 0.0

    def get_system_prompt(self) -> str:
        """
        TODO: Implement the system prompt that instructs the agent to follow ReAct.
        Should include:
        1.  Available tools and their descriptions.
        2.  Format instructions: Thought, Action, Observation.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])

        if self.version == "v2":
            extra_rules = """
    Rules:
    - Chỉ được gọi đúng tên tool đã cung cấp.
    - Mỗi bước chỉ dùng tối đa 1 Action.
    - Nếu đã đủ dữ liệu, trả lời ngay bằng Final Answer.
    - Nếu tool trả lỗi/không tìm thấy, nêu rõ cho người dùng và gợi ý dữ liệu cần bổ sung.
    - Nhà hàng chỉ giao trong Hà Nội. Không xác nhận giao hàng ngoài Hà Nội.
    """
        else:
            extra_rules = """
    Rules:
    - Dùng tool khi cần dữ liệu thực tế (món ăn, combo, freeship, best seller).
    - Khi có Observation đủ thông tin thì chốt Final Answer.
    - Nhà hàng chỉ giao trong Hà Nội. Không xác nhận giao hàng ngoài Hà Nội.
    """

        return f"""
    Bạn là trợ lý đặt món của nhà hàng gà rán tại Hà Nội.
    Bạn có thể suy luận theo ReAct và dùng tools sau:
    {tool_descriptions}

    {extra_rules}

    Bắt buộc đúng format:
    Thought: <lý do ngắn>

    Trường hợp cần gọi tool:
    Action: <tool_name>(<args>)

    Trường hợp đủ dữ liệu:
    Final Answer: <câu trả lời tiếng Việt cho người dùng>

    Lưu ý quan trọng:
    - KHÔNG tự tạo Observation.
    - Observation sẽ do hệ thống cung cấp sau khi Action được chạy.
        """

    def run(self, user_input: str) -> str:
        if self.version == "v2":
            return self._run_v2(user_input)
        return self._run_v1(user_input)

    def _run_v1(self, user_input: str) -> str:
        """
        ReAct loop for v1 (kept stable for baseline comparison).
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name, "version": self.version})

        scratchpad: List[str] = []
        steps = 0
        final_answer = ""
        total_tokens = 0
        total_latency = 0
        total_cost = 0.0
        total_prompt = 0
        total_completion = 0

        while steps < self.max_steps:
            current_prompt = self._build_prompt(user_input, scratchpad)
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = result.get("content", "").strip()
            
            total_tokens += result.get("usage", {}).get("total_tokens", 0)
            total_prompt += result.get("usage", {}).get("prompt_tokens", 0)
            total_completion += result.get("usage", {}).get("completion_tokens", 0)
            total_cost += result.get("cost", 0.0)
            if result.get("latency_ms"):
                total_latency += result.get("latency_ms")

            logger.log_event(
                "AGENT_STEP",
                {
                    "step": steps + 1,
                    "llm_output": content,
                    "usage": result.get("usage", {}),
                    "latency_ms": result.get("latency_ms"),
                },
            )

            parsed_action = self._parse_action(content)
            if parsed_action:
                tool_name, args = parsed_action
                observation = self._execute_tool(tool_name, args)
                observation_text = json.dumps(observation, ensure_ascii=False)
                thought = self._extract_thought(content)
                if thought:
                    scratchpad.append(f"Thought: {thought}")
                scratchpad.append(f"Action: {tool_name}({args})")
                scratchpad.append(f"Observation: {observation_text}")
            else:
                final_answer = self._extract_final_answer(content)
                if final_answer:
                    steps += 1
                    break

                # Recovery path for malformed outputs: force model to continue with strict format.
                scratchpad.append(content)
                scratchpad.append(
                    "Observation: Invalid format. Hãy dùng đúng mẫu Action: tool_name(args) hoặc Final Answer:."
                )

            steps += 1

        if not final_answer:
            final_answer = (
                "Mình chưa thể hoàn tất trong số bước cho phép. "
                "Bạn vui lòng cung cấp thêm chi tiết (tên món/mã combo/tổng tiền/thành phố) để mình xử lý chính xác hơn."
            )

        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": final_answer})

        self.last_trace = scratchpad.copy()
        self.last_tokens = total_tokens
        self.last_latency = total_latency
        self.last_cost = total_cost
        from src.core.metrics import calculate_token_ratio
        self.last_ratio = calculate_token_ratio(total_prompt, total_completion)

        logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_answer})
        return final_answer

    def _run_v2(self, user_input: str) -> str:
        """
        Improved v2:
        - Pre-grounds likely-needed tool data before first LLM call.
        - Keeps ReAct loop for follow-up tool calls.
        - Enforces delivery business rules on the final answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name, "version": self.version})

        scratchpad: List[str] = []
        steps = 0
        final_answer = ""
        total_tokens = 0
        total_latency = 0
        total_cost = 0.0
        total_prompt = 0
        total_completion = 0
        latest_observations: Dict[str, Dict[str, Any]] = {}

        # Ground likely facts early to reduce hallucination risk.
        planned_actions = self._plan_actions_v2(user_input)
        for tool_name, args in planned_actions:
            observation = self._execute_tool(tool_name, args)
            latest_observations[tool_name] = observation
            scratchpad.append("Thought: Dùng dữ liệu thực từ tool để trả lời chính xác.")
            scratchpad.append(f"Action: {tool_name}({args})")
            scratchpad.append(f"Observation: {json.dumps(observation, ensure_ascii=False)}")

        while steps < self.max_steps:
            current_prompt = self._build_prompt(user_input, scratchpad)
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = result.get("content", "").strip()

            total_tokens += result.get("usage", {}).get("total_tokens", 0)
            total_prompt += result.get("usage", {}).get("prompt_tokens", 0)
            total_completion += result.get("usage", {}).get("completion_tokens", 0)
            total_cost += result.get("cost", 0.0)
            if result.get("latency_ms"):
                total_latency += result.get("latency_ms")

            logger.log_event(
                "AGENT_STEP",
                {
                    "step": steps + 1,
                    "llm_output": content,
                    "usage": result.get("usage", {}),
                    "latency_ms": result.get("latency_ms"),
                },
            )

            parsed_action = self._parse_action(content)
            if parsed_action:
                tool_name, args = parsed_action
                observation = self._execute_tool(tool_name, args)
                latest_observations[tool_name] = observation
                thought = self._extract_thought(content)
                if thought:
                    scratchpad.append(f"Thought: {thought}")
                scratchpad.append(f"Action: {tool_name}({args})")
                scratchpad.append(f"Observation: {json.dumps(observation, ensure_ascii=False)}")
            else:
                final_answer = self._extract_final_answer(content)
                if final_answer:
                    steps += 1
                    break

                scratchpad.append(content)
                scratchpad.append(
                    "Observation: Invalid format. Hãy dùng đúng mẫu Action: tool_name(args) hoặc Final Answer:."
                )

            steps += 1

        if not final_answer:
            final_answer = (
                "Mình chưa thể hoàn tất trong số bước cho phép. "
                "Bạn vui lòng cung cấp thêm chi tiết (tên món/mã combo/tổng tiền/thành phố) để mình xử lý chính xác hơn."
            )

        final_answer = self._enforce_business_rules_v2(final_answer, latest_observations, user_input)

        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": final_answer})

        self.last_trace = scratchpad.copy()
        self.last_tokens = total_tokens
        self.last_latency = total_latency
        self.last_cost = total_cost
        from src.core.metrics import calculate_token_ratio
        self.last_ratio = calculate_token_ratio(total_prompt, total_completion)

        logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_answer})
        return final_answer

    def _build_prompt(self, user_input: str, scratchpad: List[str]) -> str:
        history_text = "\n".join(
            f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
            for h in self.history[-6:]
        )
        trace_text = "\n".join(scratchpad)
        return (
            f"Conversation:\n{history_text}\n\n"
            f"Current user request: {user_input}\n\n"
            f"ReAct trace so far:\n{trace_text}\n\n"
            "Tiếp tục theo đúng format ReAct."
        )

    @staticmethod
    def _extract_final_answer(text: str) -> str:
        match = re.search(r"Final\s*Answer\s*:\s*(.*)", text, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_thought(text: str) -> str:
        match = re.search(r"Thought\s*:\s*(.*)", text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_action(text: str) -> Optional[Tuple[str, str]]:
        # Accept both single-line and multiline action arguments.
        match = re.search(r"Action\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*)\((.*?)\)", text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        tool_name = match.group(1).strip()
        args = match.group(2).strip().strip('"').strip("'")
        return tool_name, args

    def _plan_actions_v2(self, user_input: str) -> List[Tuple[str, str]]:
        lower = user_input.lower()
        actions: List[Tuple[str, str]] = []

        # Combo info requests.
        if "combo" in lower:
            combo_match = re.search(r"combo\s+([\w\sÀ-ỹ]+)", user_input, flags=re.IGNORECASE)
            combo_arg = ""
            if combo_match:
                candidate = combo_match.group(1).strip(" ?!.,")
                if candidate.lower() not in {"nao", "nào", "gi", "gì"}:
                    combo_arg = candidate
            actions.append(("get_combo", combo_arg))

        # Bestseller / top-5 requests.
        if any(k in lower for k in ["bán chạy nhất", "ban chay nhat", "best seller", "món hot", "mon hot"]):
            actions.append(("get_best_seller", ""))
        if any(k in lower for k in ["top 5", "5 món bán chạy", "5 mon ban chay", "top nam", "top năm"]):
            actions.append(("get_best_five", ""))

        # Item-specific checks.
        item_patterns = [
            r"món\s+([\w\sÀ-ỹ]+)",
            r"gia\s+([\w\sÀ-ỹ]+)",
            r"giá\s+([\w\sÀ-ỹ]+)",
            r"còn\s+([\w\sÀ-ỹ]+)",
            r"con\s+([\w\sÀ-ỹ]+)",
        ]
        for pattern in item_patterns:
            m = re.search(pattern, user_input, flags=re.IGNORECASE)
            if m:
                candidate = m.group(1).strip(" ?!.,")
                candidate = re.sub(
                    r"\b(còn không|con khong|còn ko|con ko|bao nhiêu|bao nhieu|không|khong|ko)\b.*$",
                    "",
                    candidate,
                    flags=re.IGNORECASE,
                ).strip(" ?!.,")
                if candidate and candidate.lower() not in {"nao", "nào", "gi", "gì"}:
                    actions.append(("get_item", candidate))
                    break

        alias = re.search(r"\b(GA\d+|BURGER|FRIES|PEPSI|SALAD|NUGGETS|CHEESE_BALLS)\b", user_input, flags=re.IGNORECASE)
        if alias and not any(name == "get_item" for name, _ in actions):
            actions.append(("get_item", alias.group(1).upper()))

        # Freeship checks.
        if any(k in lower for k in ["freeship", "miễn phí ship", "mien phi ship", "giao", "ship"]):
            amount_match = re.search(r"(\d[\d\._]{4,})", user_input)
            if amount_match:
                amount = amount_match.group(1).replace(".", "").replace("_", "")
                city = "Ha Noi"
                if any(s in lower for s in ["tp.hcm", "hcm", "ho chi minh", "hồ chí minh", "sai gon", "sài gòn"]):
                    city = "Ho Chi Minh"
                elif any(s in lower for s in ["hà nội", "ha noi", "hanoi"]):
                    city = "Ha Noi"
                actions.append(("check_freeship", f"{amount},{city}"))

        # Remove duplicates while keeping first occurrence order.
        seen = set()
        deduped: List[Tuple[str, str]] = []
        for tool_name, args in actions:
            key = (tool_name, args)
            if key in seen:
                continue
            seen.add(key)
            deduped.append((tool_name, args))
        return deduped

    def _enforce_business_rules_v2(
        self,
        final_answer: str,
        latest_observations: Dict[str, Dict[str, Any]],
        user_input: str,
    ) -> str:
        # Guard: Only enforce delivery restriction for out-of-Hanoi cities.
        # Do NOT block orders under 200k - let the agent decide based on tool data.
        freeship_obs = latest_observations.get("check_freeship")
        if isinstance(freeship_obs, dict):
            if freeship_obs.get("ok") and freeship_obs.get("deliverable") is False:
                return "Xin lỗi, hiện nhà hàng chỉ giao trong Hà Nội nên chưa thể giao đến địa chỉ này."

        # Additional hard guard for cross-city asks if model still claims deliverability.
        lower = user_input.lower()
        is_hcm = any(s in lower for s in ["tp.hcm", "hcm", "ho chi minh", "hồ chí minh", "sai gon", "sài gòn"])
        if is_hcm and any(s in final_answer.lower() for s in ["giao được", "miễn phí giao", "giao hàng"]):
            return "Xin lỗi, hiện nhà hàng chỉ giao trong Hà Nội nên chưa thể giao đến địa chỉ này."

        return final_answer

    def _execute_tool(self, tool_name: str, args: str) -> Dict[str, Any]:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool["name"] == tool_name:
                func = tool.get("func")
                if not callable(func):
                    return {
                        "ok": False,
                        "error": f"Tool {tool_name} is missing callable func.",
                    }

                try:
                    output = func(args)
                    if isinstance(output, dict):
                        return output
                    return {
                        "ok": True,
                        "result": output,
                    }
                except Exception as e:
                    logger.log_event(
                        "AGENT_TOOL_ERROR",
                        {"tool": tool_name, "args": args, "error": str(e)},
                    )
                    return {
                        "ok": False,
                        "error": f"Tool execution failed: {e}",
                    }

        return {
            "ok": False,
            "error": f"Tool {tool_name} not found.",
        }
