from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

PyObjectId = Annotated[str, BeforeValidator(str)]


class BaseSchema(BaseModel):
    """
    Base schema: serialize enums by their values.
    """

    model_config = ConfigDict(use_enum_values=True)


class EmotionType(StrEnum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    SURPRISE = "surprise"
    NEUTRAL = "neutral"
    FEAR = "fear"
    DISGUST = "disgust"


class Error(BaseSchema):
    code: int = Field(..., description="HTTP status code for the error")
    message: str = Field(..., description="Error message describing the issue")
    source: str | None = Field(
        default=None,
        description="Optional source of the error, e.g., field name or operation",
    )


class VideoError(BaseSchema):
    errors: list[Error] = Field(
        default_factory=list,
        description="List of errors encountered during video processing",
    )


class AudioVADScore(BaseSchema):
    arousal: float = Field(..., description="Arousal score from audio VAD analysis")
    dominance: float = Field(..., description="Dominance score from audio VAD analysis")
    valence: float = Field(..., description="Valence score from audio VAD analysis")


class TranscriptionChunk(BaseSchema):
    timestamp: tuple[float, float] = Field(
        ..., description="Start and end timestamps of the audio chunk in seconds"
    )
    text: str = Field(..., description="Transcription text for this audio chunk")
    emotion: Optional[EmotionType] = Field(
        None, description="Detected emotion label for this chunk, if applicable"
    )
    emotion_score: Optional[float] = Field(
        None, description="Confidence score of the detected emotion, if applicable"
    )
    audio_chunk_file_path: str | None = Field(
        default=None,
        description="MinIO key where the audio chunk is stored, if applicable",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": (0.0, 5.0),
                "text": "This is an example transcription.",
                "emotion": "joy",
                "emotion_score": 0.95,
            }
        },
    )


class TranscriptionResult(BaseSchema):
    text: str = Field(..., description="Transcription text of the audio")
    chunks: list[TranscriptionChunk] = Field(
        default_factory=list,
        description="List of audio chunks with timestamps and text",
    )


class FaceEmotions(BaseSchema):
    angry: float | None = Field(
        default=None, description="Probability of anger emotion"
    )
    disgust: float | None = Field(
        default=None, description="Probability of disgust emotion"
    )
    fear: float | None = Field(default=None, description="Probability of fear emotion")
    happy: float | None = Field(
        default=None, description="Probability of happiness emotion"
    )
    neutral: float | None = Field(
        default=None, description="Probability of neutrality emotion"
    )
    sad: float | None = Field(
        default=None, description="Probability of sadness emotion"
    )


class EmotionSegment(BaseSchema):
    timestamp: tuple[float, float] = Field(
        ..., description="Start and end timestamps of the emotion segment"
    )
    text: str = Field(..., description="Transcript text for this segment")
    emotion: EmotionType = Field(..., description="Detected emotion label")
    emotion_score: float = Field(
        ..., description="Confidence score of the detected emotion"
    )
    vad_score: AudioVADScore | None = Field(
        default=None,
        description="Optional VAD scores for arousal, dominance, and valence",
    )
    audio_chunk_file_path: str | None = Field(
        default=None,
        description="MinIO key where the audio chunk is stored, if applicable",
    )
    face_emotions: FaceEmotions | None = Field(
        default=None,
        description="Optional face emotion probabilities for this segment",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": (34.36, 37.8),
                "text": "And you can do that on your own if you want.",
                "emotion": "neutral",
                "emotion_score": 0.94203,
            }
        },
    )


class AudioChunk(BaseSchema):
    filename: str = Field(..., description="Temporary file path of the audio chunk")
    start: float = Field(..., description="Start time of the audio chunk in seconds")
    end: float = Field(..., description="End time of the audio chunk in seconds")


class EmotionDetectionItem(BaseSchema):
    model_config = ConfigDict(
        serialize_by_alias=True,
    )
    id: PyObjectId = Field(alias="_id", description="MongoDB document ID as string")
    video_filename: str = Field(description="Original uploaded video filename")
    video_object_path: str = Field(description="MinIO key where the video is stored")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this record was created",
    )
    audio_object_path: str | None = Field(
        None, description="MinIO key where the extracted audio is stored"
    )
    transcription_result: str | None = Field(
        default=None, description="Full ASR transcript of the video audio"
    )
    emotion_chunks: list[EmotionSegment] | None = Field(
        default_factory=list,
        description="List of detected emotions with timestamps",
    )
    video_uploaded_at: datetime | None = Field(
        default=None,
        description="Timestamp when the video was uploaded",
    )
    audio_extracted_at: datetime | None = Field(
        default=None,
        description="Timestamp when the audio was extracted from the video",
    )
    transcription_completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the transcription was completed",
    )
    transcription_chunks_emotion_completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when emotion detection on transcription chunks was completed",
    )
    audio_chunks_uploaded_at: datetime | None = Field(
        default=None,
        description="Timestamp when audio chunks were uploaded to MinIO",
    )
    audio_chunks_emotion_completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when emotion detection on audio chunks was completed",
    )
    video_face_recognition_emotion_at: datetime | None = Field(
        default=None,
        description="Timestamp when emotion detection on video faces was completed",
    )

    def as_document(self) -> dict:
        """Convert the model to a MongoDB document format."""
        doc = self.model_dump(by_alias=True, exclude_none=True)
        if "id" in doc:
            doc["_id"] = doc.pop("id")
        return doc


class UploadedVideoResponse(EmotionDetectionItem):
    extract_job_id: str = Field(
        description="Unique identifier for the video processing job",
        example="1234567890abcdef",
    )


class VideosResponse(BaseSchema):
    videos: list[EmotionDetectionItem] = Field(..., description="Video items list")
    total: int = Field(..., description="Total number of videos in the collection")

    model_config = ConfigDict(json_schema_extra={"example": {"total": 1}})
