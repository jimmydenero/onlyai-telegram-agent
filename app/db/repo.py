import asyncio
import json
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
import numpy as np

from app.config import settings


class DatabaseRepo:
    def __init__(self):
        self.connection_string = settings.database_url
    
    async def get_connection(self):
        return await psycopg.AsyncConnection.connect(
            self.connection_string,
            row_factory=dict_row
        )
    
    # User management
    async def get_user(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM users WHERE telegram_user_id = %s",
                    (telegram_user_id,)
                )
                return await cur.fetchone()
    
    async def create_user(self, telegram_user_id: int, role: str = 'none') -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO users (telegram_user_id, role) VALUES (%s, %s) RETURNING *",
                    (telegram_user_id, role)
                )
                return await cur.fetchone()
    
    async def update_user_role(self, telegram_user_id: int, role: str) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET role = %s WHERE telegram_user_id = %s RETURNING *",
                    (role, telegram_user_id)
                )
                return await cur.fetchone()
    
    # Whitelist management
    async def is_whitelisted(self, telegram_user_id: int) -> bool:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM whitelist WHERE telegram_user_id = %s",
                    (telegram_user_id,)
                )
                return await cur.fetchone() is not None
    
    async def add_to_whitelist(self, telegram_user_id: int, note: str = None) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO whitelist (telegram_user_id, note) VALUES (%s, %s) RETURNING *",
                    (telegram_user_id, note)
                )
                return await cur.fetchone()
    
    async def remove_from_whitelist(self, telegram_user_id: int) -> bool:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM whitelist WHERE telegram_user_id = %s",
                    (telegram_user_id,)
                )
                return cur.rowcount > 0
    
    async def get_whitelist(self) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM whitelist ORDER BY created_at DESC")
                return await cur.fetchall()
    
    # Message storage
    async def store_message(self, chat_id: int, sender_id: int, text: str, kept: bool = False) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO messages (chat_id, sender_id, text, kept) VALUES (%s, %s, %s, %s) RETURNING *",
                    (chat_id, sender_id, text, kept)
                )
                return await cur.fetchone()
    
    async def get_recent_messages(self, chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM messages WHERE chat_id = %s ORDER BY created_at DESC LIMIT %s",
                    (chat_id, limit)
                )
                return await cur.fetchall()
    
    async def get_kept_messages_for_digest(self, date: date) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM messages WHERE kept = TRUE AND DATE(created_at) = %s ORDER BY created_at",
                    (date,)
                )
                return await cur.fetchall()
    
    # Document management
    async def create_document(self, title: str, source: str) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO docs (title, source) VALUES (%s, %s) RETURNING *",
                    (title, source)
                )
                return await cur.fetchone()
    
    async def get_document_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM docs WHERE title = %s AND is_active = TRUE ORDER BY version DESC LIMIT 1",
                    (title,)
                )
                return await cur.fetchone()
    
    async def update_document_version(self, title: str) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                # Get current version
                await cur.execute(
                    "SELECT version FROM docs WHERE title = %s AND is_active = TRUE ORDER BY version DESC LIMIT 1",
                    (title,)
                )
                current = await cur.fetchone()
                if current:
                    new_version = current['version'] + 1
                    await cur.execute(
                        "INSERT INTO docs (title, version, source) VALUES (%s, %s, %s) RETURNING *",
                        (title, new_version, f"{title}_v{new_version}")
                    )
                    return await cur.fetchone()
                return None
    
    async def deactivate_old_versions(self, title: str) -> int:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE docs SET is_active = FALSE WHERE title = %s AND version < (SELECT MAX(version) FROM docs WHERE title = %s)",
                    (title, title)
                )
                return cur.rowcount
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM docs WHERE is_active = TRUE ORDER BY updated_at DESC"
                )
                return await cur.fetchall()
    
    # Document chunks
    async def store_chunk(self, doc_id: UUID, section: str, text: str, tokens: int, 
                         embedding: List[float], meta: Dict[str, Any] = None) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO doc_chunks (doc_id, section, text, tokens, embedding, meta) 
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
                    (doc_id, section, text, tokens, embedding, json.dumps(meta or {}))
                )
                return await cur.fetchone()
    
    async def delete_document_chunks(self, doc_id: UUID) -> int:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM doc_chunks WHERE doc_id = %s",
                    (doc_id,)
                )
                return cur.rowcount
    
    # Chat digests
    async def store_digest(self, date: date, text: str, embedding: List[float], 
                          meta: Dict[str, Any] = None) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO chat_digests (date, text, embedding, meta) 
                       VALUES (%s, %s, %s, %s) RETURNING *""",
                    (date, text, embedding, json.dumps(meta or {}))
                )
                return await cur.fetchone()
    
    # Hybrid search (BM25 + Vector)
    async def hybrid_search(self, query: str, query_embedding: List[float], 
                           top_k: int = 8) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                # BM25 search
                await cur.execute(
                    """SELECT id, text, 'doc_chunk' as type, 
                       ts_rank(to_tsvector('english', text), plainto_tsquery('english', %s)) as bm25_score,
                       NULL as vector_score, meta
                       FROM doc_chunks 
                       WHERE to_tsvector('english', text) @@ plainto_tsquery('english', %s)
                       ORDER BY bm25_score DESC LIMIT %s""",
                    (query, query, top_k)
                )
                bm25_results = await cur.fetchall()
                
                # Vector search
                await cur.execute(
                    """SELECT id, text, 'doc_chunk' as type, 
                       NULL as bm25_score,
                       1 - (embedding <=> %s) as vector_score, meta
                       FROM doc_chunks 
                       WHERE embedding IS NOT NULL
                       ORDER BY embedding <=> %s LIMIT %s""",
                    (query_embedding, query_embedding, top_k)
                )
                vector_results = await cur.fetchall()
                
                # Also search in digests
                await cur.execute(
                    """SELECT id, text, 'digest' as type, 
                       NULL as bm25_score,
                       1 - (embedding <=> %s) as vector_score, meta
                       FROM chat_digests 
                       WHERE embedding IS NOT NULL
                       ORDER BY embedding <=> %s LIMIT %s""",
                    (query_embedding, query_embedding, top_k // 2)
                )
                digest_results = await cur.fetchall()
                
                # Combine and rerank
                all_results = bm25_results + vector_results + digest_results
                
                # Simple reranking: combine scores
                for result in all_results:
                    bm25_score = result['bm25_score'] or 0
                    vector_score = result['vector_score'] or 0
                    result['combined_score'] = (bm25_score * 0.3) + (vector_score * 0.7)
                
                # Sort by combined score and return top_k
                all_results.sort(key=lambda x: x['combined_score'], reverse=True)
                return all_results[:top_k]
    
    # Q&A logging
    async def log_qa(self, user_id: int, question: str, answer: str, 
                    sources: List[str], latency_ms: int) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO qa_logs (user_id, question, answer, sources, latency_ms) 
                       VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                    (user_id, question, answer, json.dumps(sources), latency_ms)
                )
                return await cur.fetchone()
    
    # Cleanup old messages
    async def cleanup_old_messages(self, days: int = 14) -> int:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cur:
                cutoff_date = datetime.now() - timedelta(days=days)
                await cur.execute(
                    "DELETE FROM messages WHERE created_at < %s AND kept = FALSE",
                    (cutoff_date,)
                )
                return cur.rowcount


# Global repository instance
repo = DatabaseRepo()
