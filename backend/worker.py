# backend/worker.py
import os
import time
import torch
from redis import Redis
from rq import Queue, Worker
from transformers import pipeline

from src.api.config import get_logger
from src.api.constants import TRANSCRIPT_MODEL

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
elapsed = time.time() - init_start
logger.info(f"ASR model loaded in {elapsed:.2f}s")

if __name__ == "__main__":
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    conn = Redis.from_url(redis_url)

    q = Queue("emotion_detection", connection=conn, default_timeout=3600)
    worker = Worker([q], connection=conn)
    worker.work()
