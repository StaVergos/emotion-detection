import io
import librosa
import soundfile as sf
from transformers import Wav2Vec2Processor
import numpy as np
import torch
import torch.nn as nn
from transformers.models.wav2vec2.modeling_wav2vec2 import (
    Wav2Vec2Model,
    Wav2Vec2PreTrainedModel,
)

from src.api.config import DEVICE
from src.api.constants import AUDIO_EMOTION_MODEL
from src.api.schemas import AudioVADScore


class RegressionHead(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features, **kwargs):
        x = self.dropout(features)
        x = torch.tanh(self.dense(x))
        x = self.dropout(x)
        return self.out_proj(x)


class EmotionModel(Wav2Vec2PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.wav2vec2 = Wav2Vec2Model(config)
        self.classifier = RegressionHead(config)
        self.init_weights()

    def forward(self, input_values):
        outputs = self.wav2vec2(input_values)
        hidden_states = outputs[0].mean(dim=1)
        return hidden_states, self.classifier(hidden_states)


model_name = AUDIO_EMOTION_MODEL
processor = Wav2Vec2Processor.from_pretrained(model_name)
model = EmotionModel.from_pretrained(model_name).to(DEVICE)


def process_func(
    x: np.ndarray, sampling_rate: int, embeddings: bool = False
) -> np.ndarray:
    inputs = processor(x, sampling_rate=sampling_rate, return_tensors="pt")[
        "input_values"
    ]
    inputs = inputs.to(DEVICE)
    with torch.no_grad():
        outputs = model(inputs)
    return outputs[0 if embeddings else 1].cpu().numpy()


def get_emotion_scores_from_file(
    audio_file: str | bytes | io.BytesIO,
    sampling_rate: int = 16000,
    embeddings: bool = False,
) -> AudioVADScore:
    """
    Reads either a filepath or raw bytes/BytesIO, then returns arousal/dominance/valence.
    """
    if isinstance(audio_file, (bytes, bytearray, io.BytesIO)):
        buf = (
            io.BytesIO(audio_file)
            if isinstance(audio_file, (bytes, bytearray))
            else audio_file
        )
        audio, sr = sf.read(buf)
    else:
        audio, sr = sf.read(audio_file)

    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    if sr != sampling_rate:
        audio = librosa.resample(
            audio.astype(np.float32), orig_sr=sr, target_sr=sampling_rate
        )
    else:
        audio = audio.astype(np.float32)

    scores = process_func(audio[np.newaxis, :], sampling_rate, embeddings)[0]
    return AudioVADScore(
        arousal=float(scores[0]),
        dominance=float(scores[1]),
        valence=float(scores[2]),
    )
