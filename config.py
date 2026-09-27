from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    app_name: str = "Futuristic AI Assistant"
    openai_api_key: Optional[str] = None  # Set via environment or config
    voice_engine: str = "pyttsx3"  # or 'edge-tts', 'gtts'
    listen_wake_word: bool = False
    tts_rate: int = 150
    tts_volume: float = 1.0

config = Config()
