import datetime
import os
import tempfile
import time
import json
from rq import get_current_job, Queue
from redis import Redis

from src.api.config import get_logger
from src.minio import MinioClient
from src.mongodb import emotion_detection_collection
from src.file_processing import break_audio_into_chunks, extract_audio_from_video
from src.analysis.transcript import get_transcript
from src.analysis.short import emotional_detection_for_each_timestamp
from src.api.schemas import (
    EmotionDetectionItem,
    TranscriptionResult,
)
from src.analysis.audio_emotion import get_emotion_scores_from_file

logger = get_logger()
minio = MinioClient()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)
queue = Queue("emotion_detection", connection=redis_conn, default_timeout=360)


def _publish_step(video_id: str, step: str, **meta):
    """
    Helper to publish a JSON step update to Redis pub/sub.
    """
    payload = {"step": step, **meta}
    redis_conn.publish(f"video:{video_id}", json.dumps(payload))


def extract_audio_task(video_id: str) -> None:
    start = time.time()
    job = get_current_job()
    logger.info(f"[{video_id}]: extract_audio_task start")
    job.meta["step"] = "extracting_audio"
    job.save_meta()
    _publish_step(video_id, "extracting_audio")

    rec = emotion_detection_collection.find_one({"_id": video_id})
    if not rec:
        msg = f"No record found for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    edi = EmotionDetectionItem.model_validate(rec)
    data = minio.get_fileobj_in_memory(minio.bucket_name, edi.video_object_path).read()

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as vf:
        vf.write(data)
        video_path = vf.name

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as af:
            wav_path = af.name
        extract_audio_from_video(video_path, wav_path)

        audio_key = f"audio/{video_id}.wav"
        with open(wav_path, "rb") as wf:
            minio.upload_fileobj(wf, minio.bucket_name, audio_key)

        edi.audio_object_path = audio_key
        edi.audio_extracted_at = datetime.datetime.now(datetime.timezone.utc)

        emotion_detection_collection.update_one(
            {"_id": video_id}, {"$set": edi.as_document()}
        )

        elapsed = time.time() - start
        logger.info(f"[{video_id}]: audio extracted in {elapsed:.2f}s → {audio_key}")

        job.meta.update(audio_key=audio_key, step="audio_extracted")
        job.save_meta()
        _publish_step(video_id, "audio_extracted", audio_key=audio_key)

    finally:
        for p in (video_path, wav_path):
            try:
                os.remove(p)
            except OSError:
                pass
        logger.info(f"[{video_id}]: cleaned temp files")


def analyze_audio_task(video_id: str) -> None:
    start = time.time()
    job = get_current_job()
    logger.info(f"[{video_id}]: analyze_audio_task start")
    job.meta["step"] = "analyzing_audio"
    job.save_meta()
    _publish_step(video_id, "analyzing_audio")

    rec = emotion_detection_collection.find_one({"_id": video_id})
    if not rec:
        msg = f"No record for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    edi = EmotionDetectionItem.model_validate(rec)
    if not edi.audio_object_path:
        msg = f"Missing audio for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    data = minio.get_fileobj_in_memory(minio.bucket_name, edi.audio_object_path).read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as af:
        af.write(data)
        wav_path = af.name

    try:
        tr: TranscriptionResult = get_transcript(wav_path)
        logger.info(f"[{video_id}]: transcribed in {time.time() - start:.2f}s")
        edi.transcription_completed_at = datetime.datetime.now(datetime.timezone.utc)
        edi.transcription_result = tr.text
        emotion_detection_collection.update_one(
            {"_id": video_id},
            {
                "$set": edi.as_document(),
            },
        )
        _publish_step(video_id, "transcription_completed")

        chunks = emotional_detection_for_each_timestamp(tr)
        edi.transcription_result = tr.text
        edi.emotion_chunks = chunks
        edi.transcription_chunks_emotion_completed_at = datetime.datetime.now(
            datetime.timezone.utc
        )
        emotion_detection_collection.update_one(
            {"_id": video_id}, {"$set": edi.as_document()}
        )

        logger.info(f"[{video_id}]: emotions detected ({len(chunks)})")
        job.meta.update(segments=len(chunks), step="emotions_detected")
        job.save_meta()
        _publish_step(video_id, "emotions_detected", segments=len(chunks))

    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass
        logger.info(f"[{video_id}]: cleaned temp file")


def chunk_audio_task(video_id: str) -> None:
    job = get_current_job()
    logger.info(f"[{video_id}]: chunk_audio_task start")
    job.meta["step"] = "chunking_audio"
    job.save_meta()
    _publish_step(video_id, "chunking_audio")

    rec = emotion_detection_collection.find_one({"_id": video_id})
    if not rec:
        msg = f"No record for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    edi = EmotionDetectionItem.model_validate(rec)
    if not edi.audio_object_path or not edi.emotion_chunks:
        msg = f"Incomplete data for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    data = minio.get_fileobj_in_memory(minio.bucket_name, edi.audio_object_path).read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as af:
        af.write(data)
        wav_path = af.name

    try:
        timestamps = [tuple(seg.timestamp) for seg in edi.emotion_chunks]
        chunks = break_audio_into_chunks(wav_path, timestamps)

        keys = []
        for i, c in enumerate(chunks):
            key = f"audio_chunks/{video_id}/chunk_{i}.wav"
            with open(c.filename, "rb") as cf:
                minio.upload_fileobj(cf, minio.bucket_name, key)
            keys.append(key)
            os.remove(c.filename)

        updated = []
        for i, seg in enumerate(edi.emotion_chunks):
            d = seg.model_dump()
            d["audio_chunk_file_path"] = keys[i]
            updated.append(d)

        edi.audio_chunks_uploaded_at = datetime.datetime.now(datetime.timezone.utc)
        edi.emotion_chunks = updated
        emotion_detection_collection.update_one(
            {"_id": video_id}, {"$set": edi.as_document()}
        )

        logger.info(f"[{video_id}]: audio chunked ({len(updated)} chunks)")
        job.meta.update(chunks=len(updated), step="audio_chunked")
        job.save_meta()
        _publish_step(video_id, "audio_chunked", chunks=len(updated))

    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass
        logger.info(f"[{video_id}]: cleaned temp file")


def calculate_audio_emotion_scores_task(video_id: str) -> None:
    job = get_current_job()
    logger.info(f"[{video_id}]: calculate_emotion_scores_task start")
    job.meta["step"] = "calculating_emotion_scores"
    job.save_meta()
    _publish_step(video_id, "calculating_emotion_scores")
    rec = emotion_detection_collection.find_one({"_id": video_id})
    if not rec:
        msg = f"No record for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)
    edi = EmotionDetectionItem.model_validate(rec)
    if not edi.emotion_chunks:
        msg = f"No audio chunks for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)
    audio_calculations = []
    for chunk in edi.emotion_chunks:
        if not chunk.audio_chunk_file_path:
            logger.warning(
                f"[{video_id}]: No audio chunk file path for segment {chunk.id}"
            )
            continue
        data = minio.get_fileobj_in_memory(
            minio.bucket_name, chunk.audio_chunk_file_path
        ).read()
        scores = get_emotion_scores_from_file(data)
        audio_calculations.append(
            {
                "chunk_timestamp": chunk.timestamp,
                "scores": scores,
            }
        )
    logger.warning(f"[{video_id}]: audio chunk emotion scores calculated")
    logger.warning(audio_calculations)


def trigger_video_processing(video_id: str) -> str:
    """
    Enqueue each step in sequence—no parent/orchestrator job.
    Returns the first (extract_audio_task) job's ID, but
    WebSocket clients subscribe by video_id, not by job_id.
    """
    j1 = queue.enqueue(extract_audio_task, video_id, timeout=3600)
    queue.enqueue(analyze_audio_task, video_id, depends_on=j1, timeout=3600)
    queue.enqueue(chunk_audio_task, video_id, depends_on=j1, timeout=3600)
    queue.enqueue(
        calculate_audio_emotion_scores_task, video_id, depends_on=j1, timeout=3600
    )
    logger.info(f"[{video_id}] triggered pipeline")
    return j1.id
