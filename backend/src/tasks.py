import os
import tempfile
from src.api.config import get_logger

from rq import get_current_job

from src.minio import MinioClient
from src.mongodb import emotion_detection_collection
from src.file_processing import break_audio_into_chunks, extract_audio_from_video
from src.analysis.transcript import get_transcript
from src.analysis.short import emotional_detection_for_each_timestamp
from src.api.schemas import (
    TranscriptProcessStatus,
    TranscriptionChunk,
    TranscriptionResult,
    EmotionDetectionItem,
)

logger = get_logger()

minio = MinioClient()


def process_video_task(video_id: str) -> None:
    job = get_current_job()
    job.meta["step"] = "fetching_video"
    job.save_meta()
    record_data = emotion_detection_collection.find_one({"_id": video_id})
    if not record_data:
        raise RuntimeError(f"No record found for video ID: {video_id}")
    emotion_detection_item = EmotionDetectionItem.model_validate(record_data)
    if not emotion_detection_item:
        raise RuntimeError(f"No record for {video_id}")

    video_object_path = emotion_detection_item.video_object_path
    data = minio.get_fileobj_in_memory(minio.bucket_name, video_object_path).read()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as vf:
        vf.write(data)
        vid_path = vf.name

    try:
        job.meta["step"] = "extracting_audio"
        job.save_meta()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as af:
            wav_path = af.name
        extract_audio_from_video(vid_path, wav_path)

        audio_key = f"audio/{video_id}.wav"
        with open(wav_path, "rb") as stream:
            minio.upload_fileobj(stream, minio.bucket_name, audio_key)

        emotion_detection_item.audio_object_path = audio_key
        emotion_detection_item.transcript_process_status = (
            TranscriptProcessStatus.UPLOADED.value
        )
        document_to_update = emotion_detection_item.as_document()

        emotion_detection_collection.update_one(
            {"_id": video_id},
            {"$set": document_to_update},
        )

        job.meta.update(audio_key=audio_key, step="audio_uploaded")
        job.save_meta()

        job.meta["step"] = "transcribing"
        job.save_meta()
        transcription_result: TranscriptionResult = get_transcript(wav_path)
        logger.info(f"Transcription result: {transcription_result}")
        job.meta["step"] = "transcribed"
        job.save_meta()

        emotion_chunks = emotional_detection_for_each_timestamp(transcription_result)
        emotion_detection_item.transcription_result = transcription_result.text
        emotion_detection_item.emotion_chunks = emotion_chunks
        document_to_update = emotion_detection_item.as_document()
        emotion_detection_collection.update_one(
            {"_id": video_id},
            {
                "$set": document_to_update,
            },
        )
        job.meta["step"] = "emotions_detected"
        job.save_meta()

        job.meta["step"] = "chunking_audio"
        job.save_meta()
        timestamps = [tuple(e.timestamp) for e in emotion_chunks if e.timestamp]
        chunks = break_audio_into_chunks(wav_path, timestamps)

        chunk_keys = []
        for i, c in enumerate(chunks):
            key = f"audio_chunks/{video_id}/chunk_{i}.wav"
            with open(c.filename, "rb") as st:
                minio.upload_fileobj(st, minio.bucket_name, key)
            chunk_keys.append(key)
            os.remove(c.filename)

        updated_emotions = []
        for idx, e in enumerate(chunks):
            d = e.model_dump()
            d["audio_chunk"] = chunk_keys[idx] if idx < len(chunk_keys) else None
            updated_emotions.append(d)

        current_emotions = emotion_detection_item.emotion_chunks
        updated_emotions: list[TranscriptionChunk] = []
        for idx, e in enumerate(current_emotions):
            updated_emotions.append(
                TranscriptionChunk(
                    text=e.text,
                    timestamp=e.timestamp,
                    audio_chunk_file_path=(
                        chunk_keys[idx] if idx < len(chunk_keys) else None
                    ),
                    emotion=e.emotion,
                    emotion_score=e.emotion_score,
                )
            )
        logger.info(f"Updated emotions: {updated_emotions} for video ID: {video_id}")
        emotion_detection_item.emotion_chunks = updated_emotions
        record_to_update = emotion_detection_item.as_document()
        emotion_detection_collection.update_one(
            {"_id": video_id},
            {"$set": record_to_update},
        )

        job.meta["step"] = "done"
        job.save_meta()

    finally:
        for f in (vid_path, wav_path):
            try:
                os.remove(f)
            except OSError:
                pass
    return
