"""
Centralized Configuration Management
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, List
import os
from pathlib import Path
import json

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "AI Voice Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 4000
    
    # AI API Keys (FREE options)
    GROQ_API_KEY: Optional[str] = None          # FREE: https://console.groq.com
    MISTRAL_API_KEY: Optional[str] = None       # Paid alternative
    
    # STT Configuration
    WHISPER_MODEL: str = "distil-whisper-large-v3-en" # Groq Cloud Model
    WHISPER_DEVICE: str = "cpu"                 # Ignored for Cloud STT
    WHISPER_LANGUAGE: str = "en"
    
    # AI Configuration
    AI_PROVIDER: str = "groq"                   # groq or mistral
    AI_MODEL: str = "llama-3.1-8b-instant"        # Groq: FREE, fast
    AI_MAX_TOKENS: int = 150
    AI_TEMPERATURE: float = 0.7
    AI_TIMEOUT: int = 30
    
    # TTS Configuration
    TTS_PROVIDER: str = "edge"                  # edge (FREE) or pyttsx3
    TTS_VOICE: str = "en-US-AriaNeural"         # Edge TTS voice
    TTS_RATE: str = "+0%"                       # Speech rate
    TTS_VOLUME: str = "+0%"                     # Volume
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100
    WS_MESSAGE_QUEUE_SIZE: int = 100
    
    # Audio Processing
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_FORMAT: str = "wav"
    
    # Performance
    MAX_WORKERS: int = 4
    REQUEST_TIMEOUT: int = 60
    MAX_CONCURRENT_REQUESTS: int = 10
    
    # Caching (optional)
    ENABLE_CACHE: bool = False
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 3600
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"                    # json or text
    LOG_DIR: str = "logs"
    
    # Security
    CORS_ORIGINS_RAW: str = "*"                 # Raw str from env; maps to CORS_ORIGINS
    API_KEY_HEADER: str = "X-API-Key"
    ENABLE_AUTH: bool = False
    
    # Monitoring
    ENABLE_METRICS: bool = False
    METRICS_PORT: int = 9090
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parsed CORS origins as list[str] for FastAPI usage."""
        raw = self.CORS_ORIGINS_RAW
        if not raw:
            return ["*"]
        
        raw = raw.strip()
        if raw == "*":
            return ["*"]
        
        try:
            # Try JSON (e.g., '["http://localhost"]')
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(o) for o in parsed if o]
            raise ValueError("Must be a list")
        except (json.JSONDecodeError, ValueError):
            # Fallback: comma-separated (e.g., 'a.com,b.com')
            origins = [o.strip() for o in raw.split(',') if o.strip()]
            if origins:
                return origins
            else:
                print(f"Warning: Invalid CORS_ORIGINS '{raw}'. Using default ['*'].")
                return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

# Singleton instance
settings = Settings()

# Create required directories
Path(settings.LOG_DIR).mkdir(exist_ok=True)
Path("models").mkdir(exist_ok=True)