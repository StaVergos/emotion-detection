import torch
import time
from transformers import pipeline
from src.api.schemas import TranscriptionResult
from src.api.constants import TRANSCRIPT_MODEL
from src.api.config import get_logger

logger = get_logger()

init_start = time.time()
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
elapsed_time = time.time() - init_start
logger.info(f"ASR model loaded in {elapsed_time:.2f} seconds")


def get_transcript(audio_file_path: str) -> list[TranscriptionResult]:
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
    transcription_result = TranscriptionResult.model_validate(result)
    logger.info(f"Transcription result: {result}")
    return transcription_result
