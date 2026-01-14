"""
Production FastAPI Application
Voice AI Service with WebSocket and REST API
"""
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config.settings import settings
from core.pipeline import AIPipeline
from core.connection_manager import manager
from models.schemas import *
from utils.logger import setup_logger
from utils.exceptions import AIServiceException
from routers import broadcast_tts

logger = setup_logger(__name__)

# Initialize pipeline
pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global pipeline
    
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")
    
    try:
        pipeline = AIPipeline()
        logger.info("✓ AI Pipeline initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize pipeline: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await manager.close_all()
    logger.info("✓ Shutdown complete")

# Initialize FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler
@app.exception_handler(AIServiceException)
async def ai_exception_handler(request, exc: AIServiceException):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": exc.message,
            "code": exc.code
        }
    )

# Health check
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    health = pipeline.health_check()
    
    return {
        "status": "healthy" if all(health.values()) else "degraded",
        "timestamp": datetime.now(timezone.utc),
        "services": health,
        "version": settings.APP_VERSION
    }


# @app.get("/", response_model=HealthResponse)
# async def root():
#     health = pipeline.health_check()
#     return {
#         "status": "healthy" if all(health.values()) else "degraded",
#         "timestamp": datetime.now(timezone.utc).isoformat(),  # convert to string
#         "services": health,
#         "version": settings.APP_VERSION
#     }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    health = pipeline.health_check()
    
    return {
        "status": "healthy" if all(health.values()) else "degraded",
        "services": health,
        "connections": manager.get_connection_count(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# REST API Endpoints

@app.post("/process-audio")
async def process_audio(audio: UploadFile = File(...), language: str = "en"):
    """
    Process audio file through complete pipeline
    Audio → STT → AI → TTS → Response
    """
    try:
        audio_data = await audio.read()
        call_id = f"rest_{datetime.now(timezone.utc).timestamp()}"
        
        result = await pipeline.process_audio(audio_data, call_id, language)
        
        return result
        
    except Exception as e:
        logger.error(f"Process audio error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-text")
async def process_text(data: dict):
    """
    Process text input (skip STT)
    Text → AI → TTS → Response
    """
    try:
        text = data.get("text")
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        call_id = data.get("call_id", f"rest_{datetime.now(timezone.utc).timestamp()}")
        
        result = await pipeline.process_text(text, call_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Process text error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/test-stt")
# async def test_stt(audio: UploadFile = File(...), language: str = "en"):
#     """Test STT only"""
#     try:
#         audio_data = await audio.read()
#         result = await pipeline.stt.transcribe_audio(audio_data, language)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/test-ai")
# async def test_ai(data: dict):
#     """Test AI only"""
#     try:
#         message = data.get("message", "Hello")
#         call_id = data.get("call_id", "test")
#         result = await pipeline.ai.get_response(message, call_id)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/test-tts")
# async def test_tts(data: dict):
#     """Test TTS only"""
#     try:
#         text = data.get("text", "Hello, this is a test.")
#         result = await pipeline.tts.text_to_speech_bytes(text)
#         if result["success"]:
#             return {
#                 "success": True,
#                 "audio_base64": result["audio_data"].hex(),
#                 "format": result["format"]
#             }
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/voices")
async def list_voices(language: str = "en"):
    """List available TTS voices"""
    try:
        voices = await pipeline.tts.list_voices(language)
        return {"voices": voices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-conversation/{call_id}")
async def reset_conversation(call_id: str):
    """Reset conversation history for a call"""
    pipeline.reset_conversation(call_id)
    return {"success": True, "call_id": call_id}

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    return {
        "active_connections": manager.get_connection_count(),
        "total_calls": len(pipeline.ai.conversation_history),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# WebSocket endpoint

@app.websocket("/ws/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    """
    WebSocket endpoint for real-time voice processing
    Handles bidirectional streaming audio
    """
    await manager.connect(websocket, call_id)
    logger.info(f"WebSocket connected: {call_id}")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            logger.info(f"[{call_id}] Received: {message_type}")
            
            if message_type == "audio_chunk":
                # Process audio
                audio_hex = data.get("audio")
                audio_bytes = bytes.fromhex(audio_hex)
                
                # Process through pipeline
                result = await pipeline.process_audio(audio_bytes, call_id) # edge-tts==6.1.9 # FREE Microsoft TTS (better quality than pyttsx3)
                # pyttsx3==2.90 # Fallback option
                
                if result["success"]:
                    # Send transcription
                    await manager.send_message(call_id, {
                        "type": "transcription",
                        "text": result["transcription"],
                        "call_id": call_id
                    })
                    
                    # Send AI response text
                    await manager.send_message(call_id, {
                        "type": "ai_response",
                        "text": result["ai_response"],
                        "call_id": call_id
                    })
                    
                    # Send audio response
                    await manager.send_message(call_id, {
                        "type": "audio_response",
                        "audio": result["audio_data"],
                        "format": result["audio_format"],
                        "call_id": call_id
                    })
                else:
                    # Send error
                    await manager.send_message(call_id, {
                        "type": "error",
                        "error": result.get("error", "Unknown error"),
                        "call_id": call_id
                    })
            
            elif message_type == "text_message":
                # Process text directly
                text = data.get("text")
                result = await pipeline.process_text(text, call_id)
                
                if result["success"]:
                    await manager.send_message(call_id, {
                        "type": "ai_response",
                        "text": result["ai_response"],
                        "audio": result["audio_data"],
                        "format": result["audio_format"],
                        "call_id": call_id
                    })
            
            elif message_type == "reset":
                # Reset conversation
                pipeline.reset_conversation(call_id)
                await manager.send_message(call_id, {
                    "type": "reset_complete",
                    "call_id": call_id
                })
            
            elif message_type == "ping":
                # Respond to ping
                await manager.send_message(call_id, {
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            elif message_type == "end_call":
                logger.info(f"Call ended by client: {call_id}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {call_id}")
    except Exception as e:
        logger.error(f"WebSocket error [{call_id}]: {str(e)}")
    finally:
        manager.disconnect(call_id)
        pipeline.reset_conversation(call_id)

# Register routers
app.include_router(broadcast_tts.router)

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )