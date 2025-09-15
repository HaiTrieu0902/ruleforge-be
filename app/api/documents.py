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
from app.models.database import get_db, Document, Summary, Rule
from app.utils.file_validator import validate_file

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "contract",  # contract or policy
    db = Depends(get_db)
):
    """Upload and process a document (contract or policy)."""
    try:
        # Validate file
        validation_result = await validate_file(file)
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["error"]
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1].lower()
        filename = f"{file_id}.{file_extension}"
        file_path = os.path.join(settings.upload_folder, filename)
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Extract text from document
        doc_processor = DocumentProcessor()
        extracted_text = await doc_processor.extract_text(file_path, file_extension)
        
        # Save document record to database
        document = Document(
            id=file_id,
            filename=file.filename,
            file_path=file_path,
            document_type=document_type,
            content=extracted_text,
            file_size=len(content),
            created_at=datetime.utcnow()
        )
        db.add(document)
        db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Document uploaded successfully",
                "document_id": file_id,
                "filename": file.filename,
                "document_type": document_type,
                "file_size": len(content),
                "text_length": len(extracted_text)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
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
        
        # Generate summary
        summarizer = ContractSummarizer()
        summary_text = await summarizer.summarize(document.content)
        
        # Save summary to database
        summary = Summary(
            id=str(uuid.uuid4()),
            document_id=document_id,
            summary_text=summary_text,
            model_used="huggingface/bart-large-cnn",
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
                "model_used": summary.model_used
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )

@router.post("/generate-rules/{document_id}")
async def generate_rules(
    document_id: str,
    ai_provider: str = "openai",  # openai or google
    db = Depends(get_db)
):
    """Generate business rules from a document."""
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
        rules_data = await rule_generator.generate_rules(
            document.content, 
            document.document_type,
            ai_provider
        )
        
        # Save rules to database
        rule_record = Rule(
            id=str(uuid.uuid4()),
            document_id=document_id,
            rules_json=rules_data,
            ai_provider=ai_provider,
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
                "ai_provider": ai_provider
            }
        )
        
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