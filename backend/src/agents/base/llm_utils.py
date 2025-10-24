from typing import Dict, Any, Optional, Type
import json
import logging

from .exceptions import ParseError, APIError

logger = logging.getLogger(__name__)


class LLMJSONMixin:
    
    async def _call_llm_json(
        self,
        prompt: str,
        system_role: str = "You are a professional assistant.",
        parse_error_class: Optional[Type[Exception]] = None,
        api_error_class: Optional[Type[Exception]] = None,
    ) -> Dict[str, Any]:
        try:
            messages = [
                ("system", system_role),
                ("human", prompt),
            ]
            
            response = await self.llm.ainvoke(
                messages,
                response_format={"type": "json_object"},
            )
            
            return json.loads(response.content)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            error_class = parse_error_class or ParseError
            raise error_class(f"Invalid JSON response: {e}") from e
        
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            error_class = api_error_class or APIError
            raise error_class(f"Failed to call LLM API: {e}") from e
