import os
import time
import threading
import queue
import uuid
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except Exception:
    pyaudio = None
    PYAUDIO_AVAILABLE = False
import wave
import asyncio
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv
from app.Config import ENV_SETTINGS
from .tts_utils import LANGUAGE_DICT, DEFAULT_SPEAKERS, detect_language

load_dotenv()

DEFAULT_LANGUAGE = "Hindi"
DEFAULT_SPEAKER = "Swara"
DEFAULT_CHUNK_SIZE = 4096
DEFAULT_MAX_WORKERS = 3
DEFAULT_TTS_TIMEOUT = 30.0
TASK_CLEANUP_AGE_SECONDS = 300

class RealTimeTTS:
    def __init__(self, api_key=None, language=DEFAULT_LANGUAGE, speaker=DEFAULT_SPEAKER, max_workers=DEFAULT_MAX_WORKERS):
        self.language = language
        self.speaker = speaker
        self.CHUNK = DEFAULT_CHUNK_SIZE
        self.text_queue = queue.Queue()
        self.is_running = False
        self.p = pyaudio.PyAudio() if PYAUDIO_AVAILABLE else None
        self.playback_finished_callback = None
        self.is_playing = False
        self.last_audio_file_path = None
        self.auto_detect_language = True
        
        self.max_workers = max_workers
        self.executor = None
        self.active_tasks = []
        self.task_lock = threading.Lock()
        
        # Enhanced tracking
        self.task_counter = 0
        self.task_results = {}
        self.task_completion_callbacks = {}
        self.result_lock = threading.RLock()
        self.pending_tasks = {}
        
    def detect_language(self, text):
        return detect_language(text)
        
    def set_playback_finished_callback(self, callback):
        self.playback_finished_callback = callback
    
    def enable_auto_language_detection(self, enable=True):
        self.auto_detect_language = enable
    
    def convert_text_and_get_path(self, text, timeout=DEFAULT_TTS_TIMEOUT):
        self.ensure_tts_ready()
        try:
            future = self.executor.submit(self._process_single_text, text)
            return future.result(timeout=timeout)
        except Exception as e:
            print(f"Error in convert_text_and_get_path: {e}")
            return None
    
    def convert_text_with_language(self, text, language=None, speaker=None):
        self.ensure_tts_ready()
        
        if language and speaker:
            original_auto_detect = self.auto_detect_language
            original_language = self.language
            original_speaker = self.speaker
            
            self.auto_detect_language = False
            self.language = language
            self.speaker = speaker
            
            try:
                future = self.executor.submit(self._process_single_text, text)
                result = future.result(timeout=30)
                audio_file_path = result
            except Exception as e:
                print(f"Error in convert_text_with_language: {e}")
                audio_file_path = None
            
            self.auto_detect_language = original_auto_detect
            self.language = original_language
            self.speaker = original_speaker
            
            return audio_file_path
        else:
            try:
                future = self.executor.submit(self._process_single_text, text)
                return future.result(timeout=DEFAULT_TTS_TIMEOUT)
            except Exception as e:
                print(f"Error in convert_text_with_language: {e}")
                return None
    
    async def _text_to_speech_elevenlabs(self, text):
        if self.auto_detect_language:
            detected_language = self.detect_language(text)
            current_speaker = DEFAULT_SPEAKERS[detected_language]
            print(f"Auto-detected language: {detected_language}, using speaker: {current_speaker}")
        else:
            detected_language = self.language
            current_speaker = self.speaker
            print(f"Using configured language: {detected_language}, speaker: {current_speaker}")
        
        voice_id = LANGUAGE_DICT[detected_language][current_speaker]
        
        if not ENV_SETTINGS.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY not found in environment settings")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ENV_SETTINGS.ELEVENLABS_API_KEY
        }
        
        data = {
            "text": text,
            "model_id": ENV_SETTINGS.ELEVENLABS_MODEL_ID,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        loop = asyncio.get_event_loop()
        
        def make_request():
            response = requests.post(url, json=data, headers=headers)
            if response.status_code != 200:
                raise Exception(f"ElevenLabs API error: {response.text}")
            return response.content

        audio_content = await loop.run_in_executor(None, make_request)
        
        audio_dir = Path("static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        unique_filename = f"{uuid.uuid4().hex}.mp3"
        audio_file_path = audio_dir / unique_filename
        
        with open(audio_file_path, "wb") as f:
            f.write(audio_content)
            
        return str(audio_file_path)

    def stop_tts(self):
        self.is_running = False
        
        with self.task_lock:
            for future in self.active_tasks:
                future.cancel()
            self.active_tasks.clear()
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        if self.p:
            self.p.terminate()

    def add_text(self, text):
        if text.strip():
            self.text_queue.put(text.strip())
    
    def add_multiple_texts(self, texts):
        for text in texts:
            if text.strip():
                self.text_queue.put(text.strip())
    
    def process_texts_concurrently(self, texts, wait_for_completion=False):
        if not self.executor:
            raise RuntimeError("TTS not initialized. Call initialize_tts() or ensure_tts_ready() first.")
        
        futures = []
        for text in texts:
            if text.strip():
                future = self.executor.submit(self._process_single_text, text.strip())
                with self.task_lock:
                    self.active_tasks.append(future)
                futures.append(future)
        
        if wait_for_completion:
            audio_files = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        audio_files.append(result)
                except Exception as e:
                    print(f"Error processing text: {e}")
            return audio_files
        
        return futures
    
    def wait_for_all_tasks(self, timeout=None):
        with self.task_lock:
            active_tasks = self.active_tasks.copy()
        
        if not active_tasks:
            return True
        
        try:
            for future in as_completed(active_tasks, timeout=timeout):
                pass
            return True
        except Exception as e:
            print(f"Error waiting for tasks: {e}")
            return False
    
    def get_active_task_count(self):
        with self.task_lock:
            return len([task for task in self.active_tasks if not task.done()])
    
    def set_max_workers(self, max_workers):
        if self.executor:
            self.executor.shutdown(wait=False)
        
        self.max_workers = max_workers
        if self.is_running:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
    
    def get_thread_pool_status(self):
        if not self.executor:
            return {"status": "not_initialized", "max_workers": self.max_workers}
        
        active_count = self.get_active_task_count()
        return {
            "status": "running" if self.is_running else "stopped",
            "max_workers": self.max_workers,
            "active_tasks": active_count,
            "queue_size": self.text_queue.qsize()
        }
    
    def _cleanup_completed_tasks(self):
        with self.task_lock:
            self.active_tasks = [task for task in self.active_tasks if not task.done()]
    
    def _process_single_text(self, text):
        try:
            self.is_playing = True
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_file_path = loop.run_until_complete(self._text_to_speech_elevenlabs(text))
            loop.close()
            
            print(f'Generated audio file: {audio_file_path}')
            self.last_audio_file_path = audio_file_path
            
            self.is_playing = False
            
            if self.playback_finished_callback:
                def delayed_callback():
                    time.sleep(0.3)
                    self.playback_finished_callback()
                
                callback_thread = threading.Thread(target=delayed_callback)
                callback_thread.daemon = True
                callback_thread.start()
            
            return audio_file_path
            
        except Exception as e:
            print(f"TTS error: {e}")
            self.is_playing = False
            if self.playback_finished_callback:
                self.playback_finished_callback()
            return None
        finally:
            self._cleanup_completed_tasks()
    
    def get_last_audio_file_path(self):
        return self.last_audio_file_path
    
    def clear_last_audio_file(self):
        if self.last_audio_file_path and os.path.exists(self.last_audio_file_path):
            try:
                os.unlink(self.last_audio_file_path)
                self.last_audio_file_path = None
                return True
            except Exception as e:
                print(f"Error deleting audio file: {e}")
                return False
        return False
    
    def process_batch_with_callback(self, texts, callback=None, max_concurrent=None):
        if not self.executor:
            raise RuntimeError("TTS not initialized. Call initialize_tts() or ensure_tts_ready() first.")
        
        if max_concurrent is None:
            max_concurrent = self.max_workers
        
        results = []
        completed_count = 0
        total_count = len([t for t in texts if t.strip()])
        
        batch_size = min(max_concurrent, total_count)
        text_batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        
        for batch in text_batches:
            batch_futures = []
            for text in batch:
                if text.strip():
                    future = self.executor.submit(self._process_single_text, text.strip())
                    with self.task_lock:
                        self.active_tasks.append(future)
                    batch_futures.append((text, future))
            
            for text, future in batch_futures:
                try:
                    result = future.result()
                    completed_count += 1
                    results.append({
                        'text': text,
                        'audio_file': result,
                        'success': result is not None,
                        'error': None
                    })
                    
                    if callback:
                        callback(completed_count, total_count, result)
                        
                except Exception as e:
                    completed_count += 1
                    results.append({
                        'text': text,
                        'audio_file': None,
                        'success': False,
                        'error': str(e)
                    })
                    
                    if callback:
                        callback(completed_count, total_count, None)
        
        return results

    def initialize_tts(self):
        if not self.executor:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.is_running = True
        print("TTS initialized for programmatic use.")
    
    def ensure_tts_ready(self):
        if not self.executor or not self.is_running:
            self.initialize_tts()
    
    def generate_task_id(self):
        with self.result_lock:
            self.task_counter += 1
            return f"tts_task_{self.task_counter}_{int(time.time() * 1000)}"
    
    def convert_text_synchronized(self, text, task_id=None, language=None, speaker=None):
        if not text or not text.strip():
            return None
            
        if task_id is None:
            task_id = self.generate_task_id()
        
        self.ensure_tts_ready()
        
        original_settings = None
        if language and speaker:
            original_settings = {
                'auto_detect': self.auto_detect_language,
                'language': self.language,
                'speaker': self.speaker
            }
            self.auto_detect_language = False
            self.language = language
            self.speaker = speaker
        
        try:
            future = self.executor.submit(self._process_single_text_synchronized, text.strip(), task_id)
            
            with self.result_lock:
                self.pending_tasks[task_id] = future
                self.task_results[task_id] = None
            
            print(f"TTS task {task_id} submitted for text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            return task_id
            
        except Exception as e:
            print(f"Error submitting TTS task {task_id}: {e}")
            with self.result_lock:
                self.task_results[task_id] = {"error": str(e), "audio_file": None}
            return task_id
        finally:
            if original_settings:
                self.auto_detect_language = original_settings['auto_detect']
                self.language = original_settings['language']
                self.speaker = original_settings['speaker']
    
    def get_audio_file_for_task(self, task_id, timeout=DEFAULT_TTS_TIMEOUT):
        if not task_id:
            return None
            
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self.result_lock:
                if task_id in self.task_results:
                    result = self.task_results[task_id]
                    
                    if result is None:
                        time.sleep(0.1)
                        continue
                    
                    if isinstance(result, dict) and "error" in result:
                        print(f"TTS task {task_id} failed: {result['error']}")
                        return None
                    
                    if isinstance(result, str):
                        print(f"TTS task {task_id} completed: {result}")
                        return result
                        
            time.sleep(0.1)
        
        print(f"Timeout waiting for TTS task {task_id}")
        return None
    
    def _process_single_text_synchronized(self, text, task_id):
        try:
            print(f"Processing TTS task {task_id}: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            if self.auto_detect_language:
                detected_language = self.detect_language(text)
                current_speaker = DEFAULT_SPEAKERS[detected_language]
                print(f"Task {task_id}: Auto-detected language: {detected_language}, speaker: {current_speaker}")
            else:
                detected_language = self.language
                current_speaker = self.speaker
                print(f"Task {task_id}: Using configured language: {detected_language}, speaker: {current_speaker}")
            
            voice_id = LANGUAGE_DICT[detected_language][current_speaker]
            
            async def generate_audio():
                if not ENV_SETTINGS.ELEVENLABS_API_KEY:
                    raise ValueError("ELEVENLABS_API_KEY not found")

                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": ENV_SETTINGS.ELEVENLABS_API_KEY
                }
                data = {
                    "text": text,
                    "model_id": ENV_SETTINGS.ELEVENLABS_MODEL_ID,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
                }
                
                loop = asyncio.get_event_loop()
                def make_request():
                    response = requests.post(url, json=data, headers=headers)
                    if response.status_code != 200:
                        raise Exception(f"ElevenLabs API error: {response.text}")
                    return response.content

                audio_content = await loop.run_in_executor(None, make_request)
                
                audio_dir = Path("static/audio")
                audio_dir.mkdir(parents=True, exist_ok=True)
                unique_filename = f"{task_id}_{uuid.uuid4().hex}.mp3"
                audio_file_path = audio_dir / unique_filename
                
                with open(audio_file_path, "wb") as f:
                    f.write(audio_content)
                return str(audio_file_path)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_file_path = loop.run_until_complete(generate_audio())
            loop.close()
            
            with self.result_lock:
                self.task_results[task_id] = audio_file_path
                if task_id in self.pending_tasks:
                    del self.pending_tasks[task_id]
            
            print(f'Task {task_id} completed: Generated audio file: {audio_file_path}')
            
            self.last_audio_file_path = audio_file_path
            
            if self.playback_finished_callback:
                def delayed_callback():
                    time.sleep(0.3)
                    self.playback_finished_callback()
                
                callback_thread = threading.Thread(target=delayed_callback)
                callback_thread.daemon = True
                callback_thread.start()
            
            return audio_file_path
            
        except Exception as e:
            print(f"TTS error for task {task_id}: {e}")
            
            with self.result_lock:
                self.task_results[task_id] = {"error": str(e), "audio_file": None}
                if task_id in self.pending_tasks:
                    del self.pending_tasks[task_id]
            
            if self.playback_finished_callback:
                self.playback_finished_callback()
            
            return None
        finally:
            self._cleanup_completed_tasks()
    
    def cleanup_completed_tasks_synchronized(self):
        with self.result_lock:
            current_time = time.time()
            tasks_to_remove = []
            
            for task_id, result in self.task_results.items():
                try:
                    timestamp_str = task_id.split('_')[-1]
                    task_timestamp = int(timestamp_str) / 1000
                    
                    if current_time - task_timestamp > TASK_CLEANUP_AGE_SECONDS and result is not None:
                        tasks_to_remove.append(task_id)
                except (ValueError, IndexError):
                    if result is not None:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.task_results[task_id]
                if task_id in self.task_completion_callbacks:
                    del self.task_completion_callbacks[task_id]
            
            if tasks_to_remove:
                print(f"Cleaned up {len(tasks_to_remove)} completed TTS tasks")
    
    def get_task_status(self, task_id):
        with self.result_lock:
            if task_id in self.pending_tasks:
                future = self.pending_tasks[task_id]
                if future.done():
                    return "completed" if not future.exception() else "failed"
                return "processing"
            elif task_id in self.task_results:
                result = self.task_results[task_id]
                if result is None:
                    return "pending"
                elif isinstance(result, dict) and "error" in result:
                    return "failed"
                return "completed"
            return "unknown"
    
    def cancel_task(self, task_id):
        with self.result_lock:
            if task_id in self.pending_tasks:
                future = self.pending_tasks[task_id]
                if not future.done():
                    cancelled = future.cancel()
                    if cancelled:
                        del self.pending_tasks[task_id]
                        self.task_results[task_id] = {"error": "Task cancelled", "audio_file": None}
                        return True
            return False