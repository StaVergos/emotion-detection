import os
import shutil
import tempfile
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_logger, DEFAULT_BUCKET_NAME
from src.minio import MinioClient
from src.preprocessing import extract_audio_from_video
from src.transcript import get_transcript
from src.short import emotional_detection_for_each_timestamp

logger = get_logger()
minio = MinioClient(bucket_name=DEFAULT_BUCKET_NAME)

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


@app.post("/process_video/")
def process_video(file: UploadFile):
    # 1) validate
    if not file.filename.lower().endswith(".mp4"):
        logger.error("Unsupported format: %s", file.filename)
        raise HTTPException(400, "Upload an MP4 video.")

    upload_id = uuid4().hex
    orig_name = Path(file.filename).name
    bucket = minio.bucket_name
    video_key = f"videos/{upload_id}/{orig_name}"
    audio_key = f"audio/{upload_id}.wav"

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_vid:
        shutil.copyfileobj(file.file, tmp_vid)
        tmp_vid_path = tmp_vid.name

    try:
        with open(tmp_vid_path, "rb") as stream:
            minio.upload_fileobj(stream, bucket, video_key)
        logger.info("Video uploaded to %s/%s", bucket, video_key)

        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav_path = tmp_wav.name
        tmp_wav.close()

        extract_audio_from_video(tmp_vid_path, tmp_wav_path)

        with open(tmp_wav_path, "rb") as stream:
            minio.upload_fileobj(stream, bucket, audio_key)
        logger.info("Audio uploaded to %s/%s", bucket, audio_key)

        transcript = get_transcript(tmp_wav_path)
        emotions = emotional_detection_for_each_timestamp(transcript)

    except Exception:
        logger.exception("Processing failed")
        raise HTTPException(500, "Processing error")

    finally:
        # clean up local temp files
        for p in (tmp_vid_path, tmp_wav_path):
            try:
                os.remove(p)
            except OSError:
                pass

    return {
        "video_object": video_key,
        "audio_object": audio_key,
        "transcript": transcript,
        "emotions": emotions,
    }
