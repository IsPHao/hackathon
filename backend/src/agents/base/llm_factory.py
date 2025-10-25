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
    
    Raises:
        ValueError: If required parameters are invalid
        Exception: If LLM initialization fails
    """
    if not model or not model.strip():
        raise ValueError("Model name cannot be empty")
    
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    if temperature < 0 or temperature > 2:
        raise ValueError(f"Temperature must be between 0 and 2, got {temperature}")
    
    config = {
        "model": model,
        "api_key": api_key,
        "temperature": temperature,
    }
    
    if base_url:
        config["base_url"] = base_url
    
    try:
        return ChatOpenAI(**config)
    except Exception as e:
        raise Exception(f"Failed to initialize ChatOpenAI with model '{model}': {e}") from e
