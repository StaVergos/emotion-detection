from pymongo import MongoClient
from src.api.config import MONGODB_URI, MONGODB_DB

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
emotion_detection_collection = db.emotion_detection

emotion_detection_collection.create_index("video_filename", unique=True)


def check_record_exists(video_filename: str) -> bool:
    """
    Check if a record with the given video filename already exists in the collection.
    """
    return (
        emotion_detection_collection.count_documents({"video_filename": video_filename})
        > 0
    )
