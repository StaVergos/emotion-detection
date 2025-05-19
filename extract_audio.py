from moviepy import VideoFileClip
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    pipeline,
)
import torch


def extract_audio_from_video(input_video: str, output_audio: str = "audio.wav"):
    """
    Extracts a 16 kHz, 16-bit WAV from the video.
    """
    clip = VideoFileClip(input_video)
    clip.audio.write_audiofile(
        output_audio,
        fps=16_000,  # Whisper expects 16 kHz
        nbytes=2,  # 16-bit PCM
        codec="pcm_s16le",
        logger=None,  # suppress MoviePy logs
    )
    clip.close()
    return output_audio


def main():
    # ← Hard-coded filenames & model
    video_file = "my_video.mp4"
    audio_file = "audio.wav"
    whisper_model = "openai/whisper-small"

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Running on device: {device}")

    print(f"▶️  Extracting audio from {video_file} → {audio_file}")
    extract_audio_from_video(video_file, audio_file)

    print("📝 Transcribing in chunks with Whisper…")
    asr = pipeline(
        "automatic-speech-recognition",
        model=whisper_model,
        chunk_length_s=20,
        stride_length_s=5,
        device=device,
        return_timestamps=True,
)
    asr.feature_extractor.return_attention_mask = True
    result = asr(audio_file)
    print(f"Transcription result: \n {result}")
    transcript = result.get("text")

    print("\n=== Transcript ===\n")
    print(transcript)

    # 1) Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        "ZebangCheng/Emotion-LLaMA", use_fast=True
    )
    tokenizer.pad_token = tokenizer.eos_token

    # 2) Load the full model onto CPU in fp16
    model = AutoModelForCausalLM.from_pretrained(
        "ZebangCheng/Emotion-LLaMA",
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map={"": "cpu"},
    )
    model.generation_config.temperature=None
    model.generation_config.top_p=None

    prompt = (
        "Given the following transcript, please identify the emotion of the speaker. "
        f"Transcript: {transcript}\n"
    )
    # 3) Tokenize & run on CPU
    input_features = tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
    )

    # 4) Generate
    output_ids = model.generate(
        **input_features,
        do_sample=True,
        temperature=0.9,
        top_p=0.6,
        max_new_tokens=256,
        eos_token_id=tokenizer.eos_token_id,  # ← stop at EOS
        pad_token_id=tokenizer.eos_token_id,  # ← for safety
    )

    # 5) Decode & print
    answer = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    # print("\n=== Emotion ===\n", answer)
    clean_answer = answer.replace(prompt, "")
    print("\n=== Emotion ===\n", clean_answer)


if __name__ == "__main__":
    main()
