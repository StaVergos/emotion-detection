from pymongo import MongoClient
from src.api.config import MONGODB_URI, MONGODB_DB

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
emotion_detection_collection = db.emotion_detection
emotion_detection_collection.create_index("video_filename", unique=True)
openai_analysis_collection = db.openai_analysis
openai_analysis_collection.create_index("video_id", unique=True)


def check_record_exists(video_filename: str) -> bool:
    """
    Check if a record with the given video filename already exists in the collection.
    """
    return (
        emotion_detection_collection.count_documents({"video_filename": video_filename})
        > 0
    )


def check_video_has_openai_analysis(video_id: str) -> bool:
    """
    Check if a record with the given video ID has an OpenAI analysis.
    """
    return openai_analysis_collection.count_documents({"video_id": video_id}) > 0
