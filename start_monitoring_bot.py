#!/usr/bin/env python3
"""
Enhanced knowledge bot with chat monitoring functionality
"""

import os
import sys
import asyncio
from pathlib import Path
from app.config import settings
from app.llm.client import llm_client
from message_classifier import classifier
from message_storage import storage

class MonitoringKnowledgeBot:
    def __init__(self):
        self.knowledge_file = "knowledge_base.txt"
        self.chunks = []
        self.monitoring_active = False
        self.load_knowledge()
    
    def load_knowledge(self):
        """Load knowledge from file"""
        if Path(self.knowledge_file).exists():
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    self.chunks = [chunk.strip() for chunk in content.split('\n\n---\n\n') if chunk.strip()]
                    print(f"📚 Loaded {len(self.chunks)} knowledge chunks")
    
    async def search_knowledge(self, query: str, top_k: int = 3) -> list:
        """Search knowledge base using embeddings"""
        if not self.chunks:
            return []
        
        try:
            # Generate query embedding
            query_embedding = await llm_client.embed_text(query)
            
            # Generate embeddings for all chunks
            chunk_embeddings = await llm_client.embed_batch(self.chunks)
            
            # Calculate similarities
            similarities = []
            for i, chunk_embedding in enumerate(chunk_embeddings):
                similarity = self.cosine_similarity(query_embedding, chunk_embedding)
                similarities.append((similarity, self.chunks[i]))
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x[0], reverse=True)
            return [chunk for _, chunk in similarities[:top_k]]
        
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    async def search_chat_history(self, query: str) -> list:
        """Search stored chat messages for relevant Q&A"""
        relevant_messages = storage.get_questions_and_answers(query)
        
        if relevant_messages:
            # Format messages for context
            context_parts = []
            for msg in relevant_messages:
                username = msg.get("username", "Unknown")
                category = msg.get("category", "UNKNOWN")
                text = msg.get("clean_text", "")
                
                if category == "QUESTION":
                    context_parts.append(f"Question by {username}: {text}")
                elif category == "ANSWER":
                    context_parts.append(f"Answer by {username}: {text}")
            
            return context_parts
        
        return []
    
    async def generate_answer(self, question: str) -> str:
        """Generate answer using knowledge base and chat history"""
        # Search knowledge base
        relevant_chunks = await self.search_knowledge(question, top_k=3)
        
        # Search chat history
        chat_context = await self.search_chat_history(question)
        
        # Build context
        context_parts = []
        
        if relevant_chunks:
            context_parts.append("Knowledge Base:\n" + "\n\n".join(relevant_chunks))
        
        if chat_context:
            context_parts.append("Previous Group Discussion:\n" + "\n".join(chat_context))
        
        # Generate answer
        if context_parts:
            context = "\n\n".join(context_parts)
            
            # Check if we have chat history answers
            has_chat_answers = any("Answer by" in part for part in chat_context)
            
            if has_chat_answers:
                # Include warning about non-Jimmy answers
                response = await llm_client.chat_completion([
                    {"role": "system", "content": "You are the OnlyAi Support Bot, built to assist members of Jimmy DeNiro's OnlyAi Telegram group. Your role is to answer student questions using the provided knowledge base and stored chat history.\n\nResponse Style:\n• Keep answers short, clear, and conversational (under 50 words).\n• Sound natural — avoid robotic or overly formal tones.\n• Never restate the question.\n• Only answer what is asked, nothing extra.\n• For vague greetings (\"hey\", \"hello\", \"help\"): Reply with prompts like: \"Hey, what do you need help with?\" or \"What's your question?\"\n\nKnowledge Usage (RAG):\n• Always pull from the OnlyAi knowledge base and group chat history first.\n• Never output full documents, long summaries, or dump strategies.\n• Provide only directly relevant information to the current question.\n\nBoundaries:\n• Do not generate full agency or business plans.\n• If asked, respond with: \"I'm not meant to create full plans, but I can answer specific questions.\"\n• Do not invent missing information. If unavailable, respond: \"I don't have that information.\"\n• Stay focused on OnlyAi course content, AI OFM strategies, and group-relevant discussions.\n\nIMPORTANT: If you reference group chat answers, always add: \"⚠️ This wasn't answered by Jimmy, so proceed with caution.\"\n\nCore Goal: Be a helpful, brief, and human-sounding guide for OnlyAi group members. Provide direct answers from the knowledge base, without unnecessary detail or robotic formality."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
                ], max_tokens=200)
            else:
                response = await llm_client.chat_completion([
                    {"role": "system", "content": "You are the OnlyAi Support Bot, built to assist members of Jimmy DeNiro's OnlyAi Telegram group. Your role is to answer student questions using the provided knowledge base and stored chat history.\n\nResponse Style:\n• Keep answers short, clear, and conversational (under 50 words).\n• Sound natural — avoid robotic or overly formal tones.\n• Never restate the question.\n• Only answer what is asked, nothing extra.\n• For vague greetings (\"hey\", \"hello\", \"help\"): Reply with prompts like: \"Hey, what do you need help with?\" or \"What's your question?\"\n\nKnowledge Usage (RAG):\n• Always pull from the OnlyAi knowledge base and group chat history first.\n• Never output full documents, long summaries, or dump strategies.\n• Provide only directly relevant information to the current question.\n\nBoundaries:\n• Do not generate full agency or business plans.\n• If asked, respond with: \"I'm not meant to create full plans, but I can answer specific questions.\"\n• Do not invent missing information. If unavailable, respond: \"I don't have that information.\"\n• Stay focused on OnlyAi course content, AI OFM strategies, and group-relevant discussions.\n\nCore Goal: Be a helpful, brief, and human-sounding guide for OnlyAi group members. Provide direct answers from the knowledge base, without unnecessary detail or robotic formality."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
                ], max_tokens=200)
            
            return response
        else:
            # No relevant knowledge found
            response = await llm_client.chat_completion([
                {"role": "system", "content": "You are the OnlyAi Support Bot, built to assist members of Jimmy DeNiro's OnlyAi Telegram group. Your role is to answer student questions using the provided knowledge base and stored chat history.\n\nResponse Style:\n• Keep answers short, clear, and conversational (under 50 words).\n• Sound natural — avoid robotic or overly formal tones.\n• Never restate the question.\n• Only answer what is asked, nothing extra.\n• For vague greetings (\"hey\", \"hello\", \"help\"): Reply with prompts like: \"Hey, what do you need help with?\" or \"What's your question?\"\n\nKnowledge Usage (RAG):\n• Always pull from the OnlyAi knowledge base and group chat history first.\n• Never output full documents, long summaries, or dump strategies.\n• Provide only directly relevant information to the current question.\n\nBoundaries:\n• Do not generate full agency or business plans.\n• If asked, respond with: \"I'm not meant to create full plans, but I can answer specific questions.\"\n• Do not invent missing information. If unavailable, respond: \"I don't have that information.\"\n• Stay focused on OnlyAi course content, AI OFM strategies, and group-relevant discussions.\n\nCore Goal: Be a helpful, brief, and human-sounding guide for OnlyAi group members. Provide direct answers from the knowledge base, without unnecessary detail or robotic formality."},
                {"role": "user", "content": f"Question: {question}"}
            ], max_tokens=150)
            
            return response

async def start_bot():
    """Start the enhanced monitoring bot"""
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import Command
    
    # Initialize bot and knowledge base
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    kb = MonitoringKnowledgeBot()
    
    @dp.message(Command("test"))
    async def test_command(message: types.Message):
        await message.reply("✅ Monitoring bot is working!")
    
    @dp.message(Command("help"))
    async def help_command(message: types.Message):
        help_text = """
🤖 OnlyAI Monitoring Bot

Available commands:
/test - Test bot connectivity
/help - Show this help message
/knowledge - Show knowledge base status
/monitor - Start/stop chat monitoring
/groups - Show monitored groups
/stats - Show monitoring statistics

Just send me any question about OnlyAi or AI-OFM strategies!
        """
        await message.reply(help_text)
    
    @dp.message(Command("knowledge"))
    async def knowledge_command(message: types.Message):
        if kb.chunks:
            await message.reply(f"📚 Knowledge base loaded with {len(kb.chunks)} chunks")
        else:
            await message.reply("📚 No knowledge base loaded. Use upload interface to add documents.")
    
    @dp.message(Command("monitor"))
    async def monitor_command(message: types.Message):
        try:
            kb.monitoring_active = not kb.monitoring_active
            status = "🟢 STARTED" if kb.monitoring_active else "🔴 STOPPED"
            
            # Add group info to monitoring
            chat_id = message.chat.id
            chat_title = message.chat.title or "Private Chat"
            
            if kb.monitoring_active:
                if not hasattr(kb, 'monitored_groups'):
                    kb.monitored_groups = {}
                kb.monitored_groups[chat_id] = chat_title
                print(f"📊 Started monitoring: {chat_title} (ID: {chat_id})")
            else:
                if hasattr(kb, 'monitored_groups') and chat_id in kb.monitored_groups:
                    del kb.monitored_groups[chat_id]
                    print(f"📊 Stopped monitoring: {chat_title} (ID: {chat_id})")
            
            # Try to send confirmation, but don't fail if we can't
            try:
                response = f"📊 Chat monitoring {status}\n\nI will now silently monitor and classify messages (information, questions, answers)."
                await message.reply(response)
            except Exception as reply_error:
                print(f"📊 Monitoring {status} for {chat_title} (silent mode - no reply sent)")
                
        except Exception as e:
            print(f"❌ Monitor command error: {e}")
            # Don't try to send error message - just log it
            print(f"📊 Monitoring status changed but couldn't send confirmation")
    
    @dp.message(Command("stats"))
    async def stats_command(message: types.Message):
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
            print(f"❌ Stats command error: {e}")
            # Log stats to console instead of trying to send error message
            print(f"📊 Stats requested but couldn't send reply. Stats: {stats}")
    
    @dp.message(Command("groups"))
    async def groups_command(message: types.Message):
        try:
            if hasattr(kb, 'monitored_groups') and kb.monitored_groups:
                groups_text = "📊 Currently Monitoring:\n\n"
                for chat_id, chat_title in kb.monitored_groups.items():
                    groups_text += f"• {chat_title} (ID: {chat_id})\n"
            else:
                groups_text = "📊 Not monitoring any groups currently.\n\nUse /monitor to start monitoring this chat."
            
            await message.reply(groups_text)
        except Exception as e:
            print(f"❌ Groups command error: {e}")
            # Log groups to console instead of trying to send error message
            if hasattr(kb, 'monitored_groups') and kb.monitored_groups:
                print(f"📊 Currently monitoring: {list(kb.monitored_groups.values())}")
            else:
                print(f"📊 Not monitoring any groups")
    
    @dp.message()
    async def handle_message(message: types.Message):
        if not message.text:
            return
        
        # Skip commands
        if message.text.startswith('/'):
            return
        
        # Get username
        username = message.from_user.username or message.from_user.first_name or "Unknown"
        
        # Monitor and classify message if monitoring is active
        if kb.monitoring_active:
            # Check if this chat is being monitored
            chat_id = message.chat.id
            if hasattr(kb, 'monitored_groups') and chat_id in kb.monitored_groups:
                try:
                    classification = await classifier.classify_message(message.text, username)
                    storage.add_message(classification)
                    
                    # Log classification (optional)
                    if classification.get("should_store"):
                        print(f"📝 Classified as {classification['category']}: {message.text[:50]}...")
                except Exception as e:
                    print(f"❌ Monitoring error: {e}")
        
        # Handle greetings
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if message.text.lower().strip() in greeting_words:
            await message.reply("How can I help you with OnlyAi and AI-OFM strategies?")
            return
        
        # Generate answer using knowledge base and chat history
        try:
            answer = await kb.generate_answer(message.text)
            await message.reply(answer)
        except Exception as e:
            try:
                await message.reply(f"Sorry, I encountered an error: {str(e)}")
            except:
                print(f"❌ Couldn't send error message: {str(e)}")
    
    print("🤖 Starting enhanced monitoring bot...")
    print(f"📚 Knowledge base: {len(kb.chunks)} chunks loaded")
    print(f"💾 Chat storage: {len(storage.messages)} messages loaded")
    print("📱 Bot will respond to questions using knowledge base + chat history")
    print("📊 Use /monitor to start chat monitoring")
    print("⏹️  Press Ctrl+C to stop")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        await bot.session.close()

def main():
    """Main startup function"""
    print("🚀 Starting OnlyAI Monitoring Bot...")
    print("=" * 50)
    
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

if __name__ == "__main__":
    main()
