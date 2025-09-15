import PyPDF2
from docx import Document as DocxDocument
import os
from typing import str

class DocumentProcessor:
    """Service for extracting text from various document formats."""
    
    async def extract_text(self, file_path: str, file_extension: str) -> str:
        """Extract text from document based on file extension."""
        try:
            if file_extension.lower() == 'pdf':
                return await self._extract_from_pdf(file_path)
            elif file_extension.lower() == 'docx':
                return await self._extract_from_docx(file_path)
            elif file_extension.lower() == 'txt':
                return await self._extract_from_txt(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        except Exception as e:
            raise Exception(f"Failed to extract text from {file_extension} file: {str(e)}")
    
    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    async def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            doc = DocxDocument(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error reading DOCX: {str(e)}")
    
    async def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read().strip()
            except Exception as e:
                raise Exception(f"Error reading TXT file with encoding: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading TXT: {str(e)}")
    
    def get_document_info(self, file_path: str) -> dict:
        """Get basic information about the document."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_stats = os.stat(file_path)
        return {
            "file_size": file_stats.st_size,
            "file_extension": os.path.splitext(file_path)[1].lower(),
            "file_name": os.path.basename(file_path)
        }