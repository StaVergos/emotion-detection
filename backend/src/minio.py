import io
import logging

import boto3
from botocore.client import Config

from src.config import (
    MINIO_ENDPOINT,
    ACCESS_KEY,
    SECRET_KEY,
    REGION_NAME,
    SIGNATURE_VERSION,
)

logger = logging.getLogger(__name__)


class MinioClient:
    def __init__(
        self,
        endpoint=MINIO_ENDPOINT,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        region_name=REGION_NAME,
        signature_version=SIGNATURE_VERSION,
        bucket_name: str = None,
    ):
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version=signature_version),
            region_name=region_name,
        )

    def bucket_exists(self, bucket: str) -> bool:
        try:
            self.s3.head_bucket(Bucket=bucket)
            return True
        except Exception:
            return False

    def create_bucket(self, bucket: str):
        if not self.bucket_exists(bucket):
            try:
                self.s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={
                        "LocationConstraint": self.s3.meta.region_name
                    },
                )
                logger.info("Created bucket %s", bucket)
            except self.s3.exceptions.BucketAlreadyOwnedByYou:
                logger.info("Bucket %s already exists", bucket)
            except Exception:
                logger.exception("Could not create bucket %s", bucket)
                raise

    def upload_fileobj(self, fileobj, bucket: str, key: str):
        if not self.bucket_exists(bucket):
            self.create_bucket(bucket)

        try:
            self.s3.upload_fileobj(Fileobj=fileobj, Bucket=bucket, Key=key)
            logger.info("Uploaded %s to %s/%s", key, bucket, key)
        except Exception:
            logger.exception("Upload failed for %s/%s", bucket, key)
            raise

    def get_fileobj_in_memory(self, bucket: str, key: str) -> io.BytesIO:
        resp = self.s3.get_object(Bucket=bucket, Key=key)
        return io.BytesIO(resp["Body"].read())
