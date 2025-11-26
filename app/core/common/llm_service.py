import json
from typing import Dict, Any, List, Optional, Union
from groq import Groq, AsyncGroq
from app.Config import ENV_SETTINGS

class LLMService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.api_key = ENV_SETTINGS.GROQ_API_KEY
        self.model = getattr(ENV_SETTINGS, 'MODEL_ID', 'openai/gpt-oss-20b')
        self.client = Groq(api_key=self.api_key)
        self.async_client = AsyncGroq(api_key=self.api_key)
        self._initialized = True

    def get_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: Optional[str] = None,
                       temperature: float = 0.1,
                       response_format: Optional[Dict[str, str]] = None,
                       max_tokens: Optional[int] = None) -> Any:
        try:
            completion = self.client.chat.completions.create(
                messages=messages,
                model=model or self.model,
                temperature=temperature,
                response_format=response_format,
                max_tokens=max_tokens
            )
            
            content = completion.choices[0].message.content
            
            if response_format and response_format.get("type") == "json_object":
                return json.loads(content)
            return content
            
        except Exception as e:
            print(f"Error in LLM completion: {e}")
            raise e

    async def get_completion_async(self, 
                                   messages: List[Dict[str, str]], 
                                   model: Optional[str] = None,
                                   temperature: float = 0.1,
                                   response_format: Optional[Dict[str, str]] = None,
                                   max_tokens: Optional[int] = None) -> Any:
        try:
            completion = await self.async_client.chat.completions.create(
                messages=messages,
                model=model or self.model,
                temperature=temperature,
                response_format=response_format,
                max_tokens=max_tokens
            )
            
            content = completion.choices[0].message.content
            
            if response_format and response_format.get("type") == "json_object":
                return json.loads(content)
            return content
            
        except Exception as e:
            print(f"Error in async LLM completion: {e}")
            raise e
