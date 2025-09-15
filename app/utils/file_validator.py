from fastapi import UploadFile
import magic
from app.core.config import settings

async def validate_file(file: UploadFile) -> dict:
    """Validate uploaded file for security and format compliance."""
    
    # Check file size
    content = await file.read()
    await file.seek(0)  # Reset file pointer
    
    if len(content) > settings.max_file_size:
        return {
            "valid": False,
            "error": f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
        }
    
    # Check file extension
    if not file.filename:
        return {
            "valid": False,
            "error": "No filename provided"
        }
    
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in settings.allowed_extensions:
        return {
            "valid": False,
            "error": f"File type '{file_extension}' not allowed. Allowed types: {', '.join(settings.allowed_extensions)}"
        }
    
    # Basic MIME type validation (if python-magic is available)
    try:
        mime_type = magic.from_buffer(content, mime=True)
        
        # Define expected MIME types for each extension
        expected_mime_types = {
            'pdf': ['application/pdf'],
            'docx': [
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/octet-stream'  # Sometimes DOCX files are detected as this
            ],
            'txt': ['text/plain', 'text/x-python', 'application/octet-stream']
        }
        
        if file_extension in expected_mime_types:
            if mime_type not in expected_mime_types[file_extension]:
                return {
                    "valid": False,
                    "error": f"File content doesn't match extension. Expected {expected_mime_types[file_extension]}, got {mime_type}"
                }
    
    except ImportError:
        # python-magic not available, skip MIME type validation
        pass
    except Exception as e:
        # If MIME type detection fails, continue with basic validation
        print(f"MIME type detection failed: {str(e)}")
    
    # Check for empty files
    if len(content) == 0:
        return {
            "valid": False,
            "error": "File is empty"
        }
    
    return {
        "valid": True,
        "error": None
    }

def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in settings.allowed_extensions