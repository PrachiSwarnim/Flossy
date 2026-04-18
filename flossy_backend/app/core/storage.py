import os
from google.cloud import storage
from app.core import config

def upload_file(file, filename: str) -> str:
    """
    Uploads a file to Google Cloud Storage if STORAGE_BUCKET is active.
    Otherwise, saves to the local UPLOAD_DIR.
    Returns the public URL or local filename.
    """
    # 🌍 CLOUD STORAGE PATH
    bucket_name = config.STORAGE_BUCKET
    if bucket_name and not bucket_name.startswith("TEMP_"):
        try:
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(filename)
            
            # Reset file pointer if it's an UploadFile objects
            if hasattr(file, 'seek'):
                file.seek(0)
            
            blob.upload_from_file(file.file if hasattr(file, 'file') else file)
            print(f"✅ Uploaded {filename} to GCS bucket: {bucket_name}")
            return f"https://storage.googleapis.com/{bucket_name}/{filename}"
        except Exception as e:
            print(f"❌ GCS Upload failed: {e}. Falling back to local.")

    # 🏠 LOCAL FALLBACK
    if not os.path.exists(config.UPLOAD_DIR):
        os.makedirs(config.UPLOAD_DIR)
    
    file_path = os.path.join(config.UPLOAD_DIR, filename)
    
    # Handle FastAPI UploadFile
    if hasattr(file, 'file'):
        file.seek(0)
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
    else:
        # Handle raw bytes or other file-likes
        with open(file_path, "wb") as buffer:
            buffer.write(file.read() if hasattr(file, 'read') else file)
            
    return filename
