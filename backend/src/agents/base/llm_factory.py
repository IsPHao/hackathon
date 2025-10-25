from typing import Optional
from langchain_openai import ChatOpenAI


def create_novel_parser_llm(
    model: str,
    api_key: str,
    base_url: Optional[str] = None,
    temperature: float = 0.3,
) -> ChatOpenAI:
    """
    Create LLM instance for NovelParserAgent
    
    Args:
        model: Model name (e.g., "gpt-4o-mini", "gpt-4o")
        api_key: API key for the LLM service
        base_url: Optional base URL for the API (for custom endpoints)
        temperature: Temperature for LLM (default: 0.3 for stability)
    
    Returns:
        ChatOpenAI: Configured LLM instance
    """
    config = {
        "model": model,
        "api_key": api_key,
        "temperature": temperature,
    }
    
    if base_url:
        config["base_url"] = base_url
    
    return ChatOpenAI(**config)
