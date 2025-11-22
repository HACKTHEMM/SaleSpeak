import os
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, ORJSONResponse
from loguru import logger

from app.database.models.transcript import TranscriptReq
from app.database.repositories.session_repository import session_repo

voice_assistant_logger = logger
voice_assistant_router = APIRouter()
assistant = None


def set_assistant(assistant_instance):
    global assistant
    assistant = assistant_instance
    voice_assistant_logger.info("Voice assistant instance set successfully")


def get_assistant():
    return assistant


@voice_assistant_router.post("/start-assistant/", response_class=ORJSONResponse)
async def start_assistant(data: TranscriptReq):
    start_time = time.time()

    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    try:
        assistant_start_time = time.time()
        result = await assistant.handle_transcription_with_audio(data.transcript)
        assistant_end_time = time.time()
        assistant_processing_time = assistant_end_time - assistant_start_time
        
        response_text = result.get("text", "")
        audio_file_path = result.get("audio_file", "")

        if audio_file_path:
            audio_file_path = session_repo.normalize_audio_path(audio_file_path)
            actual_audio_path = session_repo.find_audio_file(audio_file_path)
            if actual_audio_path:
                audio_file_path = actual_audio_path
            else:
                audio_file_path = ""

        session_repo.store_session_response(data.session_id, response_text, audio_file_path)
        audio_urls = session_repo.get_audio_urls(data.session_id, audio_file_path)

        end_time = time.time()
        total_execution_time = end_time - start_time

        return {
            "success": True,
            "text": response_text,
            "audio_file": audio_file_path,
            "audio_url": audio_urls["audio_url"],
            "static_audio_url": audio_urls["static_audio_url"],
            "audio_filename": os.path.basename(audio_file_path) if audio_file_path else "",
            "products": [],
            "message": "Generated response based on transcript",
            "execution_time": {
                "assistant_processing_time": assistant_processing_time,
                "total_execution_time": total_execution_time
            }
        }

    except Exception as e:
        end_time = time.time()
        total_execution_time = end_time - start_time
        voice_assistant_logger.error(f"ERROR after {total_execution_time:.3f} seconds: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start assistant: {e}")


@voice_assistant_router.post("/get-transcript", response_class=ORJSONResponse)
async def get_transcript(data: TranscriptReq):
    start_time = time.time()
    end_time = time.time()
    execution_time = end_time - start_time
    return {
        "message": "Transcript received",
        "text": data.transcript,
        "execution_time": execution_time
    }


@voice_assistant_router.get("/get-audio/{session_id}")
async def get_audio_file(session_id: str):
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="No audio file available for this session ID")

    session_data = session_repo.get_session_response(session_id)
    audio_file_path = session_data.get("audio_file", "")

    if not audio_file_path:
        raise HTTPException(status_code=404, detail="No audio file generated for this session")

    if not os.path.isabs(audio_file_path):
        audio_file_path = os.path.abspath(audio_file_path)

    if not os.path.exists(audio_file_path):
        filename = os.path.basename(audio_file_path)
        static_audio_dir = os.path.join("static", "audio")
        alternative_paths = [
            os.path.join(static_audio_dir, filename),
            os.path.abspath(os.path.join(static_audio_dir, filename)),
            os.path.join(os.getcwd(), static_audio_dir, filename)
        ]
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                audio_file_path = alt_path
                break
        else:
            raise HTTPException(status_code=404, detail="Audio file not found on server")

    return FileResponse(
        path=audio_file_path,
        media_type="audio/wav",
        filename=os.path.basename(audio_file_path),
        headers={
            "Content-Disposition": f"inline; filename={os.path.basename(audio_file_path)}",
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Access-Control-Allow-Origin": "*"
        }
    )


@voice_assistant_router.get("/get-latest-response/{session_id}", response_class=ORJSONResponse)
async def get_latest_response(session_id: str):
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="No response available for this session ID")

    response_data = session_repo.get_session_response(session_id)
    audio_file_path = response_data.get("audio_file", "")
    audio_urls = session_repo.get_audio_urls(session_id, audio_file_path)

    return {
        "success": True,
        "text": response_data.get("text", ""),
        "audio_file": audio_file_path,
        "audio_url": audio_urls["audio_url"],
        "static_audio_url": audio_urls["static_audio_url"],
        "direct_audio_endpoint": audio_urls["direct_audio_endpoint"],
        "audio_filename": response_data.get("audio_filename", ""),
        "timestamp": response_data.get("timestamp", 0),
        "message": "Response retrieved successfully"
    }


@voice_assistant_router.get("/debug-session/{session_id}", response_class=ORJSONResponse)
async def debug_session(session_id: str):
    return session_repo.get_debug_info(session_id)
