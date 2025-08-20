#!/usr/bin/env python3
"""
Railway startup script for OnlyAI Telegram Agent
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.main import app
from app.bot import set_webhook
from app.config import settings
import uvicorn

async def setup_webhook():
    """Set up webhook for Railway deployment"""
    try:
        print("🔗 Setting up Telegram webhook...")
        success = await set_webhook()
        if success:
            print("✅ Webhook set successfully")
        else:
            print("❌ Failed to set webhook")
    except Exception as e:
        print(f"❌ Webhook setup error: {e}")

def main():
    """Main startup function for Railway"""
    print("🚀 Starting OnlyAI Telegram Agent on Railway...")
    print("=" * 50)
    
    # Set up webhook asynchronously
    asyncio.run(setup_webhook())
    
    # Start the FastAPI app
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"🌐 Starting server on {host}:{port}")
    print("📱 Bot is ready to receive webhooks")
    print("⏹️  Press Ctrl+C to stop")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
