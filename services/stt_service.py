"""
Production STT Service with Whisper
Includes error handling, caching, and performance optimization
"""
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

import io
import time
from functools import lru_cache
from config.settings import settings
from utils.logger import setup_logger
from utils.exceptions import STTException

logger = setup_logger(__name__)

class STTService:
    """Speech-to-Text service using OpenAI Whisper"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern for model caching"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load Whisper model with error handling"""
        if not WHISPER_AVAILABLE:
            logger.error("Whisper module not available - STT service disabled")
            self._model = None
            return
            
        try:
            logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
            self._model = whisper.load_model(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE
            )
            logger.info("✓ Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise STTException(f"Model loading failed: {str(e)}")
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = None
    ) -> dict:
        """
        Transcribe audio bytes to text
        
        Args:
            audio_data: Audio file bytes
            language: Language code (optional)
        
        Returns:
            dict with transcription results
        """
        start_time = time.time()
        
        # Check if required modules are available
        if not WHISPER_AVAILABLE:
            error_msg = "Whisper STT service not available - module not installed"
            logger.error(error_msg)
            return {
                "success": False,
                "text": "",
                "language": "",
                "duration": time.time() - start_time,
                "error": error_msg
            }
        
        if not NUMPY_AVAILABLE:
            error_msg = "NumPy module not available - STT service disabled"
            logger.error(error_msg)
            return {
                "success": False,
                "text": "",
                "language": "",
                "duration": time.time() - start_time,
                "error": error_msg
            }
        
        if not SOUNDFILE_AVAILABLE:
            error_msg = "SoundFile module not available - STT service disabled"
            logger.error(error_msg)
            return {
                "success": False,
                "text": "",
                "language": "",
                "duration": time.time() - start_time,
                "error": error_msg
            }
        
        if self._model is None:
            error_msg = "Whisper model not loaded - STT service disabled"
            logger.error(error_msg)
            return {
                "success": False,
                "text": "",
                "language": "",
                "duration": time.time() - start_time,
                "error": error_msg
            }
        
        try:
            # Convert bytes to numpy array
            audio_io = io.BytesIO(audio_data)
            audio_np, sample_rate = sf.read(audio_io)
            
            # Preprocess audio
            audio_np = self._preprocess_audio(audio_np, sample_rate)
            
            # Transcribe
            language = language or settings.WHISPER_LANGUAGE
            logger.info(f"Transcribing audio (length: {len(audio_np)/sample_rate:.2f}s)")
            
            result = self._model.transcribe(
                audio_np,
                language=language,
                fp16=False  # CPU compatibility
            )
            
            transcription = result["text"].strip()
            duration = time.time() - start_time
            
            logger.info(f"✓ Transcribed in {duration:.2f}s: {transcription[:50]}...")
            
            return {
                "success": True,
                "text": transcription,
                "language": result.get("language", language),
                "duration": duration,
                "confidence": self._calculate_confidence(result)
            }
            
        except Exception as e:
            logger.error(f"STT Error: {str(e)}")
            return {
                "success": False,
                "text": "",
                "language": "",
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def _preprocess_audio(self, audio_np: np.ndarray, sample_rate: int) -> np.ndarray:
        """Preprocess audio for Whisper"""
        try:
            # Convert to mono if stereo
            if len(audio_np.shape) > 1:
                audio_np = audio_np.mean(axis=1)
            
            # Convert to float32
            if audio_np.dtype != np.float32:
                audio_np = audio_np.astype(np.float32)
            
            # Normalize to [-1, 1]
            max_val = np.abs(audio_np).max()
            if max_val > 0:
                audio_np = audio_np / max_val
            
            # Resample if needed (Whisper expects 16kHz)
            if sample_rate != 16000:
                from scipy import signal
                audio_np = signal.resample(
                    audio_np,
                    int(len(audio_np) * 16000 / sample_rate)
                )
            
            return audio_np
            
        except Exception as e:
            logger.error(f"Audio preprocessing error: {e}")
            raise STTException(f"Audio preprocessing failed: {str(e)}")
    
    def _calculate_confidence(self, result: dict) -> float:
        """Calculate confidence score from Whisper result"""
        try:
            # Whisper doesn't provide direct confidence
            # We can estimate based on language probability
            if "language_probability" in result:
                return result["language_probability"]
            return 0.95  # Default high confidence
        except:
            return 0.0
    
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
        return (WHISPER_AVAILABLE and 
                NUMPY_AVAILABLE and 
                SOUNDFILE_AVAILABLE and 
                self._model is not None)