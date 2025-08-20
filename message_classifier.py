#!/usr/bin/env python3
"""
Message classification system for chat monitoring
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from app.llm.client import llm_client

class MessageClassifier:
    def __init__(self):
        self.classification_prompt = """
You are a message classifier for a Telegram group chat. Your job is to categorize each message into one of these 5 categories:

1. INFORMATION - Contains useful facts, tips, strategies, or educational content
2. JOKE - Humor, memes, funny comments, or entertainment
3. QUESTION - Asks for help, advice, clarification, or information
4. USELESS - Spam, random characters, or content with no value
5. ANSWER - Responds to someone else's question or provides help

Rules:
- Be strict about USELESS - only mark as useless if truly no value
- JOKE includes sarcasm, humor, and entertainment
- INFORMATION includes tips, strategies, tutorials, and educational content
- QUESTION includes both direct questions and implied requests for help
- ANSWER includes responses to others, even if not directly answering a question

Respond with ONLY the category name (INFORMATION, JOKE, QUESTION, USELESS, or ANSWER).
"""

    async def classify_message(self, message_text: str, username: str = "Unknown") -> Dict:
        """
        Classify a message and return detailed information
        """
        try:
            # Clean the message text
            clean_text = self._clean_message(message_text)
            
            if not clean_text.strip():
                return {
                    "category": "USELESS",
                    "confidence": 1.0,
                    "reason": "Empty or whitespace-only message",
                    "timestamp": datetime.now().isoformat(),
                    "username": username,
                    "original_text": message_text,
                    "clean_text": clean_text
                }
            
            # Get AI classification
            classification = await llm_client.chat_completion([
                {"role": "system", "content": self.classification_prompt},
                {"role": "user", "content": f"Classify this message: '{clean_text}'"}
            ], max_tokens=10, temperature=0.1)
            
            # Clean the response
            category = classification.strip().upper()
            if category not in ["INFORMATION", "JOKE", "QUESTION", "USELESS", "ANSWER"]:
                category = "USELESS"  # Default fallback
            
            # Determine if we should store this message
            should_store = category in ["INFORMATION", "QUESTION", "ANSWER"]
            
            return {
                "category": category,
                "confidence": 0.9,  # High confidence for AI classification
                "reason": f"AI classified as {category}",
                "timestamp": datetime.now().isoformat(),
                "username": username,
                "original_text": message_text,
                "clean_text": clean_text,
                "should_store": should_store
            }
            
        except Exception as e:
            print(f"❌ Classification error: {e}")
            return {
                "category": "USELESS",
                "confidence": 0.0,
                "reason": f"Classification failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "username": username,
                "original_text": message_text,
                "clean_text": message_text,
                "should_store": False
            }
    
    def _clean_message(self, text: str) -> str:
        """Clean and normalize message text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Remove common bot commands and mentions
        text = text.replace("@", "").replace("/", "")
        
        # Remove URLs (simple regex)
        import re
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        return text.strip()
    
    async def batch_classify(self, messages: List[Dict]) -> List[Dict]:
        """Classify multiple messages efficiently"""
        results = []
        for message in messages:
            result = await self.classify_message(
                message.get("text", ""),
                message.get("username", "Unknown")
            )
            results.append(result)
        return results

# Global classifier instance
classifier = MessageClassifier()
