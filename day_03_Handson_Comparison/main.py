"""
main.py - Restaurant Order Assistant Demo

Cách dùng:
  python main.py --mode chatbot
  python main.py --mode agent_v1
  python main.py --mode agent_v2
  python main.py --mode all                  # chạy cả 3, so sánh
  python main.py --mode chatbot --uc 3       # chỉ chạy UC3
  python main.py --mode all --uc 4           # so sánh cả 3 trên UC4
  python main.py --mode chatbot --interactive # chế độ chat tự do

Provider mặc định lấy từ .env (DEFAULT_PROVIDER).
Ghi đè: python main.py --mode chatbot --provider openai
"""

import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Use cases ─────────────────────────────────────────────────────────────────

USE_CASES = [
    {
        "id": "UC1",
        "name": "Cross-city detection",
        "query": "Tôi ở TP.HCM muốn đặt 1 GA4. Nhà hàng có giao không?",
        "expected": "Từ chối giao hàng vì khác thành phố",
    },
    {
        "id": "UC2",
        "name": "Menu & discount query",
        "query": "Hôm nay có những món gì và mã giảm giá nào đang áp dụng?",
        "expected": "Liệt kê thực đơn + mã giảm giá active",
    },
    {
        "id": "UC3",
        "name": "Price comparison",
        "query": "Đi 2 người, mua 2 GA2 + 2 Pepsi hay dùng Combo FF2 thì rẻ hơn?",
        "expected": "FF2 (159k) rẻ hơn 2xGA2+2xPepsi (168k) và có thêm 2 FRIES",
    },
    {
        "id": "UC4",
        "name": "Bill calculation + freeship",
        "query": "Tính bill: 1 Combo Gia đình + 2 Khoai tây chiên + 3 Pepsi, dùng mã GA20. Freeship không?",
        "expected": "Tổng 434k → GA20 giảm 86.8k → còn 347.2k → đủ freeship tại Hà Nội",
    },
    {
        "id": "UC5",
        "name": "Out-of-domain",
        "query": "Hôm nay thời tiết Hà Nội như thế nào?",
        "expected": "Từ chối lịch sự, không liên quan nhà hàng",
    },
]

# ── Provider factory ───────────────────────────────────────────────────────────

def build_provider(name: str):
    name = name or os.getenv("DEFAULT_PROVIDER", "openai")
    if name == "openai":
        from src.core.openai_provider import OpenAIProvider
        return OpenAIProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    elif name == "google":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    elif name == "local":
        from src.core.local_provider import LocalProvider
        return LocalProvider(model_path=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf"))
    else:
        raise ValueError(f"Unknown provider: {name}. Choose: openai | google | local")

# ── System builders ────────────────────────────────────────────────────────────

def build_chatbot(llm):
    from src.chatbot.chatbot import RestaurantChatbot
    return RestaurantChatbot(llm)

def build_agent_v1(llm):
    try:
        from src.agent.agent import ReActAgent
        from src.tools import TOOL_REGISTRY
        return ReActAgent(llm, TOOL_REGISTRY, max_steps=5, version="v1")
    except (ImportError, AttributeError):
        print("[WARN] Agent v1 chưa được implement đầy đủ.")
        return None

def build_agent_v2(llm):
    try:
        from src.agent.agent import ReActAgent
        from src.tools import TOOL_REGISTRY
        return ReActAgent(llm, TOOL_REGISTRY, max_steps=7, version="v2")
    except (ImportError, AttributeError):
        print("[WARN] Agent v2 chưa được implement đầy đủ.")
        return None

# ── Runner ─────────────────────────────────────────────────────────────────────

def run_query(system, mode_name: str, query: str) -> str:
    if system is None:
        return "[Chưa implement]"
    try:
        if mode_name == "chatbot":
            system.reset()
            return system.chat(query)
        else:
            return system.run(query)
    except Exception as e:
        return f"[ERROR] {e}"

def run_single_mode(mode: str, uc_filter: int | None, llm):
    builders = {
        "chatbot":  build_chatbot,
        "agent_v1": build_agent_v1,
        "agent_v2": build_agent_v2,
    }
    system = builders[mode](llm)
    cases = [USE_CASES[uc_filter - 1]] if uc_filter else USE_CASES

    for uc in cases:
        print(f"\n{'='*65}")
        print(f"[{uc['id']}] {uc['name']}")
        print(f"Query    : {uc['query']}")
        print(f"Expected : {uc['expected']}")
        print(f"{'─'*65}")
        answer = run_query(system, mode, uc["query"])
        print(f"Answer   : {answer}")

def run_all_modes(uc_filter: int | None, llm):
    chatbot  = build_chatbot(llm)
    agent_v1 = build_agent_v1(llm)
    agent_v2 = build_agent_v2(llm)

    cases = [USE_CASES[uc_filter - 1]] if uc_filter else USE_CASES

    for uc in cases:
        print(f"\n{'='*65}")
        print(f"[{uc['id']}] {uc['name']}")
        print(f"Query    : {uc['query']}")
        print(f"Expected : {uc['expected']}")
        print(f"{'─'*65}")
        print(f"CHATBOT  : {run_query(chatbot,  'chatbot',  uc['query'])}")
        print(f"AGENT V1 : {run_query(agent_v1, 'agent_v1', uc['query'])}")
        print(f"AGENT V2 : {run_query(agent_v2, 'agent_v2', uc['query'])}")

def run_interactive(mode: str, llm):
    builders = {
        "chatbot":  build_chatbot,
        "agent_v1": build_agent_v1,
        "agent_v2": build_agent_v2,
    }
    system = builders[mode](llm)
    print(f"\nChế độ chat tự do [{mode.upper()}] — gõ 'quit' để thoát\n")

    while True:
        try:
            user_input = input("Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "thoát"):
            print("Tạm biệt!")
            break
        answer = run_query(system, mode, user_input)
        print(f"Bot: {answer}\n")

# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Restaurant Order Assistant — Chatbot vs ReAct Agent"
    )
    parser.add_argument(
        "--mode",
        choices=["chatbot", "agent_v1", "agent_v2", "all"],
        default="chatbot",
        help="Hệ thống cần chạy (default: chatbot)",
    )
    parser.add_argument(
        "--uc",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=None,
        help="Chỉ chạy 1 use case cụ thể (1-5). Mặc định: chạy tất cả",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "google", "local"],
        default=None,
        help="LLM provider (mặc định lấy từ .env DEFAULT_PROVIDER)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Chế độ chat tự do (không dùng được với --mode all)",
    )
    args = parser.parse_args()

    llm = build_provider(args.provider)
    print(f"Provider : {llm.__class__.__name__} ({llm.model_name})")

    if args.interactive:
        if args.mode == "all":
            print("[ERROR] --interactive không dùng được với --mode all")
            sys.exit(1)
        run_interactive(args.mode, llm)
    elif args.mode == "all":
        run_all_modes(args.uc, llm)
    else:
        run_single_mode(args.mode, args.uc, llm)


if __name__ == "__main__":
    main()
