#!/usr/bin/env python3
"""
Message storage system for chat monitoring
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class MessageStorage:
    def __init__(self, storage_file: str = "chat_messages.json"):
        self.storage_file = storage_file
        self.messages = []
        self.load_messages()
    
    def load_messages(self):
        """Load existing messages from file"""
        if Path(self.storage_file).exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
                print(f"📚 Loaded {len(self.messages)} stored messages")
            except Exception as e:
                print(f"❌ Error loading messages: {e}")
                self.messages = []
        else:
            self.messages = []
    
    def save_messages(self):
        """Save messages to file"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving messages: {e}")
    
    def add_message(self, message_data: Dict):
        """Add a new message to storage"""
        if message_data.get("should_store", False):
            self.messages.append(message_data)
            self.save_messages()
            print(f"💾 Stored {message_data['category']} message from {message_data['username']}")
    
    def search_messages(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Search for relevant messages"""
        results = []
        
        for message in self.messages:
            # Skip if category filter is specified and doesn't match
            if category and message.get("category") != category:
                continue
            
            # Simple text search
            text = message.get("clean_text", "").lower()
            if query.lower() in text:
                results.append(message)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]
    
    def get_questions_and_answers(self, query: str) -> List[Dict]:
        """Find questions and their corresponding answers"""
        relevant_messages = []
        
        # Find questions related to the query
        for message in self.messages:
            if message.get("category") == "QUESTION":
                text = message.get("clean_text", "").lower()
                if query.lower() in text:
                    relevant_messages.append(message)
        
        # Find answers that might be related
        for message in self.messages:
            if message.get("category") == "ANSWER":
                text = message.get("clean_text", "").lower()
                if query.lower() in text:
                    relevant_messages.append(message)
        
        # Sort by timestamp
        relevant_messages.sort(key=lambda x: x.get("timestamp", ""))
        return relevant_messages
    
    def get_stats(self) -> Dict:
        """Get storage statistics"""
        stats = {
            "total_messages": len(self.messages),
            "by_category": {},
            "by_user": {},
            "recent_activity": 0
        }
        
        # Count by category and user
        for message in self.messages:
            category = message.get("category", "UNKNOWN")
            username = message.get("username", "Unknown")
            
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            stats["by_user"][username] = stats["by_user"].get(username, 0) + 1
        
        # Count recent activity (last 24 hours)
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=24)
        for message in self.messages:
            try:
                msg_time = datetime.fromisoformat(message.get("timestamp", ""))
                if msg_time > cutoff:
                    stats["recent_activity"] += 1
            except:
                pass
        
        return stats
    
    def clear_old_messages(self, days: int = 30):
        """Clear messages older than specified days"""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        original_count = len(self.messages)
        self.messages = [
            msg for msg in self.messages
            if datetime.fromisoformat(msg.get("timestamp", "")) > cutoff
        ]
        
        removed_count = original_count - len(self.messages)
        if removed_count > 0:
            self.save_messages()
            print(f"🗑️  Removed {removed_count} old messages")

# Global storage instance
storage = MessageStorage()
