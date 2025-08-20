import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.bot import bot, set_webhook, remove_webhook, create_webhook_app
from app.handlers.admin import router as admin_router
from app.security import verify_admin_token
from app.ingest.group_digest import digest_generator

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting OnlyAI Telegram Agent...")
    
    # Start digest scheduler
    digest_generator.start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("Shutting down OnlyAI Telegram Agent...")
    
    # Stop digest scheduler
    digest_generator.stop_scheduler()
    
    # Close bot session
    await bot.session.close()


# Create FastAPI app
app = FastAPI(
    title="OnlyAI Telegram Agent",
    description="AI-powered Telegram bot for OnlyAi course Q&A with knowledge base",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include admin router
app.include_router(admin_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OnlyAI Telegram Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        from app.db.repo import repo
        await repo.get_connection()
        
        # Test OpenAI connection
        from app.llm.client import llm_client
        test_embedding = await llm_client.embed_text("health check")
        
        return {
            "status": "healthy",
            "database": "connected",
            "openai": "connected",
            "bot": "running"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/webhook/set")
async def set_webhook_endpoint(_: bool = Depends(verify_admin_token)):
    """Set Telegram webhook"""
    try:
        success = await set_webhook()
        if success:
            return {"message": "Webhook set successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/remove")
async def remove_webhook_endpoint(_: bool = Depends(verify_admin_token)):
    """Remove Telegram webhook"""
    try:
        success = await remove_webhook()
        if success:
            return {"message": "Webhook removed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove webhook")
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhook/info")
async def webhook_info(_: bool = Depends(verify_admin_token)):
    """Get webhook information"""
    try:
        webhook_info = await bot.get_webhook_info()
        return {
            "url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections,
            "allowed_updates": webhook_info.allowed_updates
        }
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bot/info")
async def bot_info(_: bool = Depends(verify_admin_token)):
    """Get bot information"""
    try:
        bot_info = await bot.get_me()
        return {
            "id": bot_info.id,
            "username": bot_info.username,
            "first_name": bot_info.first_name,
            "can_join_groups": bot_info.can_join_groups,
            "can_read_all_group_messages": bot_info.can_read_all_group_messages,
            "supports_inline_queries": bot_info.supports_inline_queries
        }
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )
