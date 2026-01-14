"""
Production STT Service with Groq (Lightweight)
Replaces heavy local Whisper with efficient Cloud API
"""
import io
import time
from groq import Groq
from config.settings import settings
from utils.logger import setup_logger
from utils.exceptions import STTException

logger = setup_logger(__name__)

class STTService:
    """Speech-to-Text service using Groq API (distil-whisper-large-v3-en)"""
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
             logger.error("GROQ_API_KEY not found. STT will fail.")
             # raise STTException("GROQ_API_KEY not configured")
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info(f"✓ STT Service initialized (Groq: {settings.WHISPER_MODEL})")
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = None
    ) -> dict:
        """
        Transcribe audio bytes using Groq API
        """
        start_time = time.time()
        
        try:
            # Prepare file for Groq API
            # Groq expects a tuple (filename, file_bytes)
            audio_file = ("audio.wav", audio_data)
            
            logger.info("Transcribing audio with Groq...")
            
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model=settings.WHISPER_MODEL, # e.g. distil-whisper-large-v3-en
                language=language or "en",
                response_format="json"
            )
            
            text = transcription.text.strip()
            duration = time.time() - start_time
            
            logger.info(f"✓ Transcribed in {duration:.2f}s: {text[:50]}...")
            
            return {
                "success": True,
                "text": text,
                "language": language or "en",
                "duration": duration,
                "confidence": 1.0 # Groq doesn't send confidence in simple JSON
            }
            
        except Exception as e:
            logger.error(f"Groq STT Error: {str(e)}")
            return {
                "success": False,
                "text": "",
                "language": "",
                "duration": time.time() - start_time,
                "error": str(e)
            }

    async def transcribe_file(self, file_path: str, language: str = None) -> dict:
        """Transcribe audio from file path"""
        try:
            with open(file_path, 'rb') as f:
                audio_data = f.read()
            return await self.transcribe_audio(audio_data, language)
        except Exception as e:
            logger.error(f"File read error: {str(e)}")
            raise STTException(f"File read failed: {str(e)}")
    
    def health_check(self) -> bool:
        """Check if service is healthy"""
        return bool(settings.GROQ_API_KEY)