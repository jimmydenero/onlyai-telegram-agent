import asyncio
from datetime import date, datetime, timedelta
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db.repo import repo
from app.llm.client import llm_client
from app.retrieval.embed import embedding_manager
from app.utils.text import should_keep_message


class GroupDigestGenerator:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    async def generate_daily_digest(self, target_date: date = None) -> Dict[str, Any]:
        """Generate daily digest from kept messages"""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)  # Yesterday
        
        # Get kept messages for the date
        messages = await repo.get_kept_messages_for_digest(target_date)
        
        if not messages:
            return {
                'date': str(target_date),
                'digest_created': False,
                'message': 'No kept messages found for this date'
            }
        
        # Extract message texts
        message_texts = [msg['text'] for msg in messages]
        
        # Generate digest using LLM
        digest_text = await llm_client.generate_digest(message_texts, str(target_date))
        
        # Create digest metadata
        digest_meta = {
            'date': str(target_date),
            'message_count': len(messages),
            'chat_ids': list(set(msg['chat_id'] for msg in messages)),
            'user_count': len(set(msg['sender_id'] for msg in messages))
        }
        
        # Store digest with embedding
        stored_digest = await embedding_manager.embed_digest(
            text=digest_text,
            date=target_date,
            meta=digest_meta
        )
        
        return {
            'date': str(target_date),
            'digest_created': True,
            'digest_id': stored_digest['id'],
            'message_count': len(messages),
            'digest_length': len(digest_text)
        }
    
    async def process_message_for_digest(self, chat_id: int, sender_id: int, text: str) -> bool:
        """Process a message to determine if it should be kept for digest"""
        # Check if message should be kept
        should_keep = should_keep_message(text)
        
        # Store message with kept flag
        await repo.store_message(
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            kept=should_keep
        )
        
        return should_keep
    
    async def cleanup_old_messages(self, days: int = 14) -> int:
        """Clean up old messages while keeping digests"""
        return await repo.cleanup_old_messages(days)
    
    def start_scheduler(self):
        """Start the scheduler for nightly digest generation"""
        # Schedule daily digest at 2:00 UTC
        self.scheduler.add_job(
            self.generate_daily_digest,
            CronTrigger(hour=2, minute=0),
            id='daily_digest',
            name='Generate daily digest',
            replace_existing=True
        )
        
        # Schedule cleanup every week
        self.scheduler.add_job(
            self.cleanup_old_messages,
            CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='cleanup_messages',
            name='Clean up old messages',
            replace_existing=True
        )
        
        self.scheduler.start()
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
    
    async def generate_digest_for_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Generate digests for a date range (useful for backfilling)"""
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                result = await self.generate_daily_digest(current_date)
                results.append(result)
            except Exception as e:
                results.append({
                    'date': str(current_date),
                    'digest_created': False,
                    'error': str(e)
                })
            
            current_date += timedelta(days=1)
        
        return results
    
    async def get_digest_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get digest statistics for the last N days"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get digests in date range
        # Note: This would require adding a method to repo to get digests by date range
        # For now, return placeholder stats
        return {
            'period_days': days,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'total_digests': 0,  # Would be calculated from DB
            'avg_messages_per_digest': 0,  # Would be calculated from DB
            'total_messages_processed': 0  # Would be calculated from DB
        }


# Global digest generator instance
digest_generator = GroupDigestGenerator()
