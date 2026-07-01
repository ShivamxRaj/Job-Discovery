import os
import shutil
from typing import BinaryIO
from fastapi import UploadFile
from app.core.config import settings

class StorageManager:
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.bucket_name = settings.SUPABASE_BUCKET_NAME
        self.local_dir = os.path.join(os.getcwd(), "storage")
        
        # Ensure local storage path exists
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)

    async def upload_file(self, file: UploadFile, unique_filename: str) -> str:
        """Upload file and return its URL/Path"""
        is_production = settings.ENVIRONMENT.lower() in ("production", "staging")
        
        if self.supabase_url and self.supabase_key:
            try:
                # Integrate with Supabase Storage client
                from supabase import create_client, Client
                supabase: Client = create_client(self.supabase_url, self.supabase_key)
                
                # Ensure bucket exists
                try:
                    supabase.storage.get_bucket(self.bucket_name)
                except Exception:
                    try:
                        supabase.storage.create_bucket(self.bucket_name, options={"public": True})
                    except Exception as ce:
                        print(f"Failed to create bucket {self.bucket_name}: {ce}")
                
                # Read file content
                content = await file.read()
                await file.seek(0)
                
                # Upload to supabase bucket
                res = supabase.storage.from_(self.bucket_name).upload(
                    path=unique_filename,
                    file=content,
                    file_options={"content-type": file.content_type}
                )
                
                # Get public URL
                public_url = supabase.storage.from_(self.bucket_name).get_public_url(unique_filename)
                return public_url
            except Exception as e:
                if is_production:
                    raise RuntimeError(f"Supabase upload failed: {str(e)}")
                print(f"Supabase upload failed, falling back to local storage: {e}")
        else:
            if is_production:
                raise RuntimeError("Supabase credentials missing in production mode")
                
        # Local storage fallback (development/staging local testing mode only)
        local_path = os.path.join(self.local_dir, unique_filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return f"/static/{unique_filename}"

storage_manager = StorageManager()
