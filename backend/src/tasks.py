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


def process_video_task(video_id: str) -> None:
    job = get_current_job()

    emotion_detection_collection.update_one(
        {"_id": video_id},
        {
            "$set": {
                "transcript_process_status": TranscriptProcessStatus.PROCESSING.value
            }
        },
    )
    job.meta["step"] = "started"
    job.save_meta()

    record = emotion_detection_collection.find_one({"_id": video_id})
    video_key = record.get("video_object")
    if not video_key:
        job.meta["step"] = "error: missing video_object"
        job.save_meta()
        raise RuntimeError(f"Missing video_object for {video_id}")

    in_mem = minio.get_fileobj_in_memory(minio.bucket_name, video_key)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_vid:
        tmp_vid.write(in_mem.read())
        tmp_vid_path = tmp_vid.name

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name
        extract_audio_from_video(tmp_vid_path, tmp_wav_path)
        job.meta["step"] = "audio extracted"
        job.save_meta()

        audio_key = f"audio/{video_id}.wav"
        with open(tmp_wav_path, "rb") as stream:
            minio.upload_fileobj(stream, minio.bucket_name, audio_key)
        job.meta["step"] = "audio uploaded"
        job.save_meta()

        transcript_res = get_transcript(tmp_wav_path)
        job.meta["step"] = "transcribed"
        job.save_meta()

        emotions = emotional_detection_for_each_timestamp(transcript_res)
        job.meta["step"] = "emotions detected"
        job.save_meta()

        emotion_detection_collection.update_one(
            {"_id": video_id},
            {
                "$set": {
                    "audio_object": audio_key,
                    "transcript": transcript_res.get("text", ""),
                    "emotions": emotions,
                    "transcript_process_status": TranscriptProcessStatus.COMPLETED.value,
                }
            },
        )
        job.meta["step"] = "done"
        job.save_meta()

    finally:
        try:
            os.remove(tmp_vid_path)
            os.remove(tmp_wav_path)
        except OSError:
            pass
