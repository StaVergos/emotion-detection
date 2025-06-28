from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    GenerationConfig,
)
import torch
import time
from src.constants import EMOTION_LLM_MODEL
from src.config import get_logger

logger = get_logger()

use_cuda = torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")

init_start = time.time()

tokenizer = AutoTokenizer.from_pretrained(EMOTION_LLM_MODEL, use_fast=True)
tokenizer.pad_token = tokenizer.eos_token

if use_cuda:
    model = AutoModelForCausalLM.from_pretrained(
        EMOTION_LLM_MODEL,
        load_in_8bit=True,
        device_map="auto",
        torch_dtype=torch.float16,
    )
else:
    model = AutoModelForCausalLM.from_pretrained(
        EMOTION_LLM_MODEL,
        torch_dtype=torch.float32,
    ).to(device)

model.eval()

logger.info(
    f"Model loaded in {time.time() - init_start:.2f}s on {device} (cuda={use_cuda})"
)

gen_config = GenerationConfig(
    do_sample=True,
    temperature=0.7,
    top_p=0.8,
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.eos_token_id,
)


def emotional_detection(transcript: dict) -> str:
    t0 = time.time()
    text = transcript.get("text", transcript)
    logger.info(f"Detecting emotion for: {text!r}")

    prompt = (
        "Given the following transcript, identify the speaker's emotion:\n"
        f"{text}\nEmotion:"
    )

    tokens = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    input_ids = tokens.input_ids.to(device)
    attention_mask = tokens.attention_mask.to(device)

    with torch.no_grad():
        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            generation_config=gen_config,
            max_new_tokens=20,
        )

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
    emotion = decoded[len(prompt) :].strip()

    elapsed = time.time() - t0
    logger.info(f"Emotion detection done in {elapsed:.2f}s")
    print(f"Emotion detection done in {elapsed:.2f}s")

    return emotion
