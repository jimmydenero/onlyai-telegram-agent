import asyncio
from typing import List, Dict, Any
from uuid import UUID

from app.llm.client import llm_client
from app.db.repo import repo


class EmbeddingManager:
    def __init__(self):
        self.batch_size = 10  # Process embeddings in batches
    
    async def embed_chunks(self, chunks: List[Dict[str, Any]], doc_id: UUID) -> List[Dict[str, Any]]:
        """Embed a list of text chunks and store them"""
        if not chunks:
            return []
        
        # Extract texts for embedding
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings in batches
        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_embeddings = await llm_client.embed_batch(batch_texts)
            embeddings.extend(batch_embeddings)
        
        # Store chunks with embeddings
        stored_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            stored_chunk = await repo.store_chunk(
                doc_id=doc_id,
                section=chunk.get('section', ''),
                text=chunk['text'],
                tokens=chunk['tokens'],
                embedding=embedding,
                meta={
                    'title': chunk.get('title', ''),
                    'section': chunk.get('section', ''),
                    'chunk_index': len(stored_chunks)
                }
            )
            stored_chunks.append(stored_chunk)
        
        return stored_chunks
    
    async def embed_digest(self, text: str, date: str, meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """Embed a digest text and store it"""
        embedding = await llm_client.embed_text(text)
        
        digest_meta = {
            'date': date,
            'type': 'digest',
            **(meta or {})
        }
        
        stored_digest = await repo.store_digest(
            date=date,
            text=text,
            embedding=embedding,
            meta=digest_meta
        )
        
        return stored_digest
    
    async def embed_query(self, query: str) -> List[float]:
        """Embed a query for search"""
        return await llm_client.embed_text(query)
    
    async def reindex_document(self, doc_id: UUID, chunks: List[Dict[str, Any]]) -> int:
        """Reindex a document by deleting old chunks and creating new ones"""
        # Delete existing chunks
        deleted_count = await repo.delete_document_chunks(doc_id)
        
        # Create new chunks with embeddings
        new_chunks = await self.embed_chunks(chunks, doc_id)
        
        return len(new_chunks)
    
    async def batch_embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in batches"""
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_embeddings = await llm_client.embed_batch(batch_texts)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings


# Global embedding manager instance
embedding_manager = EmbeddingManager()
