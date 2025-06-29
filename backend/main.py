import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, UploadFile, HTTPException, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_logger
from src.minio import MinioClient
from src.mongodb import emotion_detection_collection, check_record_exists
from src.schemas import (
    EmotionDetection,
    VideoListItem,
)
from src.preprocessing import extract_audio_from_video
from src.transcript import get_transcript
from src.short import emotional_detection_for_each_timestamp

logger = get_logger()
minio = MinioClient()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthcheck")
def healthcheck():
    return {"status": "online"}


@app.get("/videos", response_model=list[VideoListItem])
def list_videos():
    items = list(emotion_detection_collection.find())
    if not items:
        raise HTTPException(404, "No videos found.")
    return items


@app.get("/videos/{video_id}", response_model=VideoListItem)
def get_video(video_id: str = PathParam(..., description="MongoDB document ID")):
    item = emotion_detection_collection.find_one({"_id": video_id})
    if not item:
        raise HTTPException(404, "Video not found.")
    return item


@app.post("/videos/upload", status_code=201)
def upload_video(file: UploadFile):
    if not file.filename.lower().endswith(".mp4"):
        raise HTTPException(400, "Please upload an MP4 video.")

    if check_record_exists(file.filename):
        raise HTTPException(409, "A record for this filename already exists.")

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
    }
    emotion_detection_collection.insert_one(doc)

    return doc


@app.post("/videos/{video_id}/process", response_model=EmotionDetection)
def process_video(video_id: str = PathParam(..., description="MongoDB document ID")):
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
