import threading
import time
import logging
import concurrent.futures
from typing import Dict, Any, Optional

from .audio_utils import ThreadSafeCounter, html_to_plain_text
from .tts_adapter import TTSAdapter
from app.core.modules.adapters.tts import RealTimeTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceAssistant:
    def __init__(self, language_processor, max_concurrent_requests: int = 5):
        self.language_processor = language_processor
        self.conversation_context = {}
        self.max_concurrent_requests = max_concurrent_requests
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent_requests,
            thread_name_prefix="VoiceAssistant"
        )
        self.active_requests = {}
        self.request_counter = ThreadSafeCounter()
        self.request_lock = threading.RLock()
        self.shutdown_event = threading.Event()
        
        self.tts_instance = RealTimeTTS(language="English", speaker="Jenny")
        self.tts_instance.enable_auto_language_detection(True)
        self.tts_adapter = TTSAdapter(self.tts_instance, max_workers=3)
        self.tts_adapter.add_completion_callback(self._on_tts_completion)
        

    
    def _on_tts_completion(self, task_id: str, audio_path: str):
        pass
        
    def _process_transcription_task(self, request_id: str, transcription: str, include_audio: bool) -> dict:
        try:

            
            start_time = time.time()
            
            response = self.language_processor.process_query(
                user_input=transcription,
                context=self.conversation_context.copy()
            )
            

            
            with self.request_lock:
                self.conversation_context.update({
                    'last_query': transcription,
                    'last_response': response,
                    'last_processed_time': time.time()
                })
            
            response_text = response.get("text", "") if isinstance(response, dict) else str(response)
            result = {"text": response_text}
            
            if include_audio:
                try:
                    audio_start_time = time.time()
                    tts_text = html_to_plain_text(response_text)
                    audio_file_path = self.tts_adapter.speak_text(tts_text, priority=1, timeout=20.0)
                    
                    result["audio_file"] = audio_file_path or ""
                    
                except Exception as tts_error:
                    logger.error(f"Request {request_id}: TTS Error: {tts_error}")
                    result["audio_file"] = ""
                    result["tts_error"] = str(tts_error)
            

            
            return result
            
        except Exception as e:
            logger.error(f"Request {request_id}: Error in transcription processing: {str(e)}")
            error_response = "I apologize, but I encountered an error processing your request."
            
            result = {"text": error_response, "error": str(e)}
            
            if include_audio:
                try:
                    audio_file_path = self.tts_adapter.speak_text(error_response, priority=2)
                    result["audio_file"] = audio_file_path or ""
                except Exception as tts_error:
                    logger.error(f"Request {request_id}: TTS Error in error handling: {tts_error}")
                    result["audio_file"] = ""
            
            return result
        
        finally:
            with self.request_lock:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
    
    def handle_transcription_with_audio_async(self, transcription: str) -> str:
        return self._handle_transcription_async(transcription, include_audio=True)
    
    def handle_transcription_only_async(self, transcription: str) -> str:
        return self._handle_transcription_async(transcription, include_audio=False)
    
    def _handle_transcription_async(self, transcription: str, include_audio: bool) -> str:
        if self.shutdown_event.is_set():
            raise Exception("VoiceAssistant is shutting down")
        
        request_id = f"req_{self.request_counter.increment()}"
        
        future = self.executor.submit(
            self._process_transcription_task,
            request_id,
            transcription,
            include_audio
        )
        
        with self.request_lock:
            self.active_requests[request_id] = {
                'future': future,
                'transcription': transcription,
                'include_audio': include_audio,
                'start_time': time.time()
            }
        

        return request_id
    
    def get_request_result(self, request_id: str, timeout: float = 30.0) -> Optional[dict]:
        with self.request_lock:
            if request_id not in self.active_requests:
                logger.warning(f"Request {request_id} not found")
                return None
            
            future = self.active_requests[request_id]['future']
        
        try:
            result = future.result(timeout=timeout)
            return result
        except concurrent.futures.TimeoutError:
            logger.error(f"Request {request_id} timed out after {timeout}s")
            return {"text": "Request timed out", "error": "timeout"}
        except Exception as e:
            logger.error(f"Request {request_id} failed: {str(e)}")
            return {"text": "Request failed", "error": str(e)}
    
    def handle_transcription_with_audio(self, transcription: str) -> dict:
        request_id = self.handle_transcription_with_audio_async(transcription)
        return self.get_request_result(request_id) or {"text": "Processing failed", "audio_file": ""}
    
    def handle_transcription_only(self, transcription: str) -> dict:
        request_id = self.handle_transcription_only_async(transcription)
        return self.get_request_result(request_id) or {"text": "Processing failed"}
    
    def get_active_request_count(self) -> int:
        with self.request_lock:
            return len(self.active_requests)
    
    def get_request_status(self, request_id: str) -> Optional[str]:
        with self.request_lock:
            if request_id not in self.active_requests:
                return None
            
            future = self.active_requests[request_id]['future']
            
            if future.done():
                if future.exception():
                    return "failed"
                else:
                    return "completed"
            else:
                return "processing"
    
    def cancel_request(self, request_id: str) -> bool:
        with self.request_lock:
            if request_id not in self.active_requests:
                return False
            
            future = self.active_requests[request_id]['future']
            success = future.cancel()
            
            if success:
                del self.active_requests[request_id]
            
            return success            
        
    def start_conversation(self) -> None:
        if self.shutdown_event.is_set():
            self.shutdown_event.clear()
        
        self.tts_adapter.start()
    
    def stop_conversation(self) -> None:
        self.shutdown_event.set()
        
        with self.request_lock:
            active_request_ids = list(self.active_requests.keys())
            for request_id in active_request_ids:
                self.cancel_request(request_id)
        
        self.tts_adapter.stop()
        
        self.executor.shutdown(wait=True)
    
    def set_language_context(self, context: Dict[str, Any]) -> None:
        with self.request_lock:
            self.conversation_context.update(context)
    
    def get_statistics(self) -> Dict[str, Any]:
        with self.request_lock:
            stats = {
                'active_requests': len(self.active_requests),
                'total_requests_processed': self.request_counter._value,
                'tts_queue_size': self.tts_adapter.get_queue_size(),
                'tts_active_tasks': self.tts_adapter.get_active_task_count(),
                'is_running': not self.shutdown_event.is_set()
            }
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        health = {
            'voice_assistant': not self.shutdown_event.is_set(),
            'tts_adapter': self.tts_adapter.is_initialized,
            'executor': not self.executor._shutdown,
            'active_requests': self.get_active_request_count(),
            'timestamp': time.time()
        }
        
        health['overall_healthy'] = all([
            health['voice_assistant'],
            health['tts_adapter'],
            health['executor']
        ])
        
        return health
