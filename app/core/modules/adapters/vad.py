import struct
import math
import time

class VoiceActivityDetector:
    def __init__(self, threshold: float = 0.02, min_duration: float = 1.0, silence_duration: float = 2.0):
        self.threshold = threshold
        self.min_duration = min_duration
        self.silence_duration = silence_duration
        self.is_voice_active = False
        self.voice_start_time = 0
        self.last_voice_time = 0
        self.voice_buffer = []
        self.buffer_size = 10
    
    def detect_voice_activity(self, audio_data: bytes) -> tuple[bool, bool]:
        try:
            audio_values = struct.unpack(f'{len(audio_data)//2}h', audio_data)
            rms = math.sqrt(sum(x*x for x in audio_values) / len(audio_values))
            normalized_rms = rms / 32768.0 
            
            self.voice_buffer.append(normalized_rms)
            if len(self.voice_buffer) > self.buffer_size:
                self.voice_buffer.pop(0)
            
            avg_rms = sum(self.voice_buffer) / len(self.voice_buffer)
            
            current_time = time.time()
            has_voice = avg_rms > self.threshold
            
            if has_voice and len(self.voice_buffer) >= 3:
                recent_above_threshold = sum(1 for x in self.voice_buffer[-3:] if x > self.threshold)
                has_voice = recent_above_threshold >= 2
            
            if has_voice:
                if not self.is_voice_active:
                    self.is_voice_active = True
                    self.voice_start_time = current_time
                self.last_voice_time = current_time
                return True, False
            else:
                if self.is_voice_active:
                    if (current_time - self.last_voice_time) > self.silence_duration:
                        if (self.last_voice_time - self.voice_start_time) > self.min_duration:
                            self.is_voice_active = False
                            return False, True
                        else:
                            self.is_voice_active = False
                            return False, False
                    return False, False
                return False, False
                    
        except Exception as e:
            return True, False
    
    def reset(self) -> None:
        self.is_voice_active = False
        self.voice_start_time = 0
        self.last_voice_time = 0
        self.voice_buffer = []
