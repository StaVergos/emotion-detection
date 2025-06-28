from enum import StrEnum
from pydantic import BaseModel, Field, ConfigDict


class EmotionType(StrEnum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"


class Emotion(BaseModel):
    timestamp: tuple[float, float] = Field(
        description="Start and end timestamps of the emotion segment"
    )
    text: str = Field(description="Text of the segment where the emotion is detected")
    emotion: EmotionType = Field(description="Detected emotion")
    emotion_score: float = Field(description="Confidence score of the detected emotion")
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "timestamp": (34.36, 37.8),
                "text": " And you can do that on your own if you want.",
                "emotion": "neutral",  # Example emotion
                "emotion_score": 0.9420299530029297,
            }
        },
    )


class EmotionDetection(BaseModel):
    video_filename: str = Field(description="The name of the video file")
    transcript: str = Field(description="The transcript of the video")
    timestamps: tuple[float, float] = Field(
        description="List of timestamps in the video",
    )
    emotions: list[Emotion] = Field(
        description="List of detected emotions at each timestamp",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_filename": "example_video.mp4",
                "transcript": "This is an example transcript of the video.",
                "timestamps": (0.0, 120.0),
                "emotions": [
                    {
                        "timestamp": (34.36, 37.8),
                        "text": "And you can do that on your own if you want.",
                        "emotion": "neutral",
                        "emotion_score": 0.9420299530029297,
                    },
                ],
            }
        }
    )
