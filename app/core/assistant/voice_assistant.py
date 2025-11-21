import os
import sys
import concurrent.futures
import threading
from queue import Queue
from typing import Optional
from dotenv import load_dotenv
from app.core.modules.adapters.stt import EnhancedRealTimeTranscriber
from app.core.modules.adapters.tts import RealTimeTTS
from app.core.modules.llm.language_processor import LanguageProcessor, QueryClassifier
from app.core.modules.adapters.audio_interface import TTSAdapter, VoiceAssistant
from app.Config import ENV_SETTINGS

load_dotenv()
class IntegratedVoiceAssistant:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, groq_api_key: Optional[str] = None, max_workers: int = 4):
        with self._lock:
            if not hasattr(self, 'is_initialized'):
                self.groq_api_key = groq_api_key or ENV_SETTINGS.GROQ_API_KEY
                if not self.groq_api_key:
                    raise ValueError("GROQ_API_KEY is required. Set it in your .env file or pass it as parameter.")
                self.stt_instance = None
                self.language_processor = None
                self.query_classifier = None
                self.voice_assistant = None
                self.is_initialized = False
                self.max_workers = max_workers
                self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
                self.processing_queue = Queue()
                self.shutdown_event = threading.Event()
                self._initialize_components()
        

    def _initialize_components(self) -> None:
        if self.is_initialized:
            return
            
        try:
            init_tasks = {}
            
            def init_language_processor():
                return LanguageProcessor(
                    api_key=self.groq_api_key,
                    model_name=getattr(ENV_SETTINGS, 'MODEL_ID', None)
                )
            init_tasks['language_processor'] = self.thread_pool.submit(init_language_processor)
            
            self.language_processor = init_tasks['language_processor'].result()
            
            def init_query_classifier():
                return QueryClassifier(self.language_processor)
            
            def init_voice_assistant():
                return VoiceAssistant(self.language_processor)
            
            init_tasks['query_classifier'] = self.thread_pool.submit(init_query_classifier)
            init_tasks['voice_assistant'] = self.thread_pool.submit(init_voice_assistant)
            
            self.query_classifier = init_tasks['query_classifier'].result()
            self.voice_assistant = init_tasks['voice_assistant'].result()
            
            self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.processing_thread.start()
            
            self.is_initialized = True
            
        except Exception as e:       
            sys.exit(1)

    def _process_queue(self):
        while not self.shutdown_event.is_set():
            try:
                if not self.processing_queue.empty():
                    task, args, kwargs = self.processing_queue.get(timeout=0.5)
                    self.thread_pool.submit(task, *args, **kwargs)
                else:
                    self.shutdown_event.wait(0.1)
            except Exception as e:
                continue

    def get_voice_assistant(self) -> VoiceAssistant:
        if not self.is_initialized:
            self._initialize_components()
        return self.voice_assistant
    
    def run(self) -> None:
        try:
            def setup_prompt():
                self.language_processor.set_system_prompt(
                    """You are a friendly and persuasive sales agent with a natural, human-like conversational style.
                        Provide engaging responses that build rapport and gently guide the conversation toward solutions and products.
                        Use casual language, occasional verbal fillers, and conversational transitions like a real sales professional would.
                        Keep responses concise as they will be spoken aloud. When discussing products, highlight benefits rather than features.
                        
                        IMPORTANT: You will receive context from multiple sources including REAL-TIME WEB CONTEXT from web searches.
                        When web context is provided, use it confidently to answer user questions with current, factual information.
                        Do not say you don't have information if web context contains the answer.
                        
                        If asked about actions you cannot perform, politely explain your limitations while suggesting alternatives."""
                )
            
            prompt_future = self.thread_pool.submit(setup_prompt)
            
            prompt_future.result()
            
            self.voice_assistant.start_conversation()
            
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
            self.stop()
        except Exception as e:
            print(f"Error running voice assistant: {e}")
            self.stop()
    
    def run_with_context(self, context: dict) -> None:
        try:
            context_future = self.thread_pool.submit(self.voice_assistant.set_language_context, context)
            context_future.result()
            self.run()
        except Exception as e:
            self.stop()

    def stop(self) -> None:
        self.shutdown_event.set()
        if self.voice_assistant:
            self.voice_assistant.stop_conversation()
        
        self.thread_pool.shutdown(wait=True)
    
    def get_language_processor(self) -> LanguageProcessor:
        return self.language_processor
    
    def get_query_classifier(self) -> QueryClassifier:
        return self.query_classifier

    def process_async(self, task, *args, **kwargs):
        self.processing_queue.put((task, args, kwargs))
        return True
