import logging
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config import settings
from app.db.repo import repo
from app.handlers.qa import qa_handler
from app.ingest.group_digest import digest_generator
from app.security import check_user_permission
from app.utils.text import should_keep_message

# Import monitoring functionality
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from message_classifier import classifier
    from message_storage import storage
except ImportError as e:
    print(f"⚠️  Monitoring modules not found: {e}")
    # Create dummy objects to prevent crashes
    class DummyClassifier:
        async def classify_message(self, text, username):
            return {"category": "USELESS", "should_store": False}
    classifier = DummyClassifier()
    
    class DummyStorage:
        def add_message(self, msg): pass
        def get_stats(self): return {"total_messages": 0, "by_category": {}, "by_user": {}, "recent_activity": 0}
    storage = DummyStorage()

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

# Global monitoring state
monitoring_active = False
monitored_groups = {}

@dp.message(Command("test"))
async def test_command(message: Message):
    """Handle /test command"""
    try:
        user_id = message.from_user.id
        
        # Check permissions
        permission = await check_user_permission(user_id)
        
        if not permission['allowed']:
            await message.reply("Access denied. Please contact an administrator to be added to the whitelist.")
            return
        
        # Run test
        result = await qa_handler.handle_test_command(user_id)
        await message.reply(result)
        
    except Exception as e:
        logger.error(f"Error in test command: {e}")
        await message.reply("❌ Test failed. Please try again later.")

@dp.message(Command("monitor"))
async def monitor_command(message: Message):
    """Handle /monitor command"""
    try:
        global monitoring_active, monitored_groups
        
        monitoring_active = not monitoring_active
        status = "🟢 STARTED" if monitoring_active else "🔴 STOPPED"
        
        # Add group info to monitoring
        chat_id = message.chat.id
        chat_title = message.chat.title or "Private Chat"
        
        if monitoring_active:
            monitored_groups[chat_id] = chat_title
            logger.info(f"📊 Started monitoring: {chat_title} (ID: {chat_id})")
        else:
            if chat_id in monitored_groups:
                del monitored_groups[chat_id]
                logger.info(f"📊 Stopped monitoring: {chat_title} (ID: {chat_id})")
        
        # Try to send confirmation, but don't fail if we can't
        try:
            response = f"📊 Chat monitoring {status}\n\nI will now silently monitor and classify messages (information, questions, answers)."
            await message.reply(response)
        except Exception as reply_error:
            logger.info(f"📊 Monitoring {status} for {chat_title} (silent mode - no reply sent)")
            
    except Exception as e:
        logger.error(f"❌ Monitor command error: {e}")
        logger.info(f"📊 Monitoring status changed but couldn't send confirmation")

@dp.message(Command("groups"))
async def groups_command(message: Message):
    """Handle /groups command"""
    try:
        if monitored_groups:
            groups_text = "📊 Currently Monitoring:\n\n"
            for chat_id, chat_title in monitored_groups.items():
                groups_text += f"• {chat_title} (ID: {chat_id})\n"
        else:
            groups_text = "📊 Not monitoring any groups currently.\n\nUse /monitor to start monitoring this chat."
        
        await message.reply(groups_text)
    except Exception as e:
        logger.error(f"❌ Groups command error: {e}")
        # Log groups to console instead of trying to send error message
        if monitored_groups:
            logger.info(f"📊 Currently monitoring: {list(monitored_groups.values())}")
        else:
            logger.info(f"📊 Not monitoring any groups")

@dp.message(Command("stats"))
async def stats_command(message: Message):
    """Handle /stats command"""
    try:
        stats = storage.get_stats()
        
        stats_text = f"""
📊 Monitoring Statistics:

Total Messages: {stats['total_messages']}
Recent Activity (24h): {stats['recent_activity']}

By Category:
"""
        for category, count in stats['by_category'].items():
            stats_text += f"• {category}: {count}\n"
        
        stats_text += "\nTop Users:\n"
        sorted_users = sorted(stats['by_user'].items(), key=lambda x: x[1], reverse=True)[:5]
        for username, count in sorted_users:
            stats_text += f"• {username}: {count}\n"
        
        await message.reply(stats_text)
    except Exception as e:
        logger.error(f"❌ Stats command error: {e}")
        # Log stats to console instead of trying to send error message
        logger.info(f"📊 Stats requested but couldn't send reply. Stats: {stats}")

@dp.message()
async def handle_message(message: Message):
    """Handle all messages (both DMs and group messages)"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text
        
        if not text:
            return
        
        # Get username for monitoring
        username = message.from_user.username or message.from_user.first_name or "Unknown"
        
        # Monitor and classify message if monitoring is active
        if monitoring_active and chat_id in monitored_groups:
            try:
                classification = await classifier.classify_message(text, username)
                storage.add_message(classification)
                
                # Log classification (optional)
                if classification.get("should_store"):
                    logger.info(f"📝 Classified as {classification['category']}: {text[:50]}...")
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
        
        # Store message for digest processing (if in group)
        if message.chat.type in ['group', 'supergroup']:
            kept = should_keep_message(text)
            await repo.store_message(chat_id, user_id, text, kept)
            
            # Only respond to mentions or direct messages to bot
            if not message.text.startswith('/') and not message.entities:
                # Check if bot is mentioned
                bot_mentioned = False
                if message.entities:
                    for entity in message.entities:
                        if entity.type == 'mention' and '@' + (await bot.me()).username in text:
                            bot_mentioned = True
                            break
                
                if not bot_mentioned:
                    return  # Don't respond to regular group messages
        
        # Check permissions for Q&A
        permission = await check_user_permission(user_id)
        
        if not permission['allowed']:
            await message.reply("Access denied. Please contact an administrator to be added to the whitelist.")
            return
        
        # Handle greetings
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if text.lower().strip() in greeting_words:
            response = await qa_handler.handle_greeting(user_id)
            await message.reply(response)
            return
        
        # Process question
        result = await qa_handler.process_question(user_id, text, chat_id)
        await message.reply(result['answer'])
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        try:
            await message.reply("Sorry, I encountered an error. Please try again later.")
        except:
            logger.error(f"❌ Couldn't send error message: {str(e)}")

async def set_webhook():
    """Set webhook for the bot"""
    try:
        webhook_url = f"{settings.telegram_webhook_base}/webhook"
        await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
        return True
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return False

async def remove_webhook():
    """Remove webhook for the bot"""
    try:
        await bot.delete_webhook()
        logger.info("Webhook removed")
        return True
    except Exception as e:
        logger.error(f"Failed to remove webhook: {e}")
        return False

def create_webhook_app():
    """Create webhook application"""
    app = web.Application()
    
    # Create webhook handler
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    
    # Set webhook path
    webhook_handler.register(app, path="/webhook")
    
    return app


# For development with polling
async def start_polling():
    """Start bot with polling (for development)"""
    logger.info("Starting bot with polling...")
    
    # Start digest scheduler
    digest_generator.start_scheduler()
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        digest_generator.stop_scheduler()
        await bot.session.close()
