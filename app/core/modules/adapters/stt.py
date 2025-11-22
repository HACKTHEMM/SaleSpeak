import os
import time
import threading
import queue
import struct
import math
import tempfile
from typing import Callable, Optional, List
from groq import Groq
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except Exception:
    pyaudio = None
    PYAUDIO_AVAILABLE = False
import wave
from dotenv import load_dotenv
from app.Config import ENV_SETTINGS
from .vad import VoiceActivityDetector

load_dotenv()

WHISPER_MODEL = "whisper-large-v3-turbo"
DEFAULT_VOICE_THRESHOLD = 0.02
DEFAULT_VAD_THRESHOLD = 0.0015

class RealTimeTranscriber:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ENV_SETTINGS.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY must be provided or set as environment variable")
            
        self.client = Groq(api_key=self.api_key)
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
        self.CHANNELS = 1
        self.RATE = 16000
        self.RECORD_SECONDS = 3 
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.p = pyaudio.PyAudio() if PYAUDIO_AVAILABLE else None
        
    def start_recording(self):
        self.is_recording = True
        print("Initializing real-time transcription...")
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio is not available in this environment. Live STT cannot start.")
        recording_thread = threading.Thread(target=self._record_audio)
        recording_thread.daemon = True
        recording_thread.start()
        print("Microphone initialized. Starting transcription...")
        transcription_thread = threading.Thread(target=self._process_audio)
        transcription_thread.daemon = True
        transcription_thread.start()
        print("Real-time transcription started. Press Ctrl+C to stop.")
        print("-" * 50)
        
        try:
            while self.is_recording:
                time.sleep(0.0)
        except KeyboardInterrupt:
            self.stop_recording()
    
    def stop_recording(self):
        print("\nStopping transcription...")
        self.is_recording = False
        if self.p:
            self.p.terminate()
        print("Transcription stopped.")
    
    def _record_audio(self):
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio is not available in this environment. Live STT cannot record.")
        stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        print("Recording started...")
        while self.is_recording:
            frames = []
            for _ in range(0, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
                if not self.is_recording:
                    break
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
            if frames:
                audio_data = b''.join(frames)
                self.audio_queue.put(audio_data)
        stream.stop_stream()
        stream.close()
    
    def _process_audio(self):
        print(f'\nBegin processing the audio from realtime.')
        while self.is_recording:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    wf = wave.open(temp_file.name, 'wb')
                    wf.setnchannels(self.CHANNELS)
                    wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
                    wf.setframerate(self.RATE)
                    wf.writeframes(audio_data)
                    wf.close()
                    
                    try:
                        with open(temp_file.name, "rb") as file:
                            transcription = self.client.audio.transcriptions.create(
                                file=(temp_file.name, file.read()),
                                model=WHISPER_MODEL,
                                response_format="json",
                                temperature=ENV_SETTINGS.LLM_TEMPERATURE
                            )
                        
                        if transcription.text.strip():
                            timestamp = time.strftime("%H:%M:%S")
                            print(f"[{timestamp}] {transcription.text}")
                            
                    except Exception as e:
                        print(f"Transcription error: {e}")
                    finally:
                        os.unlink(temp_file.name)
                
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Processing error: {e}")
    
    def _has_sufficient_voice_content(self, audio_data: bytes) -> bool:
        try:
            chunk_size = 1024 * 2
            voice_chunks = 0
            total_chunks = 0
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i+chunk_size]
                if len(chunk) < chunk_size:
                    continue
                    
                try:
                    audio_values = struct.unpack(f'{len(chunk)//2}h', chunk)
                    rms = math.sqrt(sum(x*x for x in audio_values) / len(audio_values))
                    normalized_rms = rms / 32768.0
                    
                    if normalized_rms > DEFAULT_VOICE_THRESHOLD:
                        voice_chunks += 1
                    total_chunks += 1
                except:
                    continue
            
            if total_chunks == 0:
                return False
                
            voice_ratio = voice_chunks / total_chunks
            return voice_ratio >= 0.3
            
        except Exception as e:
            print(f"Voice content check error: {e}")
            return True


