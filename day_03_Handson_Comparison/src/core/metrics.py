def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate the estimated cost based on the model and token usage.
    Returns cost in USD.
    """
    model_pricing = {
        "gpt-4o": {"input": 0.005 / 1000, "output": 0.015 / 1000},
        "gpt-4o-mini": {"input": 0.00015 / 1000, "output": 0.0006 / 1000},
        "gemini-1.5-flash": {"input": 0.000075 / 1000, "output": 0.00030 / 1000},
        "gemini-1.5-pro": {"input": 0.0035 / 1000, "output": 0.0105 / 1000},
    }

    # Default to 0 for local or unknown models
    pricing = model_pricing.get(model_name.lower(), {"input": 0.0, "output": 0.0})
    
    input_cost = prompt_tokens * pricing["input"]
    output_cost = completion_tokens * pricing["output"]
    
    return input_cost + output_cost

def calculate_token_ratio(prompt_tokens: int, completion_tokens: int) -> float:
    """
    Returns the ratio of prompt tokens to total tokens.
    Higher ratio means the prompt is significantly larger than the generation (expected in extraction/classification).
    """
    total = prompt_tokens + completion_tokens
    if total == 0:
        return 0.0
    return prompt_tokens / total
