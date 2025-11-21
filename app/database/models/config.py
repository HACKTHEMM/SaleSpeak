from dataclasses import dataclass
from typing import Optional, Dict, Any
from app.Config import ENV_SETTINGS

@dataclass
class AudioConfig:
    chunk_size: int = 4096
    audio_format: int = 16
    channels: int = 1
    sample_rate: int = 16000
    record_seconds: float = 3.0
    silence_threshold: float = 0.01
    min_voice_duration: float = 0.5

@dataclass
class STTConfig:
    model: str = "whisper-large-v3-turbo"
    response_format: str = "json"
    temperature: float = 0.0
    language: Optional[str] = None

@dataclass
class TTSConfig:
    model: str = "playai-tts"
    voice: str = "Basil-PlayAI"
    response_format: str = "wav"
    speed: float = 1.0

@dataclass
class LLMConfig:
    model: str = "mixtral-8x7b-32768"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

@dataclass
class VoiceAssistantConfig:
    groq_api_key: Optional[str] = None
    
    audio: AudioConfig = None
    stt: STTConfig = None
    tts: TTSConfig = None
    llm: LLMConfig = None
    
    assistant_name: str = "AI Voice Assistant"
    wake_word: Optional[str] = None
    max_conversation_history: int = 10
    response_timeout: float = 30.0
    
    default_system_prompt: str = """You are a friendly and persuasive sales agent with a natural, human-like conversational style.
        Provide engaging responses that build rapport and gently guide the conversation toward solutions and products.
        Use casual language, occasional verbal fillers, and conversational transitions like a real sales professional would.
        Keep responses concise as they will be spoken aloud. When discussing products, highlight benefits rather than features.
        If asked about actions you cannot perform, politely explain your limitations while suggesting alternatives."""
    
    debug_mode: bool = False
    log_conversations: bool = False
    log_file_path: Optional[str] = None
    
    def __post_init__(self):
        if self.audio is None:
            self.audio = AudioConfig()
        if self.stt is None:
            self.stt = STTConfig()
        if self.tts is None:
            self.tts = TTSConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        
        if self.groq_api_key is None:
            self.groq_api_key = ENV_SETTINGS.GROQ_API_KEY

class ConfigManager:
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> VoiceAssistantConfig:
        config = VoiceAssistantConfig()
        
        self._load_from_environment(config)
        
        if self.config_path and os.path.exists(self.config_path):
            self._load_from_file(config)
        
        self._validate_config(config)
        
        return config
    
    def _load_from_environment(self, config: VoiceAssistantConfig) -> None:
        config.groq_api_key = ENV_SETTINGS.GROQ_API_KEY
    
    def _load_from_file(self, config: VoiceAssistantConfig) -> None:
        pass
    
    def _validate_config(self, config: VoiceAssistantConfig) -> None:
        if not config.groq_api_key:
            raise ValueError("GROQ_API_KEY is required but not found in environment variables or config")
        
        if config.audio.chunk_size <= 0:
            raise ValueError("Audio chunk size must be positive")
        
        if config.audio.sample_rate <= 0:
            raise ValueError("Audio sample rate must be positive")
        
        if config.llm.temperature < 0 or config.llm.temperature > 2:
            raise ValueError("LLM temperature must be between 0 and 2")
        
        if config.llm.max_tokens <= 0:
            raise ValueError("LLM max tokens must be positive")
    
    def get_config(self) -> VoiceAssistantConfig:
        return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        pass
    
    def save_config(self, file_path: str) -> None:
        pass

_config_manager = None

def get_config() -> VoiceAssistantConfig:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.get_config()

def set_config(config_path: str) -> None:
    global _config_manager
    _config_manager = ConfigManager(config_path)

def get_development_config() -> VoiceAssistantConfig:
    config = VoiceAssistantConfig()
    config.debug_mode = True
    config.log_conversations = True
    config.llm.temperature = 0.3
    config.audio.record_seconds = 2.0
    return config

def get_production_config() -> VoiceAssistantConfig:
    config = VoiceAssistantConfig()
    config.debug_mode = False
    config.log_conversations = False
    config.llm.temperature = 0.7
    config.audio.record_seconds = 3.0
    return config
