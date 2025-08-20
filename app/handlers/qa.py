import time
from typing import List, Dict, Any
from app.config import settings
from app.db.repo import repo
from app.llm.client import llm_client
from app.retrieval.retrieve import retrieval_engine
from app.utils.text import safe_truncate


class QAHandler:
    def __init__(self):
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file"""
        try:
            with open("app/prompts/system.txt", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "You answer questions about the OnlyAi course and AI-OFM strategies. Be concise and direct."
    
    async def process_question(self, user_id: int, question: str, chat_id: int = None) -> Dict[str, Any]:
        """Process a question and generate an answer"""
        start_time = time.time()
        
        # Get recent chat context if available
        chat_context = []
        if chat_id:
            recent_messages = await repo.get_recent_messages(chat_id, settings.context_messages)
            chat_context = [msg['text'] for msg in recent_messages if msg['sender_id'] == user_id]
        
        # Get retrieval context
        retrieval_result = await retrieval_engine.get_context_for_question(question, chat_context)
        
        # Generate answer
        if retrieval_result['context_chunks']:
            answer = await self._generate_answer_with_context(question, retrieval_result['context_chunks'])
        else:
            answer = await retrieval_engine.get_fallback_response(question)
            retrieval_result['sources'] = []
        
        # Format answer with sources
        formatted_answer = await retrieval_engine.format_answer_with_sources(answer, retrieval_result['sources'])
        
        # Ensure answer is within length limit
        final_answer = safe_truncate(formatted_answer, settings.max_answer_length)
        
        # Calculate total latency
        total_latency = int((time.time() - start_time) * 1000)
        
        # Log the Q&A interaction
        await repo.log_qa(
            user_id=user_id,
            question=question,
            answer=final_answer,
            sources=retrieval_result['sources'],
            latency_ms=total_latency
        )
        
        return {
            'answer': final_answer,
            'sources': retrieval_result['sources'],
            'latency_ms': total_latency,
            'context_chunks_used': len(retrieval_result['context_chunks'])
        }
    
    async def _generate_answer_with_context(self, question: str, context_chunks: List[str]) -> str:
        """Generate answer using context chunks"""
        # Combine context chunks
        context_text = "\n\n".join([f"Context {i+1}: {chunk}" for i, chunk in enumerate(context_chunks)])
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}
        ]
        
        answer = await llm_client.chat_completion(
            messages=messages,
            max_tokens=settings.max_answer_length,
            temperature=0.7
        )
        
        return answer.strip()
    
    async def handle_greeting(self, user_id: int) -> str:
        """Handle greeting messages"""
        return "How can I help?"
    
    async def handle_test_command(self, user_id: int) -> str:
        """Handle /test command"""
        try:
            # Test database connection
            user = await repo.get_user(user_id)
            
            # Test OpenAI connection
            test_embedding = await llm_client.embed_text("test")
            
            return "✅ All systems operational - Database and OpenAI connections working."
        except Exception as e:
            return f"❌ System check failed: {str(e)}"
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        # Get user info
        user = await repo.get_user(user_id)
        
        # Get Q&A history
        # Note: This would require adding a method to repo to get user's QA history
        # For now, return basic user info
        return {
            'user_id': user_id,
            'role': user['role'] if user else 'none',
            'whitelisted': await repo.is_whitelisted(user_id) if user else False
        }


# Global QA handler instance
qa_handler = QAHandler()
