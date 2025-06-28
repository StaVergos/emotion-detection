from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["emotion_detection_project"]
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
