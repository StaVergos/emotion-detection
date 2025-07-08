# backend/main.py
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
    UploadeVideoResponse,
    VideoListItem,
    VideosResponse,
    VideoError,
)
from src.api.exceptions import APIError
from src.tasks import extract_audio_task, transcribe_task

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


@app.get("/videos/{video_id}", response_model=VideoListItem)
def get_video(video_id: str):
    item = emotion_detection_collection.find_one({"_id": video_id})
    if not item:
        raise HTTPException(404, "Video not found.")
    return item


@app.post(
    "/videos",
    status_code=status.HTTP_201_CREATED,
    response_model=UploadeVideoResponse,
    responses={400: {"model": VideoError}, 409: {"model": VideoError}},
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
    doc = {
        "_id": upload_id,
        "video_filename": orig_name,
        "video_object": video_key,
        "created_at": created_at,
        "transcript_process_status": None,
    }
    emotion_detection_collection.insert_one(doc)

    extract_job = queue.enqueue(
        extract_audio_task,
        upload_id,
        job_id=f"{upload_id}-extract",
        ttl=3600,
    )

    return {**doc, "extract_job_id": extract_job.id}


@app.delete("/videos/{video_id}", status_code=204)
def delete_video(video_id: str):
    record = emotion_detection_collection.find_one({"_id": video_id})
    if not record:
        raise HTTPException(404, "Video not found.")

    video_key = record["video_object"]
    audio_key = record.get("audio_object")

    minio.s3.delete_object(Bucket=minio.bucket_name, Key=video_key)
    if audio_key:
        minio.s3.delete_object(Bucket=minio.bucket_name, Key=audio_key)

    emotion_detection_collection.delete_one({"_id": video_id})

    return {"message": "Video deleted successfully."}


@app.post("/videos/{video_id}/transcript")
def transcript_video(video_id: str):
    record = emotion_detection_collection.find_one({"_id": video_id})
    if not record:
        raise HTTPException(404, "Video not found.")
    record_key = record.get("audio_object", None)
    if not record_key:
        raise HTTPException(404, "Audio object not found. Please extract audio first.")

    job = queue.enqueue(transcribe_task, video_id, record_key, job_id=video_id)
    return {"job_id": job.id}


@app.post("/videos/{id}/analyze")
def analyze(id: str):
    record = emotion_detection_collection.find_one({"_id": id})
    if not record:
        raise HTTPException(404, "Video not found.")
    transcript = record.get("transcript")
    if not transcript:
        raise HTTPException(400, "Transcript not found for this video.")
    return {"job_id": "job.id"}


@app.websocket("/ws/status/{job_id}")
async def ws_job_status(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        job = Job.fetch(job_id, connection=redis)
    except NoSuchJobError:
        await websocket.send_json({"error": "Job not found"})
        await websocket.close()
        return

    try:
        while True:
            status = job.get_status()
            meta = job.meta or {}
            await websocket.send_json(
                {"job_id": job_id, "status": status, "meta": meta}
            )
            if status in ("finished", "failed"):
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
    await websocket.close()
