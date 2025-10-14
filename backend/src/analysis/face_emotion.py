from collections import Counter

from moviepy import VideoFileClip
from PIL import Image
import pandas as pd
import torch
import numpy as np
from facenet_pytorch import MTCNN
from transformers import (
    AutoFeatureExtractor,
    AutoModelForImageClassification,
    AutoConfig,
)
from src.api.config import DEVICE, get_logger
from src.api.constants import FACE_EMOTION_MODEL

logger = get_logger()


device = torch.device(DEVICE)
mtcnn = MTCNN(
    image_size=160,
    margin=0,
    min_face_size=200,
    thresholds=[0.6, 0.7, 0.7],
    factor=0.709,
    post_process=True,
    keep_all=False,
    device=device,
)
extractor = AutoFeatureExtractor.from_pretrained(FACE_EMOTION_MODEL)
model = AutoModelForImageClassification.from_pretrained(FACE_EMOTION_MODEL).to(device)
config = AutoConfig.from_pretrained(FACE_EMOTION_MODEL)
id2label = config.id2label


def detect_emotions(image) -> tuple[Image.Image | None, dict | None]:
    """
    Detect emotions in a PIL or numpy image.
    Returns a tuple (face_crop, probabilities_dict),
    or (None, None) if no face detected or error.
    """
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)

    try:
        boxes, _ = mtcnn.detect(image)
    except RuntimeError:
        return None, None

    if boxes is None or len(boxes) == 0 or boxes[0] is None:
        return None, None

    face = image.crop(boxes[0])

    inputs = extractor(images=face, return_tensors="pt").to(device)
    outputs = model(**inputs)
    probs = (
        torch.nn.functional.softmax(outputs.logits, dim=-1)[0].detach().cpu().numpy()
    )
    class_probs = {id2label[i]: float(probs[i]) for i in range(len(probs))}
    logger.info(f"Detected emotions: {class_probs}")
    return face, class_probs


def analyze_video_intervals(
    video_path: str, timestamps: list[tuple[float, float]], skip: int = 2
) -> list[dict]:
    clip = VideoFileClip(video_path).without_audio()
    fps = clip.fps
    results = []

    for start, end in timestamps:
        subclip = clip.subclipped(start, end)
        sample_fps = fps / skip
        frames = [frame for frame in subclip.iter_frames(fps=sample_fps)]

        all_probs = []
        segment_emotions = []  # reset per interval

        for arr in frames:
            _, probs = detect_emotions(arr)
            if probs is not None and len(probs) > 0:
                all_probs.append(probs)
                # argmax label for this frame
                segment_emotions.append(max(probs, key=probs.get))

        mean_probs = pd.DataFrame(all_probs).mean().to_dict() if all_probs else {}

        if segment_emotions:
            initial_emotion = segment_emotions[0]
            final_emotion = segment_emotions[-1]
            counts = Counter(segment_emotions)
            most_common = counts.most_common()
            top_freq = most_common[0][1]
            dominant_candidates = [emo for emo, f in most_common if f == top_freq]
            dominant_emotion = max(
                dominant_candidates, key=lambda emo: mean_probs.get(emo, 0.0)
            )
            emotion_stability = "stable" if len(counts) == 1 else "changed"
        else:
            initial_emotion = final_emotion = None
            dominant_emotion = (
                max(mean_probs, key=mean_probs.get) if mean_probs else None
            )
            emotion_stability = None

        face_summary = {
            **mean_probs,
            "initial_emotion": initial_emotion,
            "final_emotion": final_emotion,
            "dominant_emotion": dominant_emotion,
            "emotion_stability": emotion_stability,
        }

        results.append({"timestamp": (start, end), "emotions": face_summary})

    return results
