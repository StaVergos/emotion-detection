import tempfile
import time
from typing import List, Tuple

from moviepy import VideoFileClip
from pydub import AudioSegment

from src.api.config import get_logger
from src.api.schemas import AudioChunk

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
    return output_audio_path


def break_audio_into_chunks(
    audio_file_path: str,
    timestamps: List[Tuple[float, float]],
) -> List[AudioChunk]:
    """
    Splits a WAV at 16 kHz, 16-bit into sub-clips given by (start_s, end_s) in seconds.
    Returns a list of AudioChunk models.
    """
    start_time = time.time()
    audio = (
        AudioSegment.from_file(audio_file_path)
        .set_frame_rate(16000)
        .set_sample_width(2)
        .set_channels(1)
    )

    chunks: List[AudioChunk] = []
    for i, (t0, t1) in enumerate(timestamps):
        start_ms = int(t0 * 1000)
        end_ms = int(t1 * 1000)
        segment = audio[start_ms:end_ms]

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        segment.export(
            tmp.name,
            format="wav",
            parameters=["-ar", "16000", "-ac", "1", "-sample_fmt", "s16"],
        )

        chunks.append(
            AudioChunk(
                filename=tmp.name,
                start=t0,
                end=t1,
            )
        )

    elapsed = time.time() - start_time
    logger.info(f"Audio chunking completed in {elapsed:.2f} seconds")
    logger.info(f"Audio file {audio_file_path} split into {len(chunks)} chunks")
    return chunks
