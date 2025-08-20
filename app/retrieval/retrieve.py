import time
from typing import List, Dict, Any, Optional
from app.config import settings
from app.db.repo import repo
from app.retrieval.embed import embedding_manager
from app.utils.text import format_citations


class RetrievalEngine:
    def __init__(self):
        self.top_k = settings.retrieval_top_k
    
    async def retrieve(self, query: str, include_digests: bool = True) -> Dict[str, Any]:
        """Main retrieval function combining hybrid search and reranking"""
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = await embedding_manager.embed_query(query)
        
        # Perform hybrid search
        search_results = await repo.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            top_k=self.top_k
        )
        
        # Extract context and sources
        context_chunks = []
        sources = []
        
        for result in search_results:
            context_chunks.append(result['text'])
            
            # Extract source information
            source_info = self._extract_source_info(result)
            sources.append(source_info)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            'context_chunks': context_chunks,
            'sources': sources,
            'latency_ms': latency_ms,
            'total_results': len(search_results)
        }
    
    def _extract_source_info(self, result: Dict[str, Any]) -> str:
        """Extract source information from search result"""
        result_type = result.get('type', 'unknown')
        
        if result_type == 'digest':
            meta = result.get('meta', {})
            date = meta.get('date', 'unknown')
            return f"Digest-{date}"
        
        elif result_type == 'doc_chunk':
            meta = result.get('meta', {})
            title = meta.get('title', 'Unknown Doc')
            section = meta.get('section', '')
            
            if section:
                return f"{title}-{section}"
            else:
                return title
        
        return "Unknown"
    
    async def get_context_for_question(self, question: str, chat_context: List[str] = None) -> Dict[str, Any]:
        """Get retrieval context for a question, optionally including chat context"""
        # Combine question with recent chat context if available
        if chat_context:
            # Use last few messages as additional context
            recent_context = " ".join(chat_context[-3:])  # Last 3 messages
            enhanced_query = f"{question} Context: {recent_context}"
        else:
            enhanced_query = question
        
        # Perform retrieval
        retrieval_result = await self.retrieve(enhanced_query)
        
        return retrieval_result
    
    async def format_answer_with_sources(self, answer: str, sources: List[str]) -> str:
        """Format answer with source citations"""
        if not sources:
            return answer
        
        # Format sources
        source_citations = format_citations(sources)
        
        # Combine answer and sources
        formatted_answer = f"{answer}\n\n{source_citations}"
        
        return formatted_answer
    
    async def get_fallback_response(self, question: str) -> str:
        """Generate fallback response when no relevant context is found"""
        fallback_responses = [
            "I don't have specific information about that in my knowledge base. Could you provide more context or ask about a different aspect of the OnlyAi course?",
            "That's not covered in my current knowledge base. Consider uploading relevant documentation or asking about AI-OFM strategies, prompt engineering, or course content.",
            "I don't have that information yet. Try asking about course materials, AI strategies, or workflow optimization techniques that I do have documented.",
            "That's outside my current knowledge scope. I can help with OnlyAi course content, AI implementation strategies, and automation workflows if you'd like to ask about those topics."
        ]
        
        # Simple hash-based selection for consistent responses
        import hashlib
        hash_value = int(hashlib.md5(question.encode()).hexdigest(), 16)
        selected_response = fallback_responses[hash_value % len(fallback_responses)]
        
        return selected_response


# Global retrieval engine instance
retrieval_engine = RetrievalEngine()
