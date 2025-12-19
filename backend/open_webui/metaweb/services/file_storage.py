# open_webui/metaweb/services/file_storage.py
# MinIO File Storage Service

import os
import uuid
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
from minio import Minio
from minio.error import S3Error
import logging

logger = logging.getLogger(__name__)


class FileStorageService:
    """MinIO File Storage Service"""

    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'metaweb_admin')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'MetaWeb2025!@')
        self.bucket_name = os.getenv('MINIO_BUCKET', 'metaweb-assignments')
        self.secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        content_type: str = "application/octet-stream",
        folder: str = "assignments"
    ) -> dict:
        """Upload file to MinIO"""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            file_ext = os.path.splitext(file_name)[1]
            object_name = f"{folder}/{datetime.now().strftime('%Y%m%d')}/{file_id}{file_ext}"

            # Get file size
            file_data.seek(0, os.SEEK_END)
            file_size = file_data.tell()
            file_data.seek(0)

            # Upload file
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type
            )

            logger.info(f"File uploaded: {object_name}")

            return {
                'file_id': file_id,
                'file_path': object_name,
                'original_name': file_name,
                'size': file_size,
                'content_type': content_type,
                'url': f"/{self.bucket_name}/{object_name}"
            }

        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise Exception(f"File upload failed: {str(e)}")

    def download_file(self, file_path: str) -> BinaryIO:
        """Download file from MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, file_path)
            return response
        except S3Error as e:
            logger.error(f"Error downloading file: {e}")
            raise Exception(f"File download failed: {str(e)}")

    def get_presigned_url(
        self,
        file_path: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Get presigned URL for file access"""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                file_path,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise Exception(f"Failed to generate URL: {str(e)}")

    def delete_file(self, file_path: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(self.bucket_name, file_path)
            logger.info(f"File deleted: {file_path}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def list_files(self, prefix: str = "") -> list:
        """List files in bucket"""
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )

            files = []
            for obj in objects:
                files.append({
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified
                })

            return files
        except S3Error as e:
            logger.error(f"Error listing files: {e}")
            return []


# Global instance
file_storage = None  # Initialize when .env is loaded
