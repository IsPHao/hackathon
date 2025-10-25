from typing import Dict, Any, Optional, Type, Union
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from .exceptions import ParseError, APIError

logger = logging.getLogger(__name__)


async def call_llm_json(
    llm: BaseChatModel,
    prompt_template: Union[str, ChatPromptTemplate],
    variables: Optional[Dict[str, Any]] = None,
    system_role: str = "You are a professional assistant.",
    pydantic_model: Optional[Type[BaseModel]] = None,
    parse_error_class: Optional[Type[Exception]] = None,
    api_error_class: Optional[Type[Exception]] = None,
) -> Dict[str, Any]:
    """
    Call LLM with structured JSON output using LangChain utilities.
    
    Args:
        llm: Language model to use for the call
        prompt_template: LangChain ChatPromptTemplate or template string
        variables: Variables to substitute in template
        system_role: System role message
        pydantic_model: Optional Pydantic model for structured output
        parse_error_class: Custom exception class for parse errors
        api_error_class: Custom exception class for API errors
    
    Returns:
        Dict[str, Any]: Parsed JSON response
    
    Raises:
        ParseError: If JSON parsing fails
        APIError: If LLM API call fails
    """
    try:
        # Create prompt template if string provided
        if isinstance(prompt_template, str):
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_role),
                ("human", prompt_template)
            ])
        else:
            prompt = prompt_template
        
        # Use with_structured_output if Pydantic model provided
        if pydantic_model:
            structured_llm = llm.with_structured_output(pydantic_model)
            chain = prompt | structured_llm
            result = await chain.ainvoke(variables or {})
            # Convert Pydantic model to dict
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump()  # type: ignore
            elif hasattr(result, 'dict'):
                result_dict = result.dict()  # type: ignore
            else:
                # If it's already a dict, return as is
                result_dict = dict(result) if not isinstance(result, dict) else result
            return result_dict
        else:
            # Use JsonOutputParser for generic JSON
            parser = JsonOutputParser()
            chain = prompt | llm | parser
            
            # Invoke chain
            result = await chain.ainvoke(variables or {})
            return result
    
    except Exception as e:
        logger.error(f"LLM JSON call failed: {e}")
        
        # Determine error type
        if "parse" in str(e).lower() or "json" in str(e).lower():
            error_class = parse_error_class or ParseError
            raise error_class(f"Failed to parse JSON response: {e}") from e
        elif api_error_class is not None:
            raise api_error_class(f"LLM API call failed: {e}") from e
        else:
            # Check if the exception is already an APIError
            if isinstance(e, APIError):
                raise
            else:
                raise APIError(f"LLM API call failed: {e}") from e