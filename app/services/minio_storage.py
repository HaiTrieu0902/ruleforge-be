from minio import Minio
from minio.error import S3Error
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import BinaryIO, Optional
import uuid
from datetime import datetime
import os

from app.core.config import settings

class MinIOStorage:
    """Service for handling file uploads to MinIO object storage."""
    
    def __init__(self):
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def initialize_bucket(self):
        """Create bucket if it doesn't exist."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._create_bucket_if_not_exists
            )
            print(f"✅ MinIO bucket '{self.bucket_name}' is ready")
            return True
        except Exception as e:
            print(f"❌ Error initializing MinIO bucket: {str(e)}")
            return False
    
    def _create_bucket_if_not_exists(self):
        """Check if bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"✅ Created bucket: {self.bucket_name}")
            else:
                print(f"✅ Bucket already exists: {self.bucket_name}")
        except S3Error as e:
            raise Exception(f"Failed to create bucket: {str(e)}")
    
    async def upload_file(self, file_content: BinaryIO, filename: str, content_type: str = "application/octet-stream") -> dict:
        """
        Upload a file to MinIO.
        
        Args:
            file_content: File content as binary stream
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            dict: Upload result with file info
        """
        try:
            # Generate unique filename to avoid conflicts
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            object_name = f"documents/{unique_filename}"
            
            # Get file size
            file_content.seek(0, 2)  # Seek to end
            file_size = file_content.tell()
            file_content.seek(0)  # Reset to beginning
            
            # Upload to MinIO
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=file_content,
                    length=file_size,
                    content_type=content_type
                )
            )
            
            # Generate presigned URL for access (valid for 7 days)
            file_url = await self.get_file_url(object_name)
            
            return {
                "success": True,
                "object_name": object_name,
                "original_filename": filename,
                "unique_filename": unique_filename,
                "file_size": file_size,
                "content_type": content_type,
                "file_url": file_url,
                "bucket": self.bucket_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_file_url(self, object_name: str, expires_in_days: int = 7) -> str:
        """Generate a presigned URL for file access."""
        try:
            url = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    expires=datetime.timedelta(days=expires_in_days)
                )
            )
            return url
        except Exception as e:
            print(f"Error generating file URL: {str(e)}")
            return ""
    
    async def download_file(self, object_name: str) -> Optional[bytes]:
        """Download file content from MinIO."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.get_object(self.bucket_name, object_name)
            )
            content = response.read()
            response.close()
            response.release_conn()
            return content
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
            return None
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete file from MinIO."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.remove_object(self.bucket_name, object_name)
            )
            return True
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
            return False
    
    async def list_files(self, prefix: str = "documents/") -> list:
        """List files in the bucket with optional prefix."""
        try:
            objects = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: list(self.client.list_objects(self.bucket_name, prefix=prefix))
            )
            
            files = []
            for obj in objects:
                files.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag
                })
            
            return files
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []
    
    def close(self):
        """Clean up resources."""
        self.executor.shutdown(wait=True)

# Global instance
minio_storage = MinIOStorage()