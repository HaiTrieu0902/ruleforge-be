from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import List
import os
import uuid
from datetime import datetime

from app.core.config import settings
from app.services.document_processor import DocumentProcessor
from app.services.summarizer import ContractSummarizer
from app.services.rule_generator import RuleGenerator
from app.services.minio_storage import minio_storage
from app.services.qdrant_service import qdrant_service
from app.models.database import get_db, Document, Summary, Rule
from app.utils.file_validator import validate_file

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "contract",  # contract or policy
    db = Depends(get_db)
):
    """Upload and process a document (contract or policy) using MinIO storage."""
    try:
        # Validate file
        validation_result = await validate_file(file)
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["error"]
            )
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1].lower()
        
        # Read file content
        content = await file.read()
        file.file.seek(0)  # Reset file pointer for MinIO upload
        
        # Upload to MinIO
        upload_result = await minio_storage.upload_file(
            file_content=file.file,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream"
        )
        
        if not upload_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to storage: {upload_result['error']}"
            )
        
        # Extract text from document for processing
        # Create temporary file for text extraction
        temp_filename = f"temp_{file_id}.{file_extension}"
        temp_path = os.path.join(settings.upload_folder, temp_filename)
        
        # Ensure upload folder exists for temp files
        os.makedirs(settings.upload_folder, exist_ok=True)
        
        try:
            with open(temp_path, "wb") as f:
                f.write(content)
            
            # Extract text from document
            doc_processor = DocumentProcessor()
            extracted_text = await doc_processor.extract_text(temp_path, file_extension)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Save document record to database with MinIO object name
        document = Document(
            id=file_id,
            filename=file.filename,
            file_path=upload_result["object_name"],  # Store MinIO object name instead of local path
            document_type=document_type,
            content=extracted_text,
            file_size=upload_result["file_size"],
            created_at=datetime.utcnow()
        )
        db.add(document)
        db.commit()
        
        # Add document to Qdrant for semantic search
        await qdrant_service.add_document(
            document_id=file_id,
            text=extracted_text,
            metadata={
                "filename": file.filename,
                "document_type": document_type,
                "file_size": upload_result["file_size"],
                "type": "document"
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Document uploaded successfully to MinIO storage",
                "document_id": file_id,
                "filename": file.filename,
                "document_type": document_type,
                "file_size": upload_result["file_size"],
                "text_length": len(extracted_text),
                "file_url": upload_result["file_url"],
                "storage_location": upload_result["object_name"]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )

@router.post("/test-groq")
async def test_groq_connection():
    """Test Groq API connection and configuration."""
    try:
        from app.core.config import settings
        
        # Check if API key is configured
        if not settings.groq_api_key or settings.groq_api_key == "":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Groq API key not configured",
                    "message": "Please set GROQ_API_KEY in your .env file"
                }
            )
        
        # Test with a simple summarization request
        summarizer = ContractSummarizer()
        test_text = "This is a simple test document. It contains basic information for testing the summarization functionality. The document should be processed and summarized correctly."
        
        try:
            summary = await summarizer.summarize(test_text, max_length=50)
            
            if summary and len(summary.strip()) > 0:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "message": "Groq API connection successful",
                        "model": settings.groq_model,
                        "test_summary": summary,
                        "api_key_configured": True
                    }
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "Groq API returned empty summary",
                        "message": "API connection works but summarization failed"
                    }
                )
                
        finally:
            summarizer.close()
            
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": f"Groq API test failed: {str(e)}",
                "message": "Check your API key and network connection"
            }
        )

@router.post("/summarize/{document_id}")
async def summarize_document(
    document_id: str,
    db = Depends(get_db)
):
    """Generate summary for an uploaded document."""
    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if document has content
        if not document.content or len(document.content.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document content is empty or too short to summarize"
            )
        
        # Generate summary
        summarizer = ContractSummarizer()
        try:
            summary_text = await summarizer.summarize(document.content)
            
            # Validate that we got a proper summary
            if not summary_text or len(summary_text.strip()) < 10:
                raise Exception("Summary generation returned empty or invalid content")
            
            print(f"✅ Summary generated successfully: {len(summary_text)} characters")
            
        except Exception as summary_error:
            print(f"❌ Summarization failed: {str(summary_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate summary: {str(summary_error)}"
            )
        finally:
            # Clean up summarizer resources
            summarizer.close()
        
        # Save summary to database only if we have valid content
        summary = Summary(
            id=str(uuid.uuid4()),
            document_id=document_id,
            summary_text=summary_text,
            model_used="groq/openai-gpt-oss-20b",
            created_at=datetime.utcnow()
        )
        db.add(summary)
        db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Summary generated successfully",
                "summary_id": summary.id,
                "summary": summary_text,
                "model_used": summary.model_used,
                "summary_length": len(summary_text),
                "document_length": len(document.content)
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        print(f"❌ Unexpected error in summarize_document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )

@router.post("/generate-rules/{document_id}")
async def generate_rules(
    document_id: str,
    db = Depends(get_db)
):
    """Generate business rules from a document using Groq AI."""
    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Generate rules
        rule_generator = RuleGenerator()
        try:
            rules_data = await rule_generator.generate_rules(
                document.content, 
                document.document_type
            )
            
            # Save rules to database
            rule_record = Rule(
                id=str(uuid.uuid4()),
                document_id=document_id,
                rules_json=rules_data,
                ai_provider="groq",  # Now using Groq
                created_at=datetime.utcnow()
            )
            db.add(rule_record)
            db.commit()
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Rules generated successfully",
                    "rule_id": rule_record.id,
                    "rules": rules_data,
                    "ai_provider": "groq"
                }
            )
        finally:
            # Clean up resources
            rule_generator.close()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating rules: {str(e)}"
        )

@router.get("/documents")
async def list_documents(db = Depends(get_db)):
    """List all uploaded documents."""
    documents = db.query(Document).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "file_size": doc.file_size,
            "created_at": doc.created_at.isoformat()
        }
        for doc in documents
    ]

@router.get("/documents/{document_id}/download")
async def download_document(document_id: str, db = Depends(get_db)):
    """Download the original document file from MinIO."""
    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Generate download URL from MinIO
        file_url = await minio_storage.get_file_url(document.file_path, expires_in_days=1)
        
        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate download URL"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "download_url": file_url,
                "filename": document.filename,
                "expires_in": "24 hours"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating download link: {str(e)}"
        )

@router.get("/documents/{document_id}")
async def get_document(document_id: str, db = Depends(get_db)):
    """Get document details with summaries and rules."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get summaries and rules for this document
    summaries = db.query(Summary).filter(Summary.document_id == document_id).all()
    rules = db.query(Rule).filter(Rule.document_id == document_id).all()
    
    return {
        "document": {
            "id": document.id,
            "filename": document.filename,
            "document_type": document.document_type,
            "file_size": document.file_size,
            "created_at": document.created_at.isoformat(),
            "content_preview": document.content[:500] + "..." if len(document.content) > 500 else document.content
        },
        "summaries": [
            {
                "id": s.id,
                "summary": s.summary_text,
                "model_used": s.model_used,
                "created_at": s.created_at.isoformat()
            }
            for s in summaries
        ],
        "rules": [
            {
                "id": r.id,
                "rules": r.rules_json,
                "ai_provider": r.ai_provider,
                "created_at": r.created_at.isoformat()
            }
            for r in rules
        ]
    }