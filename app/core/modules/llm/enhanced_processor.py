import time
import hashlib
import threading
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from .processor import LanguageProcessor

class EnhancedLanguageProcessor(LanguageProcessor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.web_cache = {}
        self.web_cache_ttl = 3600
        
        self.enhanced_thread_pool = ThreadPoolExecutor(
            max_workers=min(6, self.max_workers + 2), 
            thread_name_prefix="Enhanced-Worker"
        )
        self.cache_cleanup_thread = None
        self._start_cache_cleanup_thread()
    
    def _start_cache_cleanup_thread(self):
        def cleanup_cache():
            while not self.thread_pool._shutdown:
                try:
                    current_time = time.time()
                    with self.web_cache_lock:
                        expired_keys = [
                            key for key, entry in self.web_cache.items()
                            if current_time - entry['timestamp'] > self.web_cache_ttl
                        ]
                        for key in expired_keys:
                            del self.web_cache[key]
                    
                    time.sleep(300)
                except Exception as e:
                    print(f"Error in cache cleanup: {e}")
        
        self.cache_cleanup_thread = threading.Thread(target=cleanup_cache, daemon=True)
        self.cache_cleanup_thread.start()
    
    def process_with_multi_context(self, user_input: str, context_names: List[str] = None,
                                  max_items_per_context: int = 2, use_web_context: bool = True) -> str:
        # Now only uses web context, context_names parameter kept for backward compatibility
        return self.process_query(user_input, use_web_context=use_web_context)
    
    def get_cached_web_context(self, query_key: str) -> Optional[Dict[str, Any]]:
        if query_key in self.web_cache:
            cache_entry = self.web_cache[query_key]
            if time.time() - cache_entry['timestamp'] < self.web_cache_ttl:
                return cache_entry['data']
            else:
                del self.web_cache[query_key]
        return None
    
    def cache_web_context(self, query_key: str, web_data: Dict[str, Any]) -> None:
        self.web_cache[query_key] = {
            'data': web_data,
            'timestamp': time.time()
        }
    
    def process_with_cached_web_context(self, user_input: str, **kwargs) -> str:
        query_key = hashlib.md5(user_input.lower().encode()).hexdigest()
        
        cached_context = self.get_cached_web_context(query_key)

        result = self.process_query(user_input, **kwargs)
        
        if kwargs.get('use_web_context', True) and self.use_web_scraper:
            try:
                web_data = self.get_web_context_for_query(user_input)
                if web_data.get('success', False):
                    self.cache_web_context(query_key, web_data)
            except Exception as e:
                print(f"Error caching web context: {e}")
        
        return result
    
    def shutdown(self):
        if hasattr(self, 'enhanced_thread_pool'):
            self.enhanced_thread_pool.shutdown(wait=True)
    
        super().shutdown()
        
