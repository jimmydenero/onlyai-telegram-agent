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

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        "OPENAI_API_KEY",
        "TELEGRAM_BOT_TOKEN", 
        "DATABASE_URL",
        "ADMIN_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please set these variables in Railway dashboard:")
        print("   Go to your Railway project → Variables tab")
        print("   Add the missing environment variables")
        return False
    
    print("✅ All required environment variables are set")
    return True

async def setup_webhook():
    """Set up webhook for Railway deployment"""
    try:
        print("🔗 Setting up Telegram webhook...")
        # Check if we have the required environment variables
        if not os.environ.get("TELEGRAM_WEBHOOK_BASE"):
            print("⚠️  TELEGRAM_WEBHOOK_BASE not set, skipping webhook setup")
            return
            
        # Import here to avoid issues with missing env vars
        from app.bot import set_webhook
        success = await set_webhook()
        if success:
            print("✅ Webhook set successfully")
        else:
            print("❌ Failed to set webhook")
    except Exception as e:
        print(f"❌ Webhook setup error: {e}")
        print("⚠️  Continuing without webhook setup")

def main():
    """Main startup function for Railway"""
    print("🚀 Starting OnlyAI Telegram Agent on Railway...")
    print("=" * 50)
    
    # Check environment variables first
    if not check_environment():
        print("\n🛑 Cannot start without required environment variables")
        print("💡 Set the missing variables in Railway dashboard and redeploy")
        sys.exit(1)
    
    try:
        # Set up webhook asynchronously
        asyncio.run(setup_webhook())
    except Exception as e:
        print(f"⚠️  Webhook setup failed: {e}")
        print("🔄 Continuing with app startup...")
    
    # Start the FastAPI app
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"🌐 Starting server on {host}:{port}")
    print("📱 Bot is ready to receive webhooks")
    print("⏹️  Press Ctrl+C to stop")
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
