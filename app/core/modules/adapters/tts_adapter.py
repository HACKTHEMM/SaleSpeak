import threading
import time
import queue
import logging
from typing import Optional, Callable

from .audio_utils import TaskStatus, AudioTask, ThreadSafeCounter, AudioProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_TTS_TIMEOUT = 15.0
DEFAULT_WAIT_TIMEOUT = 30.0

class TTSAdapter(AudioProcessor):
    def __init__(self, tts_instance, max_workers: int = 3, max_queue_size: int = 50):
        self.tts_instance = tts_instance
        self.is_initialized = False
        self.is_speaking = False
        self.max_workers = max_workers
        self.task_counter = ThreadSafeCounter()
        self.task_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.active_tasks = {}
        self.completed_tasks = {}
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.stop_event = threading.Event()
        self.queue_processor_thread = None
        self.completion_callbacks = []
        
    def add_completion_callback(self, callback: Callable[[str, str], None]):
        with self.lock:
            self.completion_callbacks.append(callback)    
    
    def _queue_processor(self):
        while not self.stop_event.is_set():
            try:
                try:
                    priority, task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                if task is None:
                    break
                
                with self.lock:
                    task.status = TaskStatus.PROCESSING
                    self.active_tasks[task.task_id] = task
                

                
                try:
                    audio_path = self._process_tts_task(task)
                    
                    with self.lock:
                        task.status = TaskStatus.COMPLETED
                        task.result = audio_path
                        self.completed_tasks[task.task_id] = task
                        if task.task_id in self.active_tasks:
                            del self.active_tasks[task.task_id]
                    
                    for callback in self.completion_callbacks:
                        try:
                            callback(task.task_id, audio_path)
                        except Exception as e:
                            logger.error(f"Error in completion callback: {e}")
                    

                    
                except Exception as e:
                    with self.lock:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        self.completed_tasks[task.task_id] = task
                        if task.task_id in self.active_tasks:
                            del self.active_tasks[task.task_id]
                    
                    logger.error(f"TTS task {task.task_id} failed: {e}")
                
                finally:
                    self.task_queue.task_done()
                    with self.condition:
                        self.condition.notify_all()
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
    
    def _process_tts_task(self, task: AudioTask) -> Optional[str]:
        try:
            safe_text = task.text if isinstance(task.text, str) else str(task.text)
            
            if hasattr(self.tts_instance, 'convert_text_synchronized'):
                tts_task_id = self.tts_instance.convert_text_synchronized(safe_text)
                
                if tts_task_id:
                    audio_path = self.tts_instance.get_audio_file_for_task(tts_task_id, timeout=DEFAULT_TTS_TIMEOUT)
                    
                    if audio_path:
                        return audio_path
                    else:
                        logger.warning(f"TTS task {task.task_id} timed out or failed")
                        return None
                else:
                    logger.error(f"Failed to submit TTS task {task.task_id}")
                    return None
            else:
                logger.warning("Using fallback TTS method - synchronization may be affected")
                safe_text = task.text if isinstance(task.text, str) else str(task.text)
                self.tts_instance.add_text(safe_text)
                
                max_wait = DEFAULT_TTS_TIMEOUT
                wait_interval = 0.1
                total_waited = 0
                
                while total_waited < max_wait and not self.stop_event.is_set():
                    audio_path = self.tts_instance.get_last_audio_file_path()
                    if audio_path:
                        return audio_path
                    
                    time.sleep(wait_interval)
                    total_waited += wait_interval
                    
                    if (hasattr(self.tts_instance, 'text_queue') and 
                        self.tts_instance.text_queue.empty() and 
                        not getattr(self.tts_instance, 'is_playing', False)):
                        
                        audio_path = self.tts_instance.get_last_audio_file_path()
                        if audio_path:
                            return audio_path
                
                logger.warning(f"Timeout waiting for audio generation for task {task.task_id}")
                return None
            
        except Exception as e:
            logger.error(f"Error processing TTS task {task.task_id}: {e}")
            raise
    
    def speak_text_async(self, text: str, priority: int = 0) -> str:
        if not self.is_initialized:
            self._initialize_tts()
        
        task_id = f"tts_{self.task_counter.increment()}"
        task = AudioTask(
            task_id=task_id,
            text=text,
            priority=priority
        )
        
        try:
            self.task_queue.put((-priority, task), timeout=1.0)
            
            with self.lock:
                self.active_tasks[task_id] = task
            
            return task_id
            
        except queue.Full:
            logger.error("TTS queue is full, cannot add new task")
            raise Exception("TTS queue is full")
    
    def speak_text(self, text: str, priority: int = 0, timeout: float = DEFAULT_WAIT_TIMEOUT) -> Optional[str]:
        task_id = self.speak_text_async(text, priority)
        return self.wait_for_task(task_id, timeout)
    
    def wait_for_task(self, task_id: str, timeout: float = DEFAULT_WAIT_TIMEOUT) -> Optional[str]:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self.lock:
                if task_id in self.completed_tasks:
                    task = self.completed_tasks[task_id]
                    if task.status == TaskStatus.COMPLETED:
                        return task.result
                    elif task.status == TaskStatus.FAILED:
                        logger.error(f"Task {task_id} failed: {task.error}")
                        return None
                
                with self.condition:
                    self.condition.wait(timeout=0.5)
        
        logger.warning(f"Timeout waiting for task {task_id}")
        return None
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        with self.lock:
            if task_id in self.active_tasks:
                return self.active_tasks[task_id].status
            elif task_id in self.completed_tasks:
                return self.completed_tasks[task_id].status
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        with self.lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.FAILED
                    task.error = "Cancelled by user"
                    self.completed_tasks[task_id] = task
                    del self.active_tasks[task_id]
                    return True
            return False
    
    def get_queue_size(self) -> int:
        return self.task_queue.qsize()
    
    def get_active_task_count(self) -> int:
        with self.lock:
            return len(self.active_tasks)    
    
    def _on_playback_finished(self):
        with self.lock:
            self.is_speaking = False
    
    def _initialize_tts(self) -> None:
        if self.is_initialized:
            return
        
        if hasattr(self.tts_instance, 'initialize_tts'):
            self.tts_instance.initialize_tts()
        else:
            self.tts_instance.is_running = True
        
        self.queue_processor_thread = threading.Thread(
            target=self._queue_processor, 
            daemon=True,
            name="TTS-QueueProcessor"
        )
        self.queue_processor_thread.start()
        
        self.is_initialized = True
    
    def process(self, text: str) -> Optional[str]:
        return self.speak_text(text)
    
    def start(self) -> None:
        self._initialize_tts()
    
    def stop(self) -> None:
        if not self.is_initialized:
            return
        
        self.stop_event.set()
        
        try:
            self.task_queue.put((-999, None), timeout=1.0)
        except queue.Full:
            pass
        
        if self.queue_processor_thread and self.queue_processor_thread.is_alive():
            self.queue_processor_thread.join(timeout=5.0)
        
        if hasattr(self.tts_instance, 'stop_tts'):
            self.tts_instance.stop_tts()
        
        with self.lock:
            while not self.task_queue.empty():
                try:
                    self.task_queue.get_nowait()
                    self.task_queue.task_done()
                except queue.Empty:
                    break
            
            self.active_tasks.clear()
            self.completed_tasks.clear()
            self.is_initialized = False
            self.is_speaking = False
