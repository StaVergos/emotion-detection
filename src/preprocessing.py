import time
from moviepy import VideoFileClip
from src.config import get_logger

logger = get_logger()


def extract_audio_from_video(video_file_path: str, output_audio_path: str) -> str:
    """
    Extracts audio from a video file and saves it as a WAV file.
    """
    start_time = time.time()
    clip = VideoFileClip(video_file_path)
    clip.audio.write_audiofile(
        output_audio_path,
        fps=16000,  # Whisper expects 16 kHz
        nbytes=2,  # 16-bit PCM
        codec="pcm_s16le",
        logger=None,  # suppress MoviePy logs
    )
    clip.close()
    end_time = time.time()
    logger.info(f"Audio extraction completed in {end_time - start_time:.2f} seconds")
    print(f"Audio extraction completed in {end_time - start_time:.2f} seconds")
    return output_audio_path
