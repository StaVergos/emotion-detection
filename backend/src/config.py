import logging

# MINIO_ENDPOINT = "http://minio:9000"
MINIO_ENDPOINT = "http://localhost:9000"
ACCESS_KEY = "minioadmin"
SECRET_KEY = "minioadmin"
REGION_NAME = "us-east-1"
SIGNATURE_VERSION = "s3v4"
DEFAULT_BUCKET_NAME = "emotion-detection"


def get_logger():
    """
    Configures the logging settings for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    return logger
