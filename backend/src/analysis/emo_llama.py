import time
from src.api.config import get_logger
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
)
import torch
from src.api.constants import EMOTION_LLAMA_MODEL

logger = get_logger()


def analyze_prompt_with_emo_llama(prompt: str) -> str:
    time_start = time.time()
    logger.info("Starting analysis with Emotion LLaMA model...")

    tokenizer = AutoTokenizer.from_pretrained(EMOTION_LLAMA_MODEL, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        EMOTION_LLAMA_MODEL,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map={"": "cpu"},
    )
    model.generation_config.temperature = None
    model.generation_config.top_p = None

    full_prompt = (
        f"What is the emotion state of the speaker in the following text? {prompt}"
    )

    input_features = tokenizer(
        full_prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=2048,
    )

    output_ids = model.generate(
        **input_features,
        do_sample=True,
        temperature=0.9,
        top_p=0.6,
        max_new_tokens=256,
        eos_token_id=tokenizer.eos_token_id,  # stop at EOS
        pad_token_id=tokenizer.eos_token_id,  # for safety
    )

    answer = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    logger.info(f"Generated analysis: {answer}")
    clean_answer = answer.replace(prompt, "")
    logger.info(f"Analysis completed in {time.time() - time_start:.2f} seconds.")
    return clean_answer
