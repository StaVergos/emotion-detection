import torch
import time
from transformers import pipeline
from src.constants import TRANSCRIPT_MODEL
from src.config import get_logger

logger = get_logger()

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
logger.info(f"Loading ASR model on device: {device}")
asr = pipeline(
    "automatic-speech-recognition",
    model=TRANSCRIPT_MODEL,
    chunk_length_s=20,
    stride_length_s=5,
    device=device,
    return_timestamps=True,
)
asr.feature_extractor.return_attention_mask = True

def get_transcript(audio_file_path: str) -> dict:
    """
    Run ASR on the given audio file and return the transcript text.

    Raises:
        ValueError: if the pipeline returns no "text" field.
    """
    logger.info(f"Running on device: {device}")
    start_time = time.time()
    result = asr(
        audio_file_path,
        generate_kwargs={
            "task": "transcribe",
            "language": "<|en|>",
        },
    )

    end_time = time.time()
    logger.info(f"Transcription completed in {end_time - start_time:.2f} seconds")
    print(f"Transcription completed in {end_time - start_time:.2f} seconds")
    if "text" not in result:
        logger.error("No text found in transcription result")
        raise ValueError("No text found in transcription result")
    return result
