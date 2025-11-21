import threading
import time
import re
import html as html_unescape
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Any

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AudioTask:
    task_id: str
    text: str
    priority: int = 0
    timestamp: float = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

def html_to_plain_text(value: str) -> str:
    try:
        if not isinstance(value, str):
            value = str(value)
        text = value
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</li>", "\n", text)
        text = re.sub(r"(?i)<li>\s*", "- ", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = html_unescape.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception:
        return str(value)

class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:
            self._value += 1
            return self._value

class AudioProcessor(ABC):
    @abstractmethod
    def process(self, data: Any) -> Any:
        pass
    
    @abstractmethod
    def start(self) -> None:
        pass
    
    @abstractmethod
    def stop(self) -> None:
        pass

