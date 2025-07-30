import time
import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel

from src.api.config import get_logger
from src.api.config import DEVICE

tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
lm_model = GPT2LMHeadModel.from_pretrained("gpt2")

lm_model.config.pad_token_id = tokenizer.eos_token_id

device = torch.device(DEVICE)
lm_model.to(device).eval()

logger = get_logger()


def analyze_prompt_with_gpt2(prompt: str, max_analysis_tokens: int = 200) -> str:
    """
    Break a full text prompt into context-sized windows (including instruction header and trailer),
    run each through GPT-2, and concatenate the generated analyses.

    :param prompt: Pre-constructed prompt string (header + timeline + instruction).
    :param max_analysis_tokens: Number of tokens GPT-2 should generate for each window.
    :return: Concatenated analysis text across all windows.
    """
    start_time = time.time()

    model_max = lm_model.config.n_positions  # typically 1024
    max_prompt_tokens = model_max - max_analysis_tokens

    header_text = (
        "You are a clinical psychologist.  Below is a multimodal breakdown of a speaker.\n"
        "Please summarize their overall emotional and psychological condition.\n\n"
        "Timeline:\n"
    )
    trailer_text = "\nAnswer in a few paragraphs:"

    header_ids = tokenizer.encode(header_text, add_special_tokens=False)
    trailer_ids = tokenizer.encode(trailer_text, add_special_tokens=False)

    all_ids = tokenizer.encode(prompt, add_special_tokens=False)
    middle_ids = all_ids[len(header_ids) :]
    if len(trailer_ids) > 0:
        middle_ids = middle_ids[: -len(trailer_ids)]

    chunk_size = max_prompt_tokens - len(header_ids) - len(trailer_ids)

    middle_windows = [
        middle_ids[i : i + chunk_size] for i in range(0, len(middle_ids), chunk_size)
    ]

    analyses = []
    for idx, win_ids in enumerate(middle_windows, 1):
        input_ids = header_ids + win_ids + trailer_ids
        input_tensor = torch.tensor([input_ids], device=device)
        attention_mask = torch.ones_like(input_tensor)

        total_len = input_tensor.shape[-1] + max_analysis_tokens
        with torch.no_grad():
            output_ids = lm_model.generate(
                input_ids=input_tensor,
                attention_mask=attention_mask,
                max_length=total_len,
                do_sample=True,
                top_p=0.9,
                pad_token_id=lm_model.config.pad_token_id,
            )[0]

        gen_ids = output_ids[len(input_ids) :]
        analysis_text = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

        analyses.append(
            f"=== Analysis window {idx}/{len(middle_windows)} ===\n{analysis_text}"
        )

    end_time = time.time()
    logger.info(
        f"GPT-2 total analysis time: {end_time - start_time:.2f}s across {len(middle_windows)} window(s)"
    )

    return "\n\n".join(analyses)
