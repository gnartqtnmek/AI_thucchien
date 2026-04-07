"""
Day 1 — LLM API Foundation
AICB-P1: AI Practical Competency Program, Phase 1

Instructions:
    1. Fill in every section marked with TODO.
    2. Do NOT change function signatures.
    3. Copy this file to solution/solution.py when done.
    4. Run: pytest tests/ -v
"""

import os
import time
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Estimated costs per 1K OUTPUT tokens (USD) — update if pricing changes
# ---------------------------------------------------------------------------
COST_PER_1K_OUTPUT_TOKENS = {
    "gpt-4o": 0.010,
    "gpt-4o-mini": 0.0006,
}

OPENAI_MODEL = "gpt-4o"
OPENAI_MINI_MODEL = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Task 1 — Call GPT-4o
# ---------------------------------------------------------------------------
def call_openai(
    prompt: str,
    model: str = OPENAI_MODEL,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 256,
) -> tuple[str, float]:
    """
    Call the OpenAI Chat Completions API and return the response text + latency.
    """
    # Đưa import vào trong hàm để vượt qua bài test giả lập (mock)
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    start_time = time.time()

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )

    end_time = time.time()
    latency_seconds = end_time - start_time

    response_text = response.choices[0].message.content or ""

    return response_text, latency_seconds


# ---------------------------------------------------------------------------
# Task 2 — Call GPT-4o-mini
# ---------------------------------------------------------------------------
def call_openai_mini(
    prompt: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 256,
) -> tuple[str, float]:
    """
    Call the OpenAI Chat Completions API using gpt-4o-mini and return the
    response text + latency.
    """
    response_text, latency_seconds = call_openai(
        prompt=prompt,
        model=OPENAI_MINI_MODEL,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )
    
    return response_text, latency_seconds


# ---------------------------------------------------------------------------
# Task 3 — Compare GPT-4o vs GPT-4o-mini
# ---------------------------------------------------------------------------
def compare_models(prompt: str) -> dict:
    """
    Call both gpt-4o and gpt-4o-mini with the same prompt and return a
    comparison dictionary.
    """
    gpt4o_response, gpt4o_latency = call_openai(prompt=prompt)
    mini_response, mini_latency = call_openai_mini(prompt=prompt)
    
    word_count = len(gpt4o_response.split())
    estimated_tokens = word_count / 0.75
    gpt4o_cost_estimate = (estimated_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS["gpt-4o"]
    
    return {
        "gpt4o_response": gpt4o_response,
        "mini_response": mini_response,
        "gpt4o_latency": gpt4o_latency,
        "mini_latency": mini_latency,
        "gpt4o_cost_estimate": gpt4o_cost_estimate
    }


# ---------------------------------------------------------------------------
# Task 4 — Streaming chatbot with conversation history
# ---------------------------------------------------------------------------
def streaming_chatbot() -> None:
    """
    Run an interactive streaming chatbot in the terminal.
    """
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    history = []
    
    print("Chatbot started! Type 'quit' or 'exit' to end.")
    print("---------------------------------------------")
    
    while True:
        user_input = input("\nYou: ")
        
        if user_input.strip().lower() in ['quit', 'exit']:
            print("Exiting chatbot. Goodbye!")
            break
            
        history.append({"role": "user", "content": user_input})
        print("Bot: ", end="", flush=True)
        
        try:
            stream = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=history,
                stream=True
            )
            
            assistant_reply = ""
            
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                print(delta, end="", flush=True)
                assistant_reply += delta
                
            print()
            
            history.append({"role": "assistant", "content": assistant_reply})
            history = history[-6:]
            
        except Exception as e:
            print(f"\n[Error occurred]: {e}")


# ---------------------------------------------------------------------------
# Bonus Task A — Retry with exponential backoff
# ---------------------------------------------------------------------------
def retry_with_backoff(
    fn: Callable,
    max_retries: int = 3,
    base_delay: float = 0.1,
) -> Any:
    """
    Call fn(). If it raises an exception, retry up to max_retries times
    with exponential backoff (base_delay * 2^attempt).
    """
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries:
                raise e
            
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Bonus Task B — Batch compare
# ---------------------------------------------------------------------------
def batch_compare(prompts: list[str]) -> list[dict]:
    """
    Run compare_models on each prompt in the list.
    """
    results = []
    for prompt in prompts:
        comparison_result = compare_models(prompt)
        comparison_result["prompt"] = prompt
        results.append(comparison_result)
    
    return results


# ---------------------------------------------------------------------------
# Bonus Task C — Format comparison table
# ---------------------------------------------------------------------------
def format_comparison_table(results: list[dict]) -> str:
    """
    Format a list of compare_models results as a readable text table.
    """
    def truncate(text: str, max_length: int = 40) -> str:
        text = str(text).replace("\n", " ")
        if len(text) > max_length:
            return text[:max_length - 3] + "..."
        return text

    w_text = 40  # Độ rộng cho cột Prompt và Responses
    w_num = 15   # Độ rộng cho cột Latency

    header = f"{'Prompt':<{w_text}} | {'GPT-4o Response':<{w_text}} | {'Mini Response':<{w_text}} | {'GPT-4o Latency':<{w_num}} | {'Mini Latency':<{w_num}}"
    separator = "-" * len(header)
    
    table_lines = [header, separator]

    for row in results:
        p_str = truncate(row.get("prompt", ""))
        g4o_str = truncate(row.get("gpt4o_response", ""))
        mini_str = truncate(row.get("mini_response", ""))
        
        lat_g4o = f"{row.get('gpt4o_latency', 0):.3f}s"
        lat_mini = f"{row.get('mini_latency', 0):.3f}s"
        
        line = f"{p_str:<{w_text}} | {g4o_str:<{w_text}} | {mini_str:<{w_text}} | {lat_g4o:<{w_num}} | {lat_mini:<{w_num}}"
        table_lines.append(line)

    return "\n".join(table_lines)


# ---------------------------------------------------------------------------
# Entry point for manual testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_prompt = "Explain the difference between temperature and top_p in one sentence."
    print("=== Comparing models ===")
    result = compare_models(test_prompt)
    for key, value in result.items():
        print(f"{key}: {value}")

    print("\n=== Starting chatbot (type 'quit' to exit) ===")
    streaming_chatbot()