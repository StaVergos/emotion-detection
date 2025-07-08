import time
from rq import get_current_job
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
import torch

from src.api.constants import EMOTION_LLM_MODEL
from src.api.config import get_logger

logger = get_logger()

use_cuda = torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")

tokenizer = AutoTokenizer.from_pretrained(EMOTION_LLM_MODEL, use_fast=True)
tokenizer.pad_token = tokenizer.eos_token

model = (
    AutoModelForCausalLM.from_pretrained(
        EMOTION_LLM_MODEL,
        load_in_8bit=use_cuda,
        device_map="auto" if use_cuda else None,
        torch_dtype=torch.float16 if use_cuda else torch.float32,
    )
    .to(device)
    .eval()
)

gen_config = GenerationConfig(
    do_sample=True,
    temperature=0.7,
    top_p=0.8,
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.eos_token_id,
)


def emotional_detection(transcript: dict) -> str:
    job = get_current_job()
    t0 = time.time()
    text = transcript.get("text", transcript)
    logger.info(f"LLM emotion-detect for: {text!r}")

    prompt = f"Given the following transcript, identify the speaker's emotion:\n{text}\nEmotion:"

    job.meta["step"] = "tokenizing"
    job.save_meta()
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    job.meta["step"] = "generating"
    job.save_meta()
    with torch.no_grad():
        out = model.generate(**inputs, generation_config=gen_config, max_new_tokens=20)

    job.meta["step"] = "decoding"
    job.save_meta()
    decoded = tokenizer.decode(out[0], skip_special_tokens=True)
    emotion = decoded[len(prompt) :].strip()

    job.meta["step"] = "done"
    job.meta["emotion"] = emotion
    job.meta["elapsed_s"] = time.time() - t0
    job.save_meta()

    logger.info(f"Detected emotion: {emotion}")
    return emotion
