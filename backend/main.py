import os
from fastapi import FastAPI, UploadFile
from src.preprocessing import extract_audio_from_video
from src.transcript import get_transcript
from src.short import emotional_detection_for_each_timestamp
from src.config import get_logger

logger = get_logger()

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

# endpoint that uploads a video file, extracts audio, transcribes it, and detects emotions
@app.post("/process_video/")
def process_video(file: UploadFile):
    """
    Process the uploaded video file to extract audio, transcribe it, and detect emotions.
    """
    # Save the uploaded file temporarily
    if not file.filename.endswith(('.mp4')):
        logger.error("Unsupported file format")
        return {"error": "Unsupported file format. Please upload a video file."}
    video_path = f"temp_{file.filename}"
    with open(video_path, "wb") as f:
        f.write(file.file.read())
    logger.info(f"Video file saved temporarily at {video_path}")

    # Extract audio from the video
    audio_path_name = os.path.splitext(video_path)[0] + ".wav"
    audio_path = extract_audio_from_video(video_path, audio_path_name)
    if not audio_path:
        logger.error("Failed to extract audio from video")
        return {"error": "Failed to extract audio from video."}
    logger.info(f"Audio extracted and saved at {audio_path}")

    transcript = get_transcript(audio_path)

    emotions = emotional_detection_for_each_timestamp(transcript)
    os.remove(video_path)
    logger.info(f"Temporary video file {video_path} removed.")
    os.remove(audio_path)
    logger.info(f"Temporary audio file {audio_path} removed.")
    logger.info("Processing completed successfully.")
    return {"transcript": transcript, "emotions": emotions}
    
