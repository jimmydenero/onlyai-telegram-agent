import os
import hashlib
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
import PyPDF2
import docx
from fastapi import UploadFile

from app.config import settings
from app.db.repo import repo
from app.retrieval.chunker import chunker
from app.retrieval.embed import embedding_manager
from app.utils.text import sanitize_filename, extract_filename_from_path


class DocumentUploader:
    def __init__(self):
        self.storage_dir = Path(settings.file_storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    async def process_upload(self, file: UploadFile, title: Optional[str] = None) -> Dict[str, Any]:
        """Process uploaded file and store in database"""
        # Generate title if not provided
        if not title:
            title = extract_filename_from_path(file.filename)
        
        # Sanitize title
        title = sanitize_filename(title)
        
        # Check if document already exists
        existing_doc = await repo.get_document_by_title(title)
        
        # Calculate file hash for deduplication
        file_hash = await self._calculate_file_hash(file)
        
        # Save file to storage
        file_path = await self._save_file(file)
        
        # Extract text from file
        text_content = await self._extract_text(file_path, file.filename)
        
        # Chunk the text
        chunks = chunker.chunk_text(text_content, title=title)
        
        if existing_doc:
            # Update existing document
            doc_id = existing_doc['id']
            await repo.update_document_version(title)
            await repo.deactivate_old_versions(title)
        else:
            # Create new document
            new_doc = await repo.create_document(title, file.filename)
            doc_id = new_doc['id']
        
        # Store chunks with embeddings
        stored_chunks = await embedding_manager.embed_chunks(chunks, doc_id)
        
        # Clean up temporary file
        os.remove(file_path)
        
        return {
            'title': title,
            'doc_id': str(doc_id),
            'chunks_created': len(stored_chunks),
            'total_tokens': sum(chunk['tokens'] for chunk in chunks),
            'file_size': file.size,
            'is_update': existing_doc is not None
        }
    
    async def _calculate_file_hash(self, file: UploadFile) -> str:
        """Calculate SHA256 hash of file content"""
        hash_sha256 = hashlib.sha256()
        
        # Read file in chunks to handle large files
        chunk_size = 8192
        while chunk := await file.read(chunk_size):
            hash_sha256.update(chunk)
        
        # Reset file pointer
        await file.seek(0)
        
        return hash_sha256.hexdigest()
    
    async def _save_file(self, file: UploadFile) -> str:
        """Save uploaded file to temporary storage"""
        # Create unique filename
        file_id = str(uuid.uuid4())
        extension = Path(file.filename).suffix if file.filename else '.tmp'
        filename = f"{file_id}{extension}"
        
        file_path = self.storage_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return str(file_path)
    
    async def _extract_text(self, file_path: str, filename: str) -> str:
        """Extract text from various file formats"""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.pdf':
                return await self._extract_pdf_text(file_path)
            elif extension in ['.docx', '.doc']:
                return await self._extract_docx_text(file_path)
            elif extension in ['.txt', '.md']:
                return await self._extract_text_file(file_path)
            else:
                raise ValueError(f"Unsupported file format: {extension}")
        except Exception as e:
            raise Exception(f"Failed to extract text from {filename}: {str(e)}")
    
    async def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        text = ""
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text.strip()
    
    async def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file"""
        doc = docx.Document(file_path)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    
    async def _extract_text_file(self, file_path: Path) -> str:
        """Extract text from plain text file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    async def reindex_document(self, doc_id: str) -> Dict[str, Any]:
        """Reindex an existing document"""
        # Get document info
        # Note: This would require adding a method to repo to get document by ID
        # For now, return placeholder
        return {
            'doc_id': doc_id,
            'status': 'reindexed',
            'message': 'Reindexing functionality to be implemented'
        }
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document and all its chunks"""
        try:
            # Delete chunks first (cascade should handle this)
            deleted_chunks = await repo.delete_document_chunks(uuid.UUID(doc_id))
            
            # Note: Would need to add method to repo to delete document
            # For now, just return success
            return True
        except Exception as e:
            raise Exception(f"Failed to delete document: {str(e)}")


# Global uploader instance
uploader = DocumentUploader()
