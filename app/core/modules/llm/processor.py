import os
import uuid
import time
import json
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, RLock
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from groq import Groq
from dotenv import load_dotenv
from app.Config import ENV_SETTINGS

from app.core.modules.web_scraper.web_scraper import (
    WebSearcher, 
    BasicQueryProcessor,
    get_web_data_for_llm
)

from .prompts import (
    get_system_prompt, get_language_reminder, get_correction_prompt, 
    CLASSIFICATION_PROMPT
)
from .language_utils import detect_input_language, contains_hindi, is_hinglish_response

load_dotenv()

class QueryClassifier:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "mixtral-8x7b-32768"):
        self.api_key = api_key or ENV_SETTINGS.GROQ_API_KEY
        self.model_name = model_name
        self.client = Groq(api_key=self.api_key)
        
    def classify(self, query: str) -> Dict[str, Any]:
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            return result
        except Exception as e:
            return {
                "category": "general",
                "requires_web_search": True,
                "requires_context": True,
                "complexity": "medium"
            }

class LanguageProcessor:    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None,
                 response_language: str = "auto", allow_mixed_language: bool = True,
                 use_web_scraper: bool = True, serpapi_key: Optional[str] = None,
                 max_workers: int = 4, enable_parallel_processing: bool = True):
        self.max_workers = max_workers
        self.enable_parallel_processing = enable_parallel_processing
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="LangProc-Worker")
        self.processing_lock = RLock()
        self.context_lock = Lock()
        self.web_cache_lock = Lock()
        
        self.processed_queries = 0
        self.error_count = 0
        self.active_futures = []
        
        self.api_key = api_key or ENV_SETTINGS.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required")
        
        self.use_web_scraper = use_web_scraper
        self.web_scraper = None
        self.query_processor = None
        
        if self.use_web_scraper:
            try:
                self.web_scraper = WebSearcher(serpapi_key)
                self.query_processor = BasicQueryProcessor()
            except Exception as e:
                self.use_web_scraper = False
        
        self.model_name = model_name or getattr(ENV_SETTINGS, 'MODEL_ID', 'mixtral-8x7b-32768')
        self.conversation_id = str(uuid.uuid4())
        self.response_language = response_language
        self.allow_mixed_language = allow_mixed_language
        
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name=self.model_name,
            temperature=0.7,
            max_tokens=4096
        )
        
        self.system_prompt = get_system_prompt(self.response_language, self.allow_mixed_language)
        
        self.conversation_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}")
        ])
        
        self.classifier = QueryClassifier(self.api_key, self.model_name)
    
    def set_response_language(self, language: str) -> None:
        self.response_language = language
        self.system_prompt = get_system_prompt(self.response_language, self.allow_mixed_language)
        self.conversation_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}")
        ])
    
    def process_query(self, user_input: str, context: Optional[Dict[str, Any]] = None,
                     force_language: Optional[str] = None,
                     use_web_context: bool = True, max_web_results: int = 3) -> str:
        try:
            if self.response_language == "auto" and not force_language:
                current_language = detect_input_language(user_input)
            else:
                current_language = force_language or self.response_language

            web_context = self._get_web_context(user_input, use_web_context, max_web_results)
            
            formatted_input = self._format_input(user_input, context, current_language, web_context)
            
            if current_language != self.response_language:
                temp_system_prompt = get_system_prompt(current_language, self.allow_mixed_language)
                temp_template = ChatPromptTemplate.from_messages([
                    ("system", temp_system_prompt),
                    ("human", "{input}")
                ])
                chain = temp_template | self.llm
            else:
                chain = self.conversation_template | self.llm
            
            response = chain.invoke({"input": formatted_input})
            response_content = response.content.strip()
            
            response_content = self._enforce_language(response_content, current_language, user_input, web_context)
            
            return response_content
            
        except Exception as e:
            return self._handle_error(e, current_language)

    def _get_web_context(self, user_input: str, use_web_context: bool, max_results: int) -> str:
        if not (self.use_web_scraper and use_web_context and self.web_scraper):
            return ""
        try:
            web_data = get_web_data_for_llm(user_input)
            if "error" not in web_data:
                context = "\n\n=== REAL-TIME WEB CONTEXT ===\n"
                context += f"[Retrieved current information for: {user_input}]\n\n"
                
                # Add quick facts first (answer boxes, knowledge graphs)
                if web_data.get("quick_facts"):
                    context += "KEY INFORMATION:\n"
                    for fact in web_data["quick_facts"]:
                        if isinstance(fact, dict):
                            for key, value in fact.items():
                                if key not in ['thumbnail', 'source']:
                                    context += f"  {key}: {value}\n"
                    context += "\n"
                
                # Add summary
                if web_data.get("summary"):
                    context += "SUMMARY FROM WEB SOURCES:\n"
                    for item in web_data["summary"][:max_results]:
                        context += f"• {item}\n"
                    context += "\n"
                
                # Add detailed results
                if web_data.get("detailed_results"):
                    context += "DETAILED INFORMATION:\n"
                    for i, item in enumerate(web_data["detailed_results"][:max_results], 1):
                        title = item.get('title', 'Source')
                        content = item.get('content', '')
                        link = item.get('link', '')
                        context += f"{i}. {title}\n   {content}\n"
                        if link:
                            context += f"   [Source: {link}]\n"
                    context += "\n"
                
                context += "[Use this current information to answer the user's question directly and confidently]\n"
                return context
            else:
                print(f"Web scraping error: {web_data.get('error')}")
                return "\n\n[Web context unavailable - API error occurred]\n"
        except Exception as e:
            print(f"Web scraping exception: {str(e)}")
            return "\n\n[Web context unavailable - exception occurred]\n"

    def _format_input(self, user_input: str, context: Optional[Dict[str, Any]], current_language: str,
                     web_context: str) -> str:
        formatted_input = user_input
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            formatted_input = f"Context:\n{context_str}\n\nUser Query: {user_input}"
        
        formatted_input += get_language_reminder(current_language, self.allow_mixed_language)
        
        if web_context: formatted_input += web_context
        
        return formatted_input

    def _enforce_language(self, response_content: str, current_language: str, user_input: str, context: str) -> str:
        if current_language == "hindi" and not self.allow_mixed_language and not contains_hindi(response_content):
            hindi_prompt = get_correction_prompt("hindi", user_input, context)
            response = self.llm.invoke([
                SystemMessage(content="You must respond in pure Hindi (हिंदी) using Devanagari script. Never use English."),
                HumanMessage(content=hindi_prompt)
            ])
            return response.content.strip()
        elif current_language == "hinglish" and not is_hinglish_response(response_content):
            hinglish_prompt = get_correction_prompt("hinglish", user_input, context)
            response = self.llm.invoke([
                SystemMessage(content="Respond in Hinglish (Hindi-English mix) as natural for Indian users. Mix languages naturally."),
                HumanMessage(content=hinglish_prompt)
            ])
            return response.content.strip()
        return response_content

    def _handle_error(self, e: Exception, current_language: str) -> str:

        
        if current_language == "hindi":
            return "क्षमा करें, आपके अनुरोध को प्रोसेस करने में त्रुटि हुई है। कृपया पुनः प्रयास करें।"
        elif current_language == "hinglish":
            return "Sorry, आपके request को process करने में error हुई है। Please फिर से try करें।"
        else:
            return "I apologize, but I encountered an error while processing your request. Please try again."
    
    def set_mixed_language_mode(self, allow_mixed: bool) -> None:
        self.allow_mixed_language = allow_mixed
        self.system_prompt = get_system_prompt(self.response_language, self.allow_mixed_language)
        self.conversation_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}")
        ])
    
    def process_hinglish_query(self, user_input: str, **kwargs) -> str:
        return self.process_query(user_input, force_language="hinglish", **kwargs)
    
    def process_hindi_query(self, user_input: str, **kwargs) -> str:
        return self.process_query(user_input, force_language="hindi", **kwargs)
    
    def process_english_query(self, user_input: str, **kwargs) -> str:
        return self.process_query(user_input, force_language="english", **kwargs)
    
    def set_conversation_id(self, conversation_id: str) -> None:
        self.conversation_id = conversation_id
    
    def set_system_prompt(self, new_prompt: str) -> None:
        self.system_prompt = new_prompt
        self.conversation_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}")
        ])
    
    def process_with_custom_prompt(self, user_input: str, custom_system_prompt: str) -> str:
        try:
            custom_template = ChatPromptTemplate.from_messages([
                ("system", custom_system_prompt),
                ("human", "{input}")
            ])
            chain = custom_template | self.llm
            response = chain.invoke({"input": user_input})
            return response.content.strip()
        except Exception as e:
            error_msg = f"Error processing query with custom prompt: {str(e)}"
            print(error_msg)
            return "I apologize, but I encountered an error while processing your request. Please try again."
    
    def get_system_status(self) -> Dict[str, Any]:
        return {
            "web_scraper_active": self.use_web_scraper and self.web_scraper is not None,
            "conversation_id": self.conversation_id,
            "response_language": self.response_language,
            "allow_mixed_language": self.allow_mixed_language,
            "web_scraper_enabled": self.use_web_scraper
        }
    
    def set_web_scraper_enabled(self, enabled: bool) -> None:
        self.use_web_scraper = enabled
    
    def process_query_with_web_priority(self, user_input: str, **kwargs) -> str:
        kwargs['use_web_context'] = True
        kwargs['max_web_results'] = kwargs.get('max_web_results', 5)
        return self.process_query(user_input, **kwargs)
    
    def process_query_without_web(self, user_input: str, **kwargs) -> str:
        kwargs['use_web_context'] = False
        return self.process_query(user_input, **kwargs)
    
    def get_web_context_for_query(self, user_input: str, max_results: int = 3) -> Dict[str, Any]:
        if not self.use_web_scraper or not self.web_scraper:
            return {"success": False, "error": "Web scraper not available"}
        try:
            web_data = get_web_data_for_llm(user_input)
            return {
                "success": "error" not in web_data,
                "context": web_data,
                "metadata": {}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def shutdown(self):
        """Shutdown thread pool"""
        self.thread_pool.shutdown(wait=True)
