import asyncio
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
from rq import Queue
from redis import Redis
from rq.job import Job
from rq.exceptions import NoSuchJobError

from src.api.config import get_logger
from src.minio import MinioClient
from src.mongodb import emotion_detection_collection, check_record_exists
from src.api.schemas import (
    Error,
    EmotionDetectionItem,
    VideosResponse,
    VideoError,
    ProcessingStatus,
    UploadedVideoResponse,
)
from src.tasks import trigger_video_processing  # <-- new unified task
from src.api.exceptions import APIError

logger = get_logger()
minio = MinioClient()
redis = Redis(host="localhost", port=6379)
queue = Queue("emotion_detection", connection=redis, default_timeout=3600)

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
    emotion_detection_item = EmotionDetectionItem(
        _id=upload_id,
        video_filename=orig_name,
        video_object_path=video_key,
        created_at=created_at,
        processing_status=ProcessingStatus.VIDEO_UPLOADED.value,
    )
    emotion_detection_collection.insert_one(emotion_detection_item.model_dump())

    job_id = trigger_video_processing(upload_id)

    return {**emotion_detection_item.model_dump(), "extract_job_id": job_id}


@app.delete("/videos/{video_id}", status_code=204)
def delete_video(video_id: str):
    record = emotion_detection_collection.find_one({"_id": video_id})
    emotion_detection_item = EmotionDetectionItem.model_validate(record)
    if not emotion_detection_item:
        raise HTTPException(404, "Video not found.")

    keys = (
        [emotion_detection_item.video_object_path]
        + (
            [emotion_detection_item.audio_object_path]
            if emotion_detection_item.audio_object_path
            else []
        )
        + [
            chunk["audio_chunk"]
            for chunk in emotion_detection_item.emotion_chunks
            if "audio_chunk" in chunk
        ]
    )
    for key in filter(None, keys):
        minio.s3.delete_object(Bucket=minio.bucket_name, Key=key)

    emotion_detection_collection.delete_one({"_id": video_id})
    return {"message": "Video deleted successfully."}


@app.websocket("/ws/status/{job_id}")
async def ws_job_status(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        try:
            Job.fetch(job_id, connection=redis)
        except NoSuchJobError:
            await websocket.send_json({"error": "Job not found"})
            await websocket.close()
            return

        while True:
            job = Job.fetch(job_id, connection=redis)
            status_ = job.get_status()
            meta = job.meta or {}

            await websocket.send_json(
                {"job_id": job_id, "status": status_, "meta": meta}
            )

            if status_ in ("finished", "failed"):
                break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
