import hashlib
import os
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException

from ..config import settings

ALLOWED_MIME_TYPES = {"application/pdf", "application/x-pdf"}


async def validate_and_save_file(file: UploadFile, upload_dir: str) -> dict:
    """Validate an uploaded file and persist it to disk.

    Returns a dict with file_id, filename, original_filename, file_path,
    file_hash, file_bytes, and size_bytes.
    """
    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {suffix} not allowed. Only PDF files accepted.",
        )

    # Read and check size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size_mb:.1f}MB. Max {settings.MAX_FILE_SIZE_MB}MB.",
        )

    # Validate PDF magic bytes
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid PDF.",
        )

    # Compute hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Save with UUID filename
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{suffix}"
    file_path = os.path.join(upload_dir, safe_filename)

    os.makedirs(upload_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "file_id": file_id,
        "filename": safe_filename,
        "original_filename": file.filename,
        "file_path": file_path,
        "file_hash": file_hash,
        "file_bytes": content,
        "size_bytes": len(content),
    }
