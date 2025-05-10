from moviepy import VideoFileClip
import cv2
import soundfile as sf
import torch
from transformers import (
    LlamaTokenizerFast,
    CLIPImageProcessor,
    Wav2Vec2FeatureExtractor,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)


def extract_audio(input_video: str, output_audio: str = "audio.wav"):
    clip = VideoFileClip(input_video)
    clip.audio.write_audiofile(
        output_audio,
        fps=16_000,  # match HuBERT’s expected 16 kHz
        nbytes=2,  # 16-bit PCM
        codec="pcm_s16le",
        logger=None,
    )
    clip.close()
    return output_audio


def extract_frames(input_video: str, max_frames: int = 4):
    cap = cv2.VideoCapture(input_video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frames, idx = [], 0
    interval = int(fps)  # one frame per second
    while len(frames) < max_frames:
        ret, img = cap.read()
        if not ret:
            break
        if idx % interval == 0:
            # BGR → RGB
            frames.append(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        idx += 1
    cap.release()
    return frames


def main():
    video_file = "my_video.mp4"
    audio_file = extract_audio(video_file)
    frames = extract_frames(video_file, max_frames=4)

    # 1) bitsandbytes 4-bit config
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    # 2) load tokenizer & pad token
    tokenizer = LlamaTokenizerFast.from_pretrained("ZebangCheng/Emotion-LLaMA")
    tokenizer.add_special_tokens({"pad_token": tokenizer.eos_token})

    # 3) load vision & audio preprocessors
    image_processor = CLIPImageProcessor.from_pretrained("openai/clip-vit-base-patch32")
    audio_processor = Wav2Vec2FeatureExtractor.from_pretrained(
        "facebook/hubert-large-ls960-ft"
    )

    # 4) load the quantized, auto-offloaded model
    model = AutoModelForCausalLM.from_pretrained(
        "ZebangCheng/Emotion-LLaMA",
        quantization_config=bnb,
        device_map="auto",
        low_cpu_mem_usage=True,
    )
    device = model.device

    # 5) tokenize text
    prompt = "What emotion is being expressed here?"
    txt = tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
    )

    # 6) preprocess frames → pixel_values
    pix = image_processor(
        images=frames,
        return_tensors="pt",
    ).pixel_values

    # 7) preprocess audio → input_values
    wav, sr = sf.read(audio_file)
    aud = audio_processor(
        wav,
        sampling_rate=sr,
        return_tensors="pt",
    ).input_values

    # 8) collate & move to device
    inputs = {
        "input_ids": txt.input_ids.to(device),
        "attention_mask": txt.attention_mask.to(device),
        "pixel_values": pix.to(device),
        "input_values": aud.to(device),
    }

    # 9) generate with sampling
    out_ids = model.generate(
        **inputs,
        do_sample=True,
        temperature=0.9,
        top_p=0.6,
        max_new_tokens=64,
    )
    reply = tokenizer.decode(out_ids[0], skip_special_tokens=True)
    print("🤖 Emotion-LLaMA says:", reply)


if __name__ == "__main__":
    main()
