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


class RegressionHead(nn.Module):
    r"""Classification head."""

    def __init__(self, config):
        super().__init__()

        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features, **kwargs):
        x = features
        x = self.dropout(x)
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        x = self.out_proj(x)

        return x


class EmotionModel(Wav2Vec2PreTrainedModel):
    r"""Speech emotion classifier."""

    def __init__(self, config):
        super().__init__(config)

        self.config = config
        self.wav2vec2 = Wav2Vec2Model(config)
        self.classifier = RegressionHead(config)
        self.init_weights()

    def forward(
        self,
        input_values,
    ):
        outputs = self.wav2vec2(input_values)
        hidden_states = outputs[0]
        hidden_states = torch.mean(hidden_states, dim=1)
        logits = self.classifier(hidden_states)

        return hidden_states, logits


device = "cpu"
model_name = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"
processor = Wav2Vec2Processor.from_pretrained(model_name)
model = EmotionModel.from_pretrained(model_name).to(device)


def process_func(
    x: np.ndarray,
    sampling_rate: int,
    embeddings: bool = False,
) -> np.ndarray:
    y = processor(x, sampling_rate=sampling_rate)
    y = y["input_values"][0].reshape(1, -1)
    y = torch.from_numpy(y).to(device)
    with torch.no_grad():
        y = model(y)[0 if embeddings else 1]
    return y.detach().cpu().numpy()


def get_emotion_scores(
    audio: np.ndarray,
    sampling_rate: int = 16000,
    embeddings: bool = False,
) -> np.ndarray:
    """
    Get emotion scores from audio signal.

    Args:
        audio (np.ndarray): Audio signal.
        sampling_rate (int): Sampling rate of the audio signal.
        embeddings (bool): If True, return embeddings instead of logits.

    Returns:
        np.ndarray: Emotion scores or embeddings.
    """
    orig_audio, orig_sr = sf.read("audio.wav")
    if orig_audio.ndim > 1:
        orig_audio = np.mean(orig_audio, axis=1)
    target_sr = 16000
    if orig_sr != target_sr:
        audio = librosa.resample(
            orig_audio.astype(np.float32), orig_sr=orig_sr, target_sr=target_sr
        )
    else:
        audio = orig_audio.astype(np.float32)

    signal = audio[np.newaxis, :]

    emotion_scores = process_func(signal, target_sr)
    return emotion_scores


if __name__ == "__main__":
    audio_file = "audio.wav"
    audio, sr = sf.read(audio_file)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    emotion_scores = get_emotion_scores(audio, sampling_rate=sr)
    print("Emotion scores (arousal, dominance, valence):", emotion_scores[0])
    print(
        {
            "arousal": emotion_scores[0][0],
            "dominance": emotion_scores[0][1],
            "valence": emotion_scores[0][2],
            "emotion_scores": emotion_scores[0].tolist(),
            "emotion_raw": emotion_scores,
        }
    )
