from enum import StrEnum
from typing import Annotated, Any, List
from pydantic import BaseModel, Field, BeforeValidator
from pydantic import ConfigDict
from datetime import datetime, timezone

PyObjectId = Annotated[str, BeforeValidator(str)]


class EmotionType(StrEnum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    SURPRISE = "surprise"
    NEUTRAL = "neutral"
    FEAR = "fear"
    DISGUST = "disgust"


class TranscriptProcessStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"


class Emotion(BaseModel):
    timestamp: tuple[float, float] = Field(
        description="Start and end timestamps of the emotion segment"
    )
    text: str = Field(description="Transcript text for this segment")
    emotion: EmotionType = Field(description="Detected emotion label")
    emotion_score: float = Field(description="Confidence score of the detected emotion")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "timestamp": (34.36, 37.8),
                "text": "And you can do that on your own if you want.",
                "emotion": "neutral",
                "emotion_score": 0.9420299530029297,
            }
        },
    )


class VideoMetadata(BaseModel):
    id: PyObjectId = Field(alias="_id", description="MongoDB document ID as string")
    video_filename: str = Field(description="Original uploaded video filename")
    video_object: str = Field(description="MinIO key where the video is stored")
    created_at: datetime = Field(
        default_factory=datetime.now(timezone.utc),
        description="UTC timestamp when this record was created",
    )
    transcript_process_status: TranscriptProcessStatus = Field(
        default="uploaded",
        description="Current status of the video processing (e.g., 'uploaded', 'processing', 'completed')",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "b2a3c489ca3249a3a46e8358e483f611",
                "video_filename": "my_video.mp4",
                "video_object": "videos/b2a3c489ca3249a3a46e8358e483f611/my_video.mp4",
                "created_at": "2025-06-29T08:49:03.081781+00:00",
            }
        },
    )


class EmotionDetection(VideoMetadata):
    audio_object: str | None = Field(
        description="MinIO key where the extracted audio is stored",
        default=None,
    )
    transcript: str | None = Field(
        description="Full ASR transcript of the video audio", default=None
    )
    emotions: List[Emotion] | None = Field(
        description="List of detected emotions with timestamps",
        default=[],
    )
    emotion_prompt_result: str | None = Field(
        default=None,
        description="Result of the emotion detection prompt, if applicable",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_filename": "example_video.mp4",
                "video_object": "videos/605c5a2e2e3a3f4b5c6d7e8f/example_video.mp4",
                "audio_object": "audio/605c5a2e2e3a3f4b5c6d7e8f.wav",
                "transcript": "This is an example transcript of the video.",
                "emotions": [
                    {
                        "timestamp": (34.36, 37.8),
                        "text": "And you can do that on your own if you want.",
                        "emotion": "neutral",
                        "emotion_score": 0.9420299530029297,
                    }
                ],
                "created_at": "2025-06-29T02:18:05Z",
                "transcript_process_status": "completed",
                "emotion_prompt_result": "The detected emotion is neutral.",
            }
        }
    )


class VideoListItem(EmotionDetection):
    id: PyObjectId = Field(alias="_id", description="MongoDB document ID as string")
    model_config = ConfigDict(populate_by_name=True)
