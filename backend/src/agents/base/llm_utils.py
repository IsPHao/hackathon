from typing import Dict, Any, Optional, Type, Union
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

from .exceptions import ParseError, APIError

logger = logging.getLogger(__name__)


class LLMJSONMixin:
    """
    Mixin providing LLM JSON calling capabilities using LangChain utilities.
    
    Uses LangChain's ChatPromptTemplate for prompt management and
    JsonOutputParser for structured output parsing.
    """
    
    async def _call_llm_json(
        self,
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
                structured_llm = self.llm.with_structured_output(pydantic_model)
                chain = prompt | structured_llm
                result = await chain.ainvoke(variables or {})
                # Convert Pydantic model to dict
                return result.model_dump() if hasattr(result, 'model_dump') else result.dict()
            else:
                # Use JsonOutputParser for generic JSON
                parser = JsonOutputParser()
                chain = prompt | self.llm | parser
                
                # Invoke chain
                result = await chain.ainvoke(variables or {})
                return result
        
        except Exception as e:
            logger.error(f"LLM JSON call failed: {e}")
            
            # Determine error type
            if "parse" in str(e).lower() or "json" in str(e).lower():
                error_class = parse_error_class or ParseError
                raise error_class(f"Failed to parse JSON response: {e}") from e
            else:
                error_class = api_error_class or APIError
                raise error_class(f"LLM API call failed: {e}") from e
