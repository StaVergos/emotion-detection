from transformers import pipeline
import time
from src.api.config import get_logger, DEVICE

logger = get_logger()

init_start = time.time()
emotion_pipe = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=False,
    device=DEVICE,
)
logger.info(f"Emotion detection model loaded in {time.time() - init_start:.2f} seconds")


def emotional_detection(transcript: dict) -> str:
    start_time = time.time()
    text = transcript.get("text", transcript)
    prompt = (
        "Given the following transcript, identify the speaker's emotion:\n"
        f"{text}\nEmotion:"
    )
    result = emotion_pipe(prompt)
    end_time = time.time()
    logger.info(f"Emotion detection completed in {end_time - start_time:.2f} seconds")
    print(f"Emotion detection completed in {end_time - start_time:.2f} seconds")
    logger.info(f"Detected emotion raw: {result}")
    return result[0]["label"]


def emotional_detection_for_each_timestamp(transcript: dict) -> list:
    """
    Process each timestamp in the transcript and return a list of emotions.
    """
    start_time = time.time()
    emotions = []
    chunks = transcript.get("chunks", [])
    if not chunks:
        logger.warning("No chunks found in transcript, returning empty emotions list")
        raise ValueError("No chunks found in transcript")
    else:
        i = 0
        for segment in chunks:
            time_start = time.time()
            text = segment.get("text", "")
            timestamp = segment.get("timestamp", "")
            if text:
                prompt = (
                    "Given the following transcript, identify the speaker's emotion:\n"
                    f"{text}\nEmotion:"
                )
                result = emotion_pipe(prompt)
                emotions.append({"emotions": result, "timestamp": timestamp})
            else:
                emotions.append(
                    {
                        "emotions": [{"label": "unknown", "score": 0.0}],
                        "timestamp": timestamp,
                    }
                )
            time_end = time.time()
            logger.info(f"Processed segment {i} in {time_end - time_start:.2f} seconds")
            i += 1
    if not emotions:
        logger.warning("No emotions detected, returning empty list")
        raise ValueError("No emotions detected")
    logger.info(f"Emotions detected for {len(emotions)} segments")
    print(f"Emotions detected for {len(emotions)} segments")

    end_time = time.time()
    logger.info(
        f"Emotion detection for each timestamp completed in {end_time - start_time:.2f} seconds"
    )
    print(
        f"Emotion detection for each timestamp completed in {end_time - start_time:.2f} seconds"
    )
    transcript_chunks = transcript.get("chunks", [])
    for i, segment in enumerate(transcript_chunks):
        segment["emotion"] = emotions[i]["emotions"][0]["label"]
        segment["emotion_score"] = emotions[i]["emotions"][0]["score"]
    return transcript_chunks
