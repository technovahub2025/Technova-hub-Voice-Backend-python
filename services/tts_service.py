"""
Production TTS Service with FREE Microsoft Edge TTS
Edge TTS provides high-quality, natural voices for free
Fallback functionality has been disabled
"""
import asyncio
import edge_tts
import io
import time
from pathlib import Path
from config.settings import settings
from utils.logger import setup_logger
from utils.exceptions import TTSException

logger = setup_logger(__name__)

class TTSService:
    """Text-to-Speech using Microsoft Edge TTS (FREE) - Fallback disabled"""
    
    # Popular Edge TTS voices
    VOICES = {
        # Tamil voices
        "ta-IN-male": "ta-IN-ValluvarNeural",
        "ta-IN-female": "ta-IN-PallaviNeural",
        
        # British English voices
        "en-GB-male": "en-GB-RyanNeural",
        "en-GB-female": "en-GB-SoniaNeural",
        
        # Other voices (commented out)
        # "en-US-male": "en-US-GuyNeural",
        # "en-US-female": "en-US-AriaNeural",
        # "en-IN-male": "en-IN-PrabhatNeural",
        # "en-IN-female": "en-IN-NeerjaNeural",
    }
    
    def __init__(self):
        self.voice = settings.TTS_VOICE
        self.rate = settings.TTS_RATE
        self.volume = settings.TTS_VOLUME
        self.use_edge_tts = True
        self.fallback_service = None
        self.edge_tts_failures = 0
        self.max_failures = 3
        
        # Fallback disabled
        logger.info(f"✓ TTS Service initialized (Edge TTS: {self.voice})")
    
    async def text_to_speech_bytes(
        self,
        text: str,
        voice: str = None,
        rate: str = None,
        volume: str = None
    ) -> dict:
        """
        Convert text to speech and return audio bytes
        With automatic fallback to pyttsx3 when Edge TTS fails
        
        Args:
            text: Text to convert
            voice: Voice ID (optional, uses default)
            rate: Speech rate adjustment (e.g., "+10%", "-20%")
            volume: Volume adjustment (e.g., "+50%", "-10%")
        
        Returns:
            dict with audio data and metadata
        """
        start_time = time.time()
        
        # Try Edge TTS first if enabled and under failure threshold
        if self.use_edge_tts and self.edge_tts_failures < self.max_failures:
            try:
                voice = voice or self.voice
                rate = rate or self.rate
                volume = volume or self.volume
                
                logger.info(f"Converting text to speech (Edge TTS): {text[:50]}...")
                
                # Create communicate object
                communicate = edge_tts.Communicate(
                    text,
                    voice,
                    rate=rate,
                    volume=volume
                )
                
                # Generate audio
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                
                duration = time.time() - start_time
                
                # Reset failure count on success
                self.edge_tts_failures = 0
                
                logger.info(f"✓ Edge TTS completed in {duration:.2f}s ({len(audio_data)} bytes)")
                
                return {
                    "success": True,
                    "audio_data": audio_data,
                    "format": "mp3",  # Edge TTS outputs MP3
                    "duration": duration,
                    "provider": "edge_tts"
                }
                
            except Exception as e:
                error_msg = str(e)
                self.edge_tts_failures += 1
                
                if "403" in error_msg:
                    logger.error(f"❌ Edge TTS 403 Forbidden: {error_msg}")
                    logger.warning(f"Edge TTS failures: {self.edge_tts_failures}/{self.max_failures}")
                else:
                    logger.error(f"Edge TTS Error: {error_msg}")
                
                # Disable Edge TTS if too many failures
                if self.edge_tts_failures >= self.max_failures:
                    logger.warning("🔄 Disabling Edge TTS due to repeated failures, switching to fallback")
                    self.use_edge_tts = False
        
        # Edge TTS failed - return error
        return {
            "success": False,
            "error": f"TTS service unavailable. Edge TTS failures: {self.edge_tts_failures}",
            "duration": time.time() - start_time,
            "provider": "none"
        }
    
    async def text_to_speech_file(
        self,
        text: str,
        output_path: str,
        voice: str = None
    ) -> dict:
        """
        Convert text to speech and save to file
        
        Args:
            text: Text to convert
            output_path: Path to save audio file
            voice: Voice ID (optional)
        
        Returns:
            dict with success status and file path
        """
        start_time = time.time()
        
        try:
            voice = voice or self.voice
            
            logger.info(f"Generating speech file: {output_path}")
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            
            duration = time.time() - start_time
            
            logger.info(f"✓ Audio saved to {output_path} in {duration:.2f}s")
            
            return {
                "success": True,
                "file_path": output_path,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"TTS File Error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    async def list_voices(self, language: str = "en") -> list:
        """
        List available voices for a language
        
        Args:
            language: Language code (e.g., "en", "es", "fr")
        
        Returns:
            List of available voices
        """
        try:
            voices = await edge_tts.list_voices()
            filtered = [
                {
                    "name": v["Name"],
                    "gender": v["Gender"],
                    "locale": v["Locale"],
                    "short_name": v["ShortName"]
                }
                for v in voices
                if v["Locale"].startswith(language)
            ]
            return filtered
        except Exception as e:
            logger.error(f"List voices error: {e}")
            return []
    
    def set_voice(self, voice: str):
        """Change voice"""
        self.voice = voice
        logger.info(f"Voice changed to: {voice}")
    
    def set_rate(self, rate: str):
        """Change speech rate (e.g., '+10%', '-20%')"""
        self.rate = rate
        logger.info(f"Speech rate changed to: {rate}")
    
    def set_volume(self, volume: str):
        """Change volume (e.g., '+50%', '-10%')"""
        self.volume = volume
        logger.info(f"Volume changed to: {volume}")
    
    def health_check(self) -> dict:
        """Check if service is healthy"""
        return {
            "edge_tts_available": self.use_edge_tts and self.edge_tts_failures < self.max_failures,
            "fallback_available": False,
            "edge_tts_failures": self.edge_tts_failures,
            "max_failures": self.max_failures,
            "current_provider": "edge_tts" if self.use_edge_tts else "none"
        }
    
    def reset_edge_tts(self):
        """Reset Edge TTS failure count and re-enable"""
        self.edge_tts_failures = 0
        self.use_edge_tts = True
        logger.info("🔄 Edge TTS reset and re-enabled")
