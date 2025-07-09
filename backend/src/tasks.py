import os
import tempfile
import time
from rq import get_current_job, Queue
from redis import Redis

from src.api.config import get_logger
from src.minio import MinioClient
from src.mongodb import emotion_detection_collection
from src.file_processing import break_audio_into_chunks, extract_audio_from_video
from src.analysis.transcript import get_transcript
from src.analysis.short import emotional_detection_for_each_timestamp
from src.api.schemas import (
    TranscriptProcessStatus,
    EmotionDetectionItem,
    TranscriptionResult,
)

logger = get_logger()

minio = MinioClient()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)
queue = Queue("emotion_detection", connection=redis_conn, default_timeout=360)


def extract_audio_task(video_id: str) -> None:
    start_time = time.time()
    job = get_current_job()
    logger.info(f"[{video_id}] Starting extract_audio_task")
    job.meta["step"] = "extracting_audio"
    job.save_meta()

    record = emotion_detection_collection.find_one({"_id": video_id})
    if not record:
        msg = f"No record found for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    item = EmotionDetectionItem.model_validate(record)
    data = minio.get_fileobj_in_memory(minio.bucket_name, item.video_object_path).read()

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

        emotion_detection_collection.update_one(
            {"_id": video_id},
            {
                "$set": {
                    "audio_object_path": audio_key,
                    "transcript_process_status": TranscriptProcessStatus.UPLOADED.value,
                }
            },
        )
        logger.info(f"[{video_id}]: Audio extracted and uploaded to {audio_key}")
        logger.info(
            f"[{video_id}]: Audio extraction completed in {time.time() - start_time:.2f} seconds"
        )
        job.meta.update(audio_key=audio_key, step="audio_uploaded")
        job.save_meta()
    finally:
        for path in (video_path, wav_path):
            try:
                os.remove(path)
            except OSError:
                pass
        logger.info(
            f"[{video_id}] Temporary files cleaned up: {video_path}, {wav_path}"
        )


def analyze_audio_task(video_id: str) -> None:
    start_time = time.time()
    job = get_current_job()
    logger.info(f"[{video_id}] Starting analyze_audio_task")
    job.meta["step"] = "analyzing_audio"
    job.save_meta()

    record = emotion_detection_collection.find_one({"_id": video_id})
    if not record:
        msg = f"No record for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    emotion_detection_item = EmotionDetectionItem.model_validate(record)
    if not emotion_detection_item.audio_object_path:
        msg = f"Missing audio for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    data = minio.get_fileobj_in_memory(
        minio.bucket_name, emotion_detection_item.audio_object_path
    ).read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as af:
        af.write(data)
        wav_path = af.name
    extracted_audio_timestamp = time.time()
    logger.info(
        f"[{video_id}]: Audio extracted to {wav_path} in {extracted_audio_timestamp - start_time:.2f} seconds"
    )
    try:
        transcription_result: TranscriptionResult = get_transcript(wav_path)
        transcription_timestamp = time.time()
        logger.info(
            f"[{video_id}]: Transcription complete in {transcription_timestamp - extracted_audio_timestamp:.2f} seconds"
        )

        logger.info(f"[{video_id}]: Starting emotion detection")
        emotion_chunks = emotional_detection_for_each_timestamp(transcription_result)
        emotion_detection_timestamp = time.time()
        logger.info(
            f"[{video_id}]: Detected {len(emotion_chunks)} emotion chunks in {emotion_detection_timestamp - transcription_timestamp:.2f} seconds"
        )
        emotion_detection_item.transcription_result = transcription_result.text
        emotion_detection_item.emotion_chunks = emotion_chunks
        document_to_update = emotion_detection_item.as_document()
        emotion_detection_collection.update_one(
            {"_id": video_id},
            {
                "$set": document_to_update,
            },
        )
        logger.info(
            f"[{video_id}] Emotion detection completed and updated in database in {time.time() - start_time:.2f} seconds"
        )
        job.meta.update(segments=len(emotion_chunks), step="emotions_detected")
        job.save_meta()
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass
    logger.info(f"[{video_id}] Temporary file {wav_path} cleaned up")


def chunk_audio_task(video_id: str) -> None:
    start_time = time.time()
    logger.info(f"[{video_id}]: Starting chunk_audio_task")
    job = get_current_job()
    job.meta["step"] = "chunking_audio"
    job.save_meta()

    record = emotion_detection_collection.find_one({"_id": video_id})
    if not record:
        msg = f"No record for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    emotion_detection_item = EmotionDetectionItem.model_validate(record)
    if (
        not emotion_detection_item.audio_object_path
        or not emotion_detection_item.emotion_chunks
    ):
        msg = f"Incomplete data for video {video_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    data = minio.get_fileobj_in_memory(
        minio.bucket_name, emotion_detection_item.audio_object_path
    ).read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as af:
        af.write(data)
        wav_path = af.name
    extracted_audio_timestamp = time.time()
    logger.info(
        f"[{video_id}]: Audio extracted to {wav_path} in {extracted_audio_timestamp - start_time:.2f} seconds"
    )
    try:
        timestamps = [
            tuple(seg.timestamp) for seg in emotion_detection_item.emotion_chunks
        ]
        logger.info(f"[{video_id}]: Starting to break audio into chunks")
        started_chunking = time.time()
        chunks = break_audio_into_chunks(wav_path, timestamps)
        chunking_timestamp = time.time()
        logger.info(
            f"[{video_id}]: Audio chunking completed in {chunking_timestamp - started_chunking:.2f} seconds"
        )

        chunk_keys = []
        for index, c in enumerate(chunks):
            key = f"audio_chunks/{video_id}/chunk_{index}.wav"
            with open(c.filename, "rb") as cf:
                minio.upload_fileobj(cf, minio.bucket_name, key)
            logger.info(f"[{video_id}]: Uploaded chunk {index} to {key}")
            chunk_keys.append(key)
            os.remove(c.filename)

        updated = []
        for index, seg in enumerate(emotion_detection_item.emotion_chunks):
            data = seg.model_dump()
            data["audio_chunk_file_path"] = chunk_keys[index]
            updated.append(data)

        emotion_detection_collection.update_one(
            {"_id": video_id},
            {"$set": {"emotion_chunks": updated}},
        )
        job.meta.update(chunks=len(updated), step="audio_chunked")
        job.save_meta()
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass
    logger.info(f"[{video_id}]: Temporary file {wav_path} cleaned up")


def pipeline_task(video_id: str) -> None:
    """
    Enqueue the three sub-tasks in order, and store their IDs
    in this orchestrator job’s meta for easy tracking.
    """
    job = get_current_job()
    logger.info(f"[{video_id}] ▶️ Starting pipeline_task (orchestrator)")
    j1 = queue.enqueue(extract_audio_task, video_id)
    j2 = queue.enqueue(analyze_audio_task, video_id, depends_on=j1)
    j3 = queue.enqueue(chunk_audio_task, video_id, depends_on=j2)

    job.meta["child_job_ids"] = [j1.id, j2.id, j3.id]
    job.meta["step"] = "subtasks_enqueued"
    job.save_meta()
    logger.info(
        f"[{video_id}] ✅ pipeline_task enqueued subtasks: {j1.id} → {j2.id} → {j3.id}"
    )


def trigger_video_processing(video_id: str) -> str:
    """
    Starts the full pipeline and returns *one* job ID (the orchestrator).
    """
    orchestrator = queue.enqueue(pipeline_task, video_id)
    logger.info(f"[{video_id}] 🎬 Pipeline orchestrator enqueued: {orchestrator.id}")
    return orchestrator.id
