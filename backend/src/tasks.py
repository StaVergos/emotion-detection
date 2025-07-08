import os
import tempfile
from rq import get_current_job

from src.minio import MinioClient
from src.mongodb import emotion_detection_collection
from src.preprocessing import extract_audio_from_video
from src.transcript import get_transcript
from src.short import emotional_detection_for_each_timestamp
from src.api.schemas import TranscriptProcessStatus

minio = MinioClient()


def extract_audio_task(video_id: str) -> str:
    job = get_current_job()
    job.meta["step"] = "started_extraction"
    job.save_meta()

    record = emotion_detection_collection.find_one({"_id": video_id})
    if not record:
        job.meta["step"] = "error:missing_record"
        job.save_meta()
        raise RuntimeError(f"Record not found for video_id {video_id}")
    video_key = record.get("video_object")
    if not video_key:
        job.meta["step"] = "error:missing_video_object"
        job.save_meta()
        raise RuntimeError(f"Missing video_object for {video_id}")

    in_mem = minio.get_fileobj_in_memory(minio.bucket_name, video_key)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_vid:
        tmp_vid.write(in_mem.read())
        vid_path = tmp_vid.name

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            wav_path = tmp_wav.name
        extract_audio_from_video(vid_path, wav_path)
        job.meta["step"] = "audio_extracted"
        job.save_meta()

        audio_key = f"audio/{video_id}.wav"
        with open(wav_path, "rb") as stream:
            minio.upload_fileobj(stream, minio.bucket_name, audio_key)
        job.meta["step"] = "audio_uploaded"
        job.save_meta()

        emotion_detection_collection.update_one(
            {"_id": video_id},
            {
                "$set": {
                    "audio_object": audio_key,
                    "transcript_process_status": TranscriptProcessStatus.UPLOADED.value,
                }
            },
        )

        job.meta["audio_key"] = audio_key
        job.meta["step"] = "done_extraction"
        job.save_meta()
        return audio_key

    finally:
        for p in (vid_path, wav_path):
            try:
                os.remove(p)
            except OSError:
                pass


def transcribe_task(video_id: str, audio_key: str) -> None:
    job = get_current_job()
    job.meta["step"] = "started_transcription"
    job.meta["audio_key"] = audio_key
    job.save_meta()

    in_mem = minio.get_fileobj_in_memory(minio.bucket_name, audio_key)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        tmp_wav.write(in_mem.read())
        wav_path = tmp_wav.name

    try:
        transcript_res = get_transcript(wav_path)
        job.meta["step"] = "transcribed"
        job.save_meta()

        emotions = emotional_detection_for_each_timestamp(transcript_res)
        job.meta["step"] = "emotions_detected"
        job.save_meta()

        emotion_detection_collection.update_one(
            {"_id": video_id},
            {
                "$set": {
                    "transcript": transcript_res.get("text", ""),
                    "emotions": emotions,
                    "transcript_process_status": TranscriptProcessStatus.COMPLETED.value,
                }
            },
        )
        job.meta["step"] = "done_transcription"
        job.save_meta()

    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass
