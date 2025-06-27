import torch
import time
from transformers import pipeline
from src.constants import TRANSCRIPT_MODEL
from src.config import get_logger

logger = get_logger()


def get_transcript(audio_file_path: str) -> str:
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    logger.info(f"Running on device: {device}")
    print(f"Running on device: {device}")
    start_time = time.time()
    asr = pipeline(
        "automatic-speech-recognition",
        model=TRANSCRIPT_MODEL,
        chunk_length_s=20,
        stride_length_s=5,
        device=device,
        return_timestamps=True,
    )
    asr.feature_extractor.return_attention_mask = True
    result = asr(audio_file_path)

    end_time = time.time()
    logger.info(f"Transcription completed in {end_time - start_time:.2f} seconds")
    print(f"Transcription completed in {end_time - start_time:.2f} seconds")
    if "text" not in result:
        logger.warning("No text found in transcription result")
        raise ValueError("No text found in transcription result")
    return result
