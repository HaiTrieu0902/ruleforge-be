import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_upload_document_invalid_file():
    """Test uploading an invalid file type."""
    # Create a temporary file with invalid extension
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp_file:
        tmp_file.write(b"test content")
        tmp_file_path = tmp_file.name
    
    try:
        with open(tmp_file_path, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("test.xyz", f, "application/octet-stream")},
                data={"document_type": "contract"}
            )
        assert response.status_code == 400
    finally:
        os.unlink(tmp_file_path)

def test_upload_document_empty_file():
    """Test uploading an empty file."""
    # Create a temporary empty file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
        tmp_file_path = tmp_file.name
    
    try:
        with open(tmp_file_path, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("empty.txt", f, "text/plain")},
                data={"document_type": "contract"}
            )
        assert response.status_code == 400
    finally:
        os.unlink(tmp_file_path)

def test_list_documents():
    """Test listing documents endpoint."""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_nonexistent_document():
    """Test getting a document that doesn't exist."""
    response = client.get("/api/v1/documents/nonexistent-id")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_document_processor():
    """Test the document processor service."""
    from app.services.document_processor import DocumentProcessor
    
    processor = DocumentProcessor()
    
    # Test TXT processing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("This is a test document.")
        tmp_file_path = tmp_file.name
    
    try:
        text = await processor.extract_text(tmp_file_path, "txt")
        assert text == "This is a test document."
    finally:
        os.unlink(tmp_file_path)

@pytest.mark.asyncio
async def test_file_validator():
    """Test the file validator utility."""
    from app.utils.file_validator import is_allowed_file
    
    assert is_allowed_file("test.pdf") == True
    assert is_allowed_file("test.docx") == True
    assert is_allowed_file("test.txt") == True
    assert is_allowed_file("test.exe") == False
    assert is_allowed_file("test") == False
    assert is_allowed_file("") == False