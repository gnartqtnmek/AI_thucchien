import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider
from src.telemetry.logger import logger
from src.tools import menu_tool

from src.core.metrics import calculate_cost, calculate_token_ratio
from src.core.retry import retry_with_backoff


class ReActAgent:
    """
    ReAct-style agent using OpenAI tool calling.
    """

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 6,
        trace_enabled: bool = False,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.trace_enabled = trace_enabled
        self.last_trace: List[Dict[str, Any]] = []
        self.last_tokens = 0
        self.last_latency = 0
        self.last_cost = 0.0
        self.last_ratio = 0.0
        self.tool_map = {t["name"]: t for t in tools}

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['description']}" for t in self.tools]
        )
        return f"""
Bạn là trợ lý của cửa hàng gà rán ở Hà Nội.
Chỉ trả lời các câu hỏi về menu, combo, giá, mã giảm giá, đặt hàng.
Nếu câu hỏi ngoài phạm vi (ví dụ: giá cổ phiếu, thời tiết), hãy nói rõ là không biết.

Bạn có các công cụ sau:
{tool_descriptions}

Quy tắc xử lý đơn hàng:
- Khi khách hỏi mua/đặt hoặc hỏi giá, luôn dùng tool để tính.
- Luôn kiểm tra tồn kho và luôn kiểm tra mã giảm giá khả dụng.
- Nếu có mã giảm giá hợp lệ, chỉ áp dụng 1 mã tốt nhất.
"""

    def _openai_tools_schema(self) -> List[Dict[str, Any]]:
        return [t["schema"] for t in self.tools]

    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def _call_llm(self, messages):
        return self.llm.client.chat.completions.create(
            model=self.llm.model_name,
            messages=messages,
            tools=self._openai_tools_schema(),
        )

    def _record_trace(self, step: int, tool_name: str, args: Dict[str, Any], observation: str) -> None:
        entry = {
            "step": step,
            "action": tool_name,
            "args": args,
            "observation": observation,
        }
        self.last_trace.append(entry)
        if self.trace_enabled:
            print(f"[Trace] Step {step}: {tool_name}({args})")
            print(f"[Trace] Observation: {observation}")

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.tool_map.get(tool_name)
        if not tool:
            return {"success": False, "message": f"Tool '{tool_name}' not found."}
        func = tool.get("func")
        if not func:
            return {"success": False, "message": f"Tool '{tool_name}' has no function."}

        if not isinstance(args, dict):
            args = {}

        if "data" in tool:
            args = dict(args)
            args.setdefault("data", tool["data"])

        try:
            result = func(**args)
        except Exception as exc:
            logger.error(f"Tool {tool_name} failed: {exc}")
            return {"success": False, "message": f"{exc}"}

        if isinstance(result, dict):
            return result
        return {"success": True, "result": result}

    def run(self, user_input: str) -> str:
        import time
        if not isinstance(self.llm, OpenAIProvider):
            return "Agent hiện chỉ hỗ trợ OpenAIProvider cho function calling."

        self.last_trace = []
        total_tokens = 0
        total_prompt = 0
        total_completion = 0
        total_latency = 0
        total_cost = 0.0

        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        messages = [
            {"role": "system", "content": self.get_system_prompt().strip()},
            {"role": "user", "content": user_input},
        ]

        for step in range(self.max_steps):
            start_time = time.time()
            response = self._call_llm(messages)
            latency_ms = (time.time() - start_time) * 1000
            total_latency += latency_ms

            if response.usage:
                total_tokens += response.usage.total_tokens
                total_prompt += response.usage.prompt_tokens
                total_completion += response.usage.completion_tokens

            msg = response.choices[0].message

            # Log usage if available
            if response.usage:
                logger.log_event(
                    "LLM_METRIC",
                    {
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens,
                        },
                        "latency_ms": None,
                        "provider": "openai",
                        "step": step + 1,
                    },
                )

            tool_calls = msg.tool_calls or []
            if tool_calls:
                # Append assistant message with tool calls
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": tool_calls,
                    }
                )

                for call in tool_calls:
                    name = call.function.name
                    try:
                        args = json.loads(call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    result = self._execute_tool(name, args)
                    tool_content = json.dumps(result, ensure_ascii=False)
                    self._record_trace(step + 1, name, args, tool_content)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": tool_content,
                        }
                    )
                continue

            # No tool calls -> final response
            if msg.content:
                logger.log_event("AGENT_END", {"steps": step + 1, "reason": "final_answer"})
                
                self.last_tokens = total_tokens
                self.last_latency = total_latency
                self.last_cost = calculate_cost(self.llm.model_name, total_prompt, total_completion)
                self.last_ratio = calculate_token_ratio(total_prompt, total_completion)

                return msg.content.strip()

        logger.log_event("AGENT_END", {"steps": self.max_steps, "reason": "max_steps"})
        
        self.last_tokens = total_tokens
        self.last_latency = total_latency
        self.last_cost = calculate_cost(self.llm.model_name, total_prompt, total_completion)
        self.last_ratio = calculate_token_ratio(total_prompt, total_completion)

        return "Xin lỗi, mình chưa thể hoàn thành yêu cầu trong số bước cho phép."


class OpenAIFunctionAgent:
    """
    Convenience wrapper to run the ReAct agent with OpenAI + menu tools.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        data_path: str = "data/mock_data.json",
        max_steps: int = 6,
        trace_enabled: Optional[bool] = None,
    ):
        load_dotenv()
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing. Please set it in your environment.")

        model_name = model_name or os.getenv("DEFAULT_MODEL", "gpt-4o")
        if trace_enabled is None:
            trace_enabled = os.getenv("AGENT_TRACE", "0") == "1"

        llm = OpenAIProvider(model_name=model_name, api_key=api_key)
        tools = _build_menu_tools(data_path)
        self.agent = ReActAgent(
            llm=llm,
            tools=tools,
            max_steps=max_steps,
            trace_enabled=trace_enabled,
        )

    def run(self, user_input: str) -> str:
        return self.agent.run(user_input)


def _build_menu_tools(data_path: str) -> List[Dict[str, Any]]:
    tools = []

    tools.append(
        {
            "name": "get_item",
            "description": "Tìm món theo id, tên hoặc category (tiếng Việt).",
            "func": menu_tool.get_item,
            "data": data_path,
            "schema": {
                "type": "function",
                "function": {
                    "name": "get_item",
                    "description": "Tìm món theo id, tên hoặc category (tiếng Việt).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string"},
                            "name": {"type": "string"},
                            "category_vi": {"type": "string"},
                            "available_only": {"type": "boolean"},
                        },
                        "required": ["item_id", "name", "category_vi", "available_only"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }
    )

    tools.append(
        {
            "name": "get_combo",
            "description": "Tìm combo theo id hoặc tên (tiếng Việt).",
            "func": menu_tool.get_combo,
            "data": data_path,
            "schema": {
                "type": "function",
                "function": {
                    "name": "get_combo",
                    "description": "Tìm combo theo id hoặc tên (tiếng Việt).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "combo_id": {"type": "string"},
                            "name": {"type": "string"},
                            "available_only": {"type": "boolean"},
                        },
                        "required": ["combo_id", "name", "available_only"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }
    )

    tools.append(
        {
            "name": "get_discount",
            "description": "Lấy mã giảm giá theo code hoặc danh sách mã giảm giá.",
            "func": menu_tool.get_discount,
            "data": data_path,
            "schema": {
                "type": "function",
                "function": {
                    "name": "get_discount",
                    "description": "Lấy mã giảm giá theo code hoặc danh sách mã giảm giá.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "active_only": {"type": "boolean"},
                        },
                        "required": ["code", "active_only"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }
    )

    tools.append(
        {
            "name": "get_best_seller",
            "description": "Lấy món bán chạy nhất.",
            "func": menu_tool.get_best_seller,
            "data": data_path,
            "schema": {
                "type": "function",
                "function": {
                    "name": "get_best_seller",
                    "description": "Lấy món bán chạy nhất.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                    "additionalProperties": False,
                    "strict": True,
                },
            },
        }
    )

    tools.append(
        {
            "name": "compare_items_vs_combo",
            "description": "So sánh giá món lẻ với combo, có xét giảm giá tốt nhất.",
            "func": menu_tool.compare_items_vs_combo,
            "data": data_path,
            "schema": {
                "type": "function",
                "function": {
                    "name": "compare_items_vs_combo",
                    "description": "So sánh giá món lẻ với combo, có xét giảm giá tốt nhất.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "item_id": {"type": "string"},
                                        "name": {"type": "string"},
                                        "quantity": {"type": "integer"},
                                    },
                                    "required": ["item_id", "name", "quantity"],
                                    "additionalProperties": False,
                                },
                            },
                            "combo_id": {"type": "string"},
                            "combo_quantity": {"type": "integer"},
                        },
                        "required": ["order_items", "combo_id", "combo_quantity"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }
    )

    tools.append(
        {
            "name": "calculating_total_bill",
            "description": "Tính tổng bill và tự chọn mã giảm giá tốt nhất.",
            "func": menu_tool.calculating_total_bill,
            "data": data_path,
            "schema": {
                "type": "function",
                "function": {
                    "name": "calculating_total_bill",
                    "description": "Tính tổng bill và tự chọn mã giảm giá tốt nhất.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "item_id": {"type": "string"},
                                        "name": {"type": "string"},
                                        "quantity": {"type": "integer"},
                                    },
                                    "required": ["item_id", "name", "quantity"],
                                    "additionalProperties": False,
                                },
                            },
                            "order_combos": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "combo_id": {"type": "string"},
                                        "name": {"type": "string"},
                                        "quantity": {"type": "integer"},
                                    },
                                    "required": ["combo_id", "name", "quantity"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["order_items", "order_combos"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }
    )

    return tools
