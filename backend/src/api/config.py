import os
import logging
import torch


def get_logger():
    """
    Configures the logging settings for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "emotion_detection_project")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
REGION_NAME = os.getenv("MINIO_REGION", "us-east-1")
SIGNATURE_VERSION = os.getenv("MINIO_SIGNATURE_VERSION", "s3v4")
DEFAULT_BUCKET_NAME = os.getenv("MINIO_BUCKET", "emotion-detection")
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
