import time
import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel

from src.api.schemas import EmotionSegment
from src.api.config import get_logger
from src.api.constants import DEVICE

tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
lm_model = GPT2LMHeadModel.from_pretrained("gpt2")

lm_model.config.pad_token_id = tokenizer.eos_token_id

device = torch.device(DEVICE)
lm_model.to(device).eval()

logger = get_logger()


def build_condition_prompt(chunks: list[EmotionSegment]) -> str:
    lines = [
        "You are a clinical psychologist.  Below is a multimodal breakdown of a speaker."
    ]
    lines.append(
        "Please summarize their overall emotional and psychological condition.\n"
    )
    lines.append("Timeline:\n")
    for seg in chunks:
        start, end = seg.timestamp
        ts = f"{int(start // 60):02d}:{int(start % 60):02d}-{int(end // 60):02d}:{int(end % 60):02d}"
        te = f"{seg.emotion} ({seg.emotion_score:.2f})"
        vad = seg.vad_score
        va = f"A{vad.arousal:.2f}/V{vad.valence:.2f}/D{vad.dominance:.2f}"
        fe = seg.face_emotions
        face_str = ", ".join(f"{k}:{getattr(fe, k):.2f}" for k in fe.model_fields)
        text = seg.text.strip()
        lines.append(
            f"[{ts}]\n  • Text: {text}\n  • Text-emo: {te}\n  • Audio(VAD): {va}\n  • Face: {face_str}\n"
        )
    lines.append("\nAnswer in a few paragraphs:")
    return "\n".join(lines)


def analyze_prompt_with_gpt2(
    chunks: list[EmotionSegment], max_analysis_tokens: int = 200
) -> str:
    """
    Break the full timeline into windows that fit GPT-2's 1024-token context,
    analyze each window, and concatenate the results into one long analysis.
    """
    start_time = time.time()
    model_max = lm_model.config.n_positions  # 1024
    max_prompt_tokens = model_max - max_analysis_tokens

    def build_prompt(subchunks):
        return build_condition_prompt(subchunks)

    def tok_len(txt):
        return len(tokenizer(txt, add_special_tokens=False)["input_ids"])

    header = (
        "You are a clinical psychologist.  Below is a multimodal breakdown of a speaker.\n"
        "Please summarize their overall emotional and psychological condition.\n\n"
        "Timeline:\n"
    )
    header_len = tok_len(header)

    windows = []
    current, curr_len = [], header_len
    for seg in chunks:
        seg_start_time = time.time()
        seg_txt = (
            f"[{int(seg.timestamp[0] // 60):02d}:{int(seg.timestamp[0] % 60):02d}"
            f" -{int(seg.timestamp[1] // 60):02d}:{int(seg.timestamp[1] % 60):02d}]\n"
            f"  • Text: {seg.text.strip()}\n"
            f"  • Text-emo: {seg.emotion} ({seg.emotion_score:.2f})\n"
            f"  • Audio(VAD): A{seg.vad_score.arousal:.2f}"
            f"/V{seg.vad_score.valence:.2f}"
            f"/D{seg.vad_score.dominance:.2f}\n"
            f"  • Face: {', '.join(f'{k}:{getattr(seg.face_emotions, k):.2f}' for k in seg.face_emotions.model_fields)}\n\n"
        )
        seg_len = tok_len(seg_txt)

        if curr_len + seg_len > max_prompt_tokens:
            if current:
                windows.append(current)
            current = [seg]
            curr_len = header_len + seg_len
        else:
            current.append(seg)
            curr_len += seg_len
        seg_end_time = time.time()
        logger.info(
            f"Time elapsed for segment {seg.text.strip()}: {seg_end_time - seg_start_time:.2f} seconds"
        )

    if current:
        windows.append(current)

    analyses = []
    for i, win in enumerate(windows, 1):
        prompt = build_prompt(win)
        enc = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=max_prompt_tokens,
        )
        input_ids = enc.input_ids.to(device)
        attention_mask = enc.attention_mask.to(device)

        total_len = input_ids.shape[-1] + max_analysis_tokens
        with torch.no_grad():
            output_ids = lm_model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=total_len,
                do_sample=True,
                top_p=0.9,
                pad_token_id=lm_model.config.pad_token_id,
            )[0]
        analysis_ids = output_ids[input_ids.shape[-1] :]
        text = tokenizer.decode(analysis_ids, skip_special_tokens=True).strip()
        analyses.append(f"=== Analysis for window {i}/{len(windows)} ===\n{text}")

    end_time = time.time()
    logger.info(
        f"Total analysis time: {end_time - start_time:.2f} seconds for {len(chunks)} segments"
    )
    full_analysis = "\n\n".join(analyses)
    return full_analysis
