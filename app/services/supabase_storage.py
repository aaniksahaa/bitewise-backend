import uuid
import mimetypes
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path

from supabase import create_client, Client
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.core.config import settings


class SupabaseStorageService:
    """Service for handling Supabase Storage operations."""
    
    _client: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get Supabase client."""
        if cls._client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("Supabase URL and key must be configured")
            
            cls._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        return cls._client
    
    @staticmethod
    def validate_image_file(file: UploadFile) -> Tuple[bool, str]:
        """
        Validate uploaded image file.
        Returns: (is_valid, error_message)
        """
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
        
        # Check file type using filename extension and content_type
        file_extension = Path(file.filename or "").suffix.lower()
        content_type = file.content_type or ""
        
        # Map extensions to MIME types
        valid_extensions = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg', 
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        
        # Check if extension is valid
        if file_extension not in valid_extensions:
            return False, f"Invalid file extension. Allowed: {', '.join(valid_extensions.keys())}"
        
        # Check content type (either from upload or inferred from extension)
        expected_mime = valid_extensions[file_extension]
        if content_type and content_type not in settings.ALLOWED_IMAGE_TYPES:
            return False, f"Invalid content type. Allowed types: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        
        # Additional validation using PIL
        try:
            file.file.seek(0)
            with Image.open(file.file) as img:
                img.verify()  # Verify it's a valid image
            file.file.seek(0)  # Reset after verification
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
        
        return True, ""
    
    @staticmethod
    def get_image_metadata(file: UploadFile) -> dict:
        """Extract metadata from image file."""
        try:
            file.file.seek(0)
            with Image.open(file.file) as img:
                metadata = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                }
                
                # Get EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    if exif_data:
                        metadata["has_exif"] = True
                        # Add relevant EXIF data (be selective to avoid too much data)
                        if 306 in exif_data:  # DateTime
                            metadata["datetime"] = exif_data[306]
                else:
                    metadata["has_exif"] = False
            
            file.file.seek(0)  # Reset file pointer
            return metadata
        except Exception as e:
            file.file.seek(0)
            return {"error": f"Could not extract metadata: {str(e)}"}
    
    @classmethod
    def upload_image(
        cls, 
        file: UploadFile, 
        user_id: int, 
        folder: str = "chat_images"
    ) -> Tuple[str, dict]:
        """
        Upload image to Supabase Storage.
        
        Args:
            file: The uploaded file
            user_id: ID of the user uploading the file
            folder: Folder in storage bucket
            
        Returns:
            Tuple of (download_url, metadata)
        """
        # Validate file
        is_valid, error_msg = cls.validate_image_file(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Get image metadata
        metadata = cls.get_image_metadata(file)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create storage path
        timestamp = datetime.now().strftime("%Y/%m/%d")
        storage_path = f"{folder}/{user_id}/{timestamp}/{unique_filename}"
        
        try:
            # Get Supabase client
            supabase = cls.get_client()
            
            # Reset file pointer to beginning
            file.file.seek(0)
            file_data = file.file.read()
            
            # Upload file to Supabase Storage
            response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=storage_path,
                file=file_data,
                file_options={
                    "content-type": file.content_type,
                    "x-upsert": "false"  # Don't overwrite existing files
                }
            )
            
            # The Supabase Python client's upload method returns different response types
            # We'll check for common error patterns instead of status_code
            if hasattr(response, 'error') and response.error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file: {response.error}"
                )
            
            # Check if response indicates an error (different response patterns)
            if isinstance(response, dict) and 'error' in response:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file: {response['error']}"
                )
            
            # Get public URL
            public_url_response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
            download_url = public_url_response
            
            # Add storage info to metadata
            metadata.update({
                "storage_path": storage_path,
                "download_url": download_url,
                "file_size": len(file_data),
                "uploaded_at": datetime.now().isoformat(),
                "uploaded_by": str(user_id),
                "original_filename": file.filename,
                "content_type": file.content_type,
                "bucket": settings.SUPABASE_BUCKET_NAME
            })
            
            return download_url, metadata
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image: {str(e)}"
            )
    
    @classmethod
    def delete_image(cls, storage_path: str) -> bool:
        """
        Delete image from Supabase Storage.
        
        Args:
            storage_path: Path to the file in storage
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            supabase = cls.get_client()
            response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([storage_path])
            
            # Check for errors instead of status_code
            if hasattr(response, 'error') and response.error:
                return False
            if isinstance(response, dict) and 'error' in response:
                return False
            
            return True
        except Exception:
            return False
    
    @classmethod
    def get_image_info(cls, storage_path: str) -> Optional[dict]:
        """
        Get information about an image in storage.
        
        Args:
            storage_path: Path to the file in storage
            
        Returns:
            Dictionary with image info or None if not found
        """
        try:
            supabase = cls.get_client()
            
            # List files to get file info (Supabase doesn't have a direct "get info" method)
            response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).list(
                path="/".join(storage_path.split("/")[:-1])  # Get parent directory
            )
            
            # Check for errors instead of status_code
            if hasattr(response, 'error') and response.error:
                return None
            if isinstance(response, dict) and 'error' in response:
                return None
            
            # Handle different response formats
            files = response if isinstance(response, list) else (response.get('data', []) if isinstance(response, dict) else [])
            filename = storage_path.split("/")[-1]
            
            for file_info in files:
                if file_info.get("name") == filename:
                    public_url = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
                    
                    return {
                        "name": file_info.get("name"),
                        "size": file_info.get("metadata", {}).get("size"),
                        "content_type": file_info.get("metadata", {}).get("mimetype"),
                        "created": file_info.get("created_at"),
                        "updated": file_info.get("updated_at"),
                        "public_url": public_url,
                        "storage_path": storage_path
                    }
            
            return None
        except Exception:
            return None
    
    @classmethod
    def create_bucket_if_not_exists(cls) -> bool:
        """
        Create the storage bucket if it doesn't exist.
        
        Returns:
            True if bucket exists or was created successfully
        """
        try:
            supabase = cls.get_client()
            
            # Try to list files in the bucket (this will fail if bucket doesn't exist)
            try:
                response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).list()
                # Check for errors
                if hasattr(response, 'error') and response.error:
                    raise Exception("Bucket doesn't exist")
                if isinstance(response, dict) and 'error' in response:
                    raise Exception("Bucket doesn't exist")
                return True  # Bucket exists
            except Exception:
                # Bucket doesn't exist, try to create it
                response = supabase.storage.create_bucket(
                    settings.SUPABASE_BUCKET_NAME,
                    options={
                        "public": True,  # Make bucket public for easier access
                        "file_size_limit": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
                        "allowed_mime_types": settings.ALLOWED_IMAGE_TYPES
                    }
                )
                
                # Check for errors in bucket creation
                if hasattr(response, 'error') and response.error:
                    return False
                if isinstance(response, dict) and 'error' in response:
                    return False
                
                return True
        except Exception:
            return False 