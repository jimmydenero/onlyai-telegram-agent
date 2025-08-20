import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.config import settings
from app.handlers.admin import router as admin_router
from app.ingest.group_digest import digest_generator

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

def check_environment():
    """Check if required environment variables are set"""
    required_vars = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "TELEGRAM_BOT_TOKEN": settings.telegram_bot_token,
        "DATABASE_URL": settings.database_url,
        "ADMIN_TOKEN": settings.admin_token
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        return False
    
    return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting OnlyAI Telegram Agent...")
    
    # Check environment variables
    if not check_environment():
        logger.error("❌ Missing required environment variables")
        logger.error("💡 Please set the missing variables in Railway dashboard")
        logger.error("🛑 Application cannot start without required configuration")
        yield
        return
    
    # Start digest scheduler
    digest_generator.start_scheduler()
    logger.info("✅ Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OnlyAI Telegram Agent...")
    digest_generator.stop_scheduler()
    logger.info("✅ Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="OnlyAI Telegram Agent",
    description="AI-powered Telegram bot for OnlyAi course support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not check_environment():
        raise HTTPException(
            status_code=503, 
            detail="Service unavailable - missing environment variables"
        )
    return {"status": "healthy", "message": "OnlyAI Telegram Agent is running"}

# Webhook management endpoints
@app.post("/webhook/set")
async def set_webhook(token: str = Depends(security)):
    """Set Telegram webhook"""
    if token.credentials != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from app.bot import set_webhook
        success = await set_webhook()
        if success:
            return {"status": "success", "message": "Webhook set successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/remove")
async def remove_webhook(token: str = Depends(security)):
    """Remove Telegram webhook"""
    if token.credentials != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from app.bot import remove_webhook
        success = await remove_webhook()
        if success:
            return {"status": "success", "message": "Webhook removed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove webhook")
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include admin router
app.include_router(admin_router, prefix="/admin", tags=["admin"])

# Webhook handler (for Telegram updates)
@app.post("/webhook")
async def webhook_handler():
    """Handle Telegram webhook updates"""
    try:
        from app.bot import create_webhook_app
        webhook_app = create_webhook_app()
        
        # This is a simplified approach - in production, you'd want to properly
        # handle the webhook request here
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
