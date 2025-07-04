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
    EmotionDetection,
    Error,
    VideoListItem,
    TranscriptProcessStatus,
    VideosResponse,
    VideoError,
)
from src.api.exceptions import APIError
from src.preprocessing import extract_audio_from_video
from src.transcript import get_transcript
from src.short import emotional_detection_for_each_timestamp

from src.tasks import long_task

logger = get_logger()
minio = MinioClient()
redis = Redis(host="localhost", port=6379)
queue = Queue("emotion_detection", connection=redis)

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
    response_model=VideoListItem,
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
        "transcript_process_status": TranscriptProcessStatus.UPLOADED.value,
    }
    emotion_detection_collection.insert_one(doc)

    return doc


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


@app.post("/videos/{video_id}/process", response_model=EmotionDetection)
def process_video(video_id: str):
    record = emotion_detection_collection.find_one({"_id": video_id})
    if not record:
        raise HTTPException(404, "Video not found.")

    video_key = record["video_object"]
    audio_key = f"audio/{video_id}.wav"

    in_mem = minio.get_fileobj_in_memory(minio.bucket_name, video_key)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_vid:
        tmp_vid.write(in_mem.read())
        tmp_vid_path = tmp_vid.name

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name
        extract_audio_from_video(tmp_vid_path, tmp_wav_path)

        with open(tmp_wav_path, "rb") as stream:
            minio.upload_fileobj(stream, minio.bucket_name, audio_key)

        transcript = get_transcript(tmp_wav_path)
        emotions = emotional_detection_for_each_timestamp(transcript)

    finally:
        os.remove(tmp_vid_path)
        os.remove(tmp_wav_path)

    transcript_text = transcript.get("text", "")
    updated = {
        "audio_object": audio_key,
        "transcript": transcript_text,
        "emotions": emotions,
    }
    emotion_detection_collection.update_one({"_id": video_id}, {"$set": updated})

    record.update(updated)
    return record


@app.post("/videos/{id}/analyze")
def analyze(id: str):
    record = emotion_detection_collection.find_one({"_id": id})
    if not record:
        raise HTTPException(404, "Video not found.")
    transcript = record.get("transcript")
    if not transcript:
        raise HTTPException(400, "Transcript not found for this video.")
    # job = queue.enqueue(emotional_detection, transcript, job_id=id)
    return {"job_id": "job.id"}


@app.post("/enqueue/{steps}")
def enqueue_test(steps: int):
    """
    Enqueue a dummy long-running task (steps seconds) for testing.
    """
    job = queue.enqueue(long_task, steps)
    return {"job_id": job.id}


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
