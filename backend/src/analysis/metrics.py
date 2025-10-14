from __future__ import annotations
from datetime import timezone

from src.api.config import get_logger
from src.api.schemas import EmotionDetectionItem, EvaluationMetrics

logger = get_logger()


def compute_evaluation_metrics(edi: EmotionDetectionItem) -> EvaluationMetrics:
    """Compute evaluation metrics for a processed video."""

    segments = edi.emotion_chunks or []
    total_segments = len(segments)

    face_success_rate = None
    if total_segments:
        successful_faces = sum(
            1
            for seg in segments
            if isinstance(seg.face_emotions, dict) and len(seg.face_emotions) > 0
        )

        face_success_rate = (
            (successful_faces / total_segments) * 100 if total_segments else None
        )

    avg_processing_time = None
    if (
        edi.video_uploaded_at
        and edi.video_face_recognition_emotion_at
        and total_segments
    ):
        uploaded = edi.video_uploaded_at
        completed = edi.video_face_recognition_emotion_at

        if uploaded.tzinfo is None:
            uploaded = uploaded.replace(tzinfo=timezone.utc)
        if completed.tzinfo is None:
            completed = completed.replace(tzinfo=timezone.utc)

        total_time = (completed - uploaded).total_seconds()
        avg_processing_time = total_time / total_segments

    return EvaluationMetrics(
        face_detection_success_rate=face_success_rate,
        average_processing_time_seconds=avg_processing_time,
    )