class EnhancedRealTimeTranscriber(RealTimeTranscriber):
    def __init__(self, api_key: str = None, callback: Optional[Callable[[str], None]] = None):
        super().__init__(api_key)
        self.transcription_callbacks: List[Callable[[str], None]] = []
        self.silence_threshold = 2.0
        self.last_transcription_time = time.time()
        self.voice_detector = VoiceActivityDetector()
        self.accumulated_audio = []
        self.is_accumulating = False
        self.is_paused = False
        
        if callback:
            self.add_transcription_callback(callback)
    
    def add_transcription_callback(self, callback: Callable[[str], None]) -> None:
        self.transcription_callbacks.append(callback)
    
    def remove_transcription_callback(self, callback: Callable[[str], None]) -> None:
        if callback in self.transcription_callbacks:
            self.transcription_callbacks.remove(callback)
    
    def clear_transcription_callbacks(self) -> None:
        self.transcription_callbacks.clear()
    
    def pause_transcription(self) -> None:
        self.is_paused = True
        print("[STT] Transcription paused")
    
    def resume_transcription(self) -> None:
        self.is_paused = False
        print("[STT] Transcription resumed")
    
    def _record_audio(self):
        stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        print("Recording started from enhanced...")
        
        while self.is_recording:
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            
            if self.voice_detector:
                has_voice, should_process = self.voice_detector.detect_voice_activity(data)
                
                if has_voice:
                    if not self.is_accumulating:
                        print("[Voice detected - recording...]")
                        self.is_accumulating = True
                        self.accumulated_audio = []
                    self.accumulated_audio.append(data)
                elif self.is_accumulating:
                    self.accumulated_audio.append(data)
                    
                    if should_process and self.accumulated_audio:
                        print("[Voice ended - processing...]")
                        combined_audio = b''.join(self.accumulated_audio)
                        self.audio_queue.put(combined_audio)
                        self.accumulated_audio = []
                        self.is_accumulating = False
            else:
                frames = [data]
                for _ in range(1, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
                    if not self.is_recording:
                        break
                    frames.append(stream.read(self.CHUNK, exception_on_overflow=False))
                
                if frames:
                    audio_data = b''.join(frames)
                    self.audio_queue.put(audio_data)
        
        print(f'stopping the stream of voice.')
        stream.stop_stream()
        stream.close()
        
    def _process_audio(self):
        print(f'\nBegin processing the audio from enhanced realtime.')
        while self.is_recording:
            try:
                if self.is_paused:
                    try:
                        self.audio_queue.get_nowait()
                        self.audio_queue.task_done()
                    except queue.Empty:
                        pass
                    time.sleep(0.1)
                    continue
                
                audio_data = self.audio_queue.get(timeout=1)
                
                if len(audio_data) < self.RATE * 2:
                    self.audio_queue.task_done()
                    continue
                
                if not self._has_sufficient_voice_content(audio_data):
                    self.audio_queue.task_done()
                    continue
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    wf = wave.open(temp_file.name, 'wb')
                    wf.setnchannels(self.CHANNELS)
                    wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
                    wf.setframerate(self.RATE)
                    wf.writeframes(audio_data)
                    wf.close()
                    
                    try:
                        with open(temp_file.name, "rb") as file:
                            transcription = self.client.audio.transcriptions.create(
                                file=(temp_file.name, file.read()),
                                model=WHISPER_MODEL,
                                response_format="json",
                                temperature=ENV_SETTINGS.LLM_TEMPERATURE
                            )
                        
                        if transcription.text.strip() and not self.is_paused:
                            timestamp = time.strftime("%H:%M:%S")
                            transcription_text = transcription.text.strip()
                            print(f"[{timestamp}] {transcription_text}")
                            print(f'\transcription_text : {transcription_text}')

                            for callback in self.transcription_callbacks:
                                try:
                                    callback(transcription_text)
                                except Exception as e:
                                    print(f"Error in transcription callback: {e}")
                            
                            self.last_transcription_time = time.time()
                            
                    except Exception as e:
                        print(f"Transcription error: {e}")
                    finally:
                        os.unlink(temp_file.name)
                
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Processing error: {e}")
    
    def start_recording_with_callback(self, callback: Callable[[str], None]) -> None:
        self.add_transcription_callback(callback)
        self.start_recording()
    
    def get_silence_duration(self) -> float:
        return time.time() - self.last_transcription_time
    
    def enable_voice_activity_detection(self, threshold: float = DEFAULT_VAD_THRESHOLD, min_duration: float = 1.0, silence_duration: float = 1.5) -> None:
        self.voice_detector = VoiceActivityDetector(threshold, min_duration, silence_duration)
    
    def disable_voice_activity_detection(self) -> None:
        self.voice_detector = None
