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


class TranscriptProcessStatus(StrEnum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"


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


class EmotionSegment(BaseSchema):
    timestamp: tuple[float, float] = Field(
        ..., description="Start and end timestamps of the emotion segment"
    )
    text: str = Field(..., description="Transcript text for this segment")
    emotion: EmotionType = Field(..., description="Detected emotion label")
    emotion_score: float = Field(
        ..., description="Confidence score of the detected emotion"
    )
    audio_chunk_file_path: str | None = Field(
        default=None,
        description="MinIO key where the audio chunk is stored, if applicable",
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
    transcript_process_status: TranscriptProcessStatus | None = Field(
        None,
        description="Current status of the video processing",
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

    def as_document(self):
        """
        Convert the EmotionDetectionItem to a dictionary suitable for MongoDB storage.
        """
        emotion_chunks_data = []
        if self.emotion_chunks:
            for chunk in self.emotion_chunks:
                emotion_chunks_data.append(chunk.model_dump())
        return {
            "_id": self.id,
            "video_filename": self.video_filename,
            "video_object_path": self.video_object_path,
            "created_at": self.created_at,
            "transcript_process_status": self.transcript_process_status,
            "audio_object_path": self.audio_object_path,
            "transcription_result": self.transcription_result,
            "emotion_chunks": emotion_chunks_data,
        }


class UploadedVideoResponse(EmotionDetectionItem):
    extract_job_id: str = Field(
        description="Unique identifier for the video processing job",
        example="1234567890abcdef",
    )


class VideosResponse(BaseSchema):
    videos: list[EmotionDetectionItem] = Field(..., description="Video items list")
    total: int = Field(..., description="Total number of videos in the collection")

    model_config = ConfigDict(json_schema_extra={"example": {"total": 1}})
