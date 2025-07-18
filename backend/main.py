import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import (
    FastAPI,
    UploadFile,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis

from src.api.config import get_logger
from src.minio import MinioClient
from src.mongodb import emotion_detection_collection, check_record_exists
from src.api.schemas import (
    Error,
    EmotionDetectionItem,
    VideosResponse,
    VideoError,
    UploadedVideoResponse,
)
from src.tasks import trigger_video_processing
from src.api.exceptions import APIError

logger = get_logger()
minio = MinioClient()
redis = Redis(host="localhost", port=6379)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    payload = VideoError(errors=[e.model_dump() for e in exc.errors]).model_dump()
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.get("/healthcheck")
def healthcheck():
    return {"status": "online"}


@app.get("/videos", response_model=VideosResponse)
def list_videos():
    items = list(emotion_detection_collection.find())
    if not items:
        raise HTTPException(404, "No videos found.")
    return {"videos": items, "total": len(items)}


@app.get("/videos/{video_id}", response_model=EmotionDetectionItem)
def get_video(video_id: str):
    item = emotion_detection_collection.find_one({"_id": video_id})
    if not item:
        raise HTTPException(404, "Video not found.")
    return item


@app.post(
    "/videos",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": UploadedVideoResponse},
        400: {"model": VideoError},
        409: {"model": VideoError},
    },
)
def upload_video(file: UploadFile):
    if not file.filename.lower().endswith(".mp4"):
        raise APIError(
            [
                Error(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="Invalid file format. Only .mp4 files are allowed.",
                    source="file",
                )
            ],
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if check_record_exists(file.filename):
        raise APIError(
            [
                Error(
                    code=status.HTTP_409_CONFLICT,
                    message="A record for this filename already exists.",
                    source="file",
                )
            ],
            status_code=status.HTTP_409_CONFLICT,
        )

    upload_id = uuid4().hex
    orig_name = Path(file.filename).name
    video_key = f"videos/{upload_id}/{orig_name}"

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as stream:
            minio.upload_fileobj(stream, minio.bucket_name, video_key)
    finally:
        os.remove(tmp_path)

    created_at = datetime.now(timezone.utc)
    edi = EmotionDetectionItem(
        _id=upload_id,
        video_filename=orig_name,
        video_object_path=video_key,
        created_at=created_at,
        video_uploaded_at=created_at,
    )
    emotion_detection_collection.insert_one(edi.model_dump())

    job_id = trigger_video_processing(upload_id)

    return {**edi.model_dump(), "extract_job_id": job_id}


@app.delete("/videos/{video_id}", status_code=204)
def delete_video(video_id: str):
    record = emotion_detection_collection.find_one({"_id": video_id})
    edi = EmotionDetectionItem.model_validate(record)
    if not edi:
        raise HTTPException(404, "Video not found.")
    emotion_chunks = edi.emotion_chunks
    if not emotion_chunks:
        logger.warning(f"[{video_id}] No emotion chunks to delete.")
    else:
        keys = [
            chunk.audio_chunk_file_path
            for chunk in emotion_chunks
            if chunk.audio_chunk_file_path
        ]
        keys.append(edi.audio_object_path)
        if not keys:
            logger.warning(f"[{video_id}] No valid audio chunk filenames to delete.")
    for key in filter(None, keys):
        minio.s3.delete_object(Bucket=minio.bucket_name, Key=key)

    emotion_detection_collection.delete_one({"_id": video_id})
    return {"message": "Video deleted successfully."}


@app.websocket("/ws/status/{video_id}")
async def ws_video_status(websocket: WebSocket, video_id: str):
    """
    Subscribe to Redis pub/sub channel for this video_id and
    forward every JSON‐encoded step to the client.
    """
    await websocket.accept()
    pubsub = redis.pubsub()
    pubsub.subscribe(f"video:{video_id}")
    logger.info(f"WS open, subscribed to video:{video_id}")

    try:
        while True:
            msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg["type"] == "message":
                raw = msg["data"]
                try:
                    payload = json.loads(
                        raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
                    )
                except Exception:
                    payload = {"step": "unknown", "data": raw}
                await websocket.send_json(payload)

            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info(f"WS disconnected for video:{video_id}")
    finally:
        pubsub.close()
        await websocket.close()
        logger.info(f"WS closed for video:{video_id}")
