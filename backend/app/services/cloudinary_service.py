"""
Cloudinary service for file upload and management
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, Dict, Any
import tempfile
import os
from fastapi import UploadFile

from app.core.config import settings


class CloudinaryService:
    """Service for handling file uploads to Cloudinary"""
    
    def __init__(self):
        self.initialized = False
    
    async def initialize(self):
        """Initialize Cloudinary configuration"""
        try:
            if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
                print("⚠️ Cloudinary credentials not configured - file upload will be disabled")
                return
            
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True
            )
            
            self.initialized = True
            print("✅ Cloudinary service initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize Cloudinary service: {e}")
            self.initialized = False
    
    async def upload_resume(self, file: UploadFile, user_id: str) -> Optional[str]:
        """
        Upload resume file to Cloudinary
        
        Args:
            file: The uploaded file
            user_id: ID of the user uploading the file
            
        Returns:
            Cloudinary URL of the uploaded file, or None if upload failed
        """
        if not self.initialized:
            raise Exception("Cloudinary service not initialized")
        
        try:
            # Create a temporary file to store the upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                # Read file content
                await file.seek(0)
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()
                
                # Upload to Cloudinary
                result = cloudinary.uploader.upload(
                    temp_file.name,
                    folder=f"resumes/{user_id}",
                    resource_type="raw",  # For non-image files like PDFs
                    public_id=f"{user_id}_{file.filename}",
                    overwrite=True,
                    use_filename=True,
                    unique_filename=False
                )
                
                # Clean up temporary file
                os.unlink(temp_file.name)
                
                return result.get('secure_url')
                
        except Exception as e:
            print(f"❌ Failed to upload file to Cloudinary: {e}")
            # Clean up temp file if it exists
            try:
                if 'temp_file' in locals():
                    os.unlink(temp_file.name)
            except:
                pass
            raise Exception(f"Failed to upload file: {str(e)}")
    
    async def delete_resume(self, file_url: str) -> bool:
        """
        Delete resume file from Cloudinary
        
        Args:
            file_url: Cloudinary URL of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.initialized:
            return False
        
        try:
            # Extract public_id from URL
            # Cloudinary URLs have format: https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/{public_id}
            url_parts = file_url.split('/')
            if 'upload' in url_parts:
                upload_index = url_parts.index('upload')
                public_id = '/'.join(url_parts[upload_index + 1:])
                # Remove file extension
                public_id = public_id.rsplit('.', 1)[0]
                
                result = cloudinary.uploader.destroy(public_id, resource_type="raw")
                return result.get('result') == 'ok'
            
            return False
            
        except Exception as e:
            print(f"❌ Failed to delete file from Cloudinary: {e}")
            return False
    
    async def get_file_info(self, file_url: str) -> Optional[Dict[str, Any]]:
        """
        Get file information from Cloudinary
        
        Args:
            file_url: Cloudinary URL of the file
            
        Returns:
            File information dictionary or None if not found
        """
        if not self.initialized:
            return None
        
        try:
            # Extract public_id from URL
            url_parts = file_url.split('/')
            if 'upload' in url_parts:
                upload_index = url_parts.index('upload')
                public_id = '/'.join(url_parts[upload_index + 1:])
                # Remove file extension
                public_id = public_id.rsplit('.', 1)[0]
                
                result = cloudinary.api.resource(public_id, resource_type="raw")
                return result
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to get file info from Cloudinary: {e}")
            return None


# Global instance
cloudinary_service = CloudinaryService()
