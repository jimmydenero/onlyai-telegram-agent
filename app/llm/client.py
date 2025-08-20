import asyncio
import time
from typing import List, Dict, Any, Optional
import openai
from openai import AsyncOpenAI
import tiktoken

from app.config import settings


class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.embed_model = settings.embed_model
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Retry function with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
    
    async def chat_completion(self, messages: List[Dict[str, str]], 
                            max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate chat completion with retries"""
        async def _chat():
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30.0
            )
            return response.choices[0].message.content
        
        return await self._retry_with_backoff(_chat)
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text with retries"""
        async def _embed():
            response = await self.client.embeddings.create(
                model=self.embed_model,
                input=text,
                timeout=30.0
            )
            return response.data[0].embedding
        
        return await self._retry_with_backoff(_embed)
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        async def _embed_batch():
            response = await self.client.embeddings.create(
                model=self.embed_model,
                input=texts,
                timeout=60.0
            )
            return [data.embedding for data in response.data]
        
        return await self._retry_with_backoff(_embed_batch)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        try:
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except:
            # Fallback to approximate counting
            return len(text.split()) * 1.3
    
    async def generate_answer(self, question: str, context: List[str], 
                            system_prompt: str) -> str:
        """Generate answer using context and system prompt"""
        # Build context string
        context_text = "\n\n".join([f"Context {i+1}: {ctx}" for i, ctx in enumerate(context)])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}
        ]
        
        return await self.chat_completion(messages, max_tokens=settings.max_answer_length)
    
    async def generate_digest(self, messages: List[str], date: str) -> str:
        """Generate daily digest from messages"""
        messages_text = "\n".join([f"- {msg}" for msg in messages])
        
        system_prompt = """You are a helpful assistant that creates concise daily summaries. 
        Summarize the key points and topics discussed in the provided messages. 
        Focus on actionable insights and important information. Keep the summary under 300 words."""
        
        user_prompt = f"Create a daily digest for {date} based on these messages:\n\n{messages_text}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self.chat_completion(messages, max_tokens=500, temperature=0.3)


# Global client instance
llm_client = OpenAIClient()
