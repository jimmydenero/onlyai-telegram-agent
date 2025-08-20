import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o"
    embed_model: str = "text-embedding-3-large"
    
    # Telegram Configuration
    telegram_bot_token: str
    telegram_webhook_base: str
    owner_telegram_id: int = 5822224802
    
    # Security
    admin_token: str
    
    # Database
    database_url: str
    pgvector_enabled: bool = True
    
    # Storage
    file_storage_dir: str = "./data"
    
    # Logging
    log_level: str = "info"
    
    # Application Settings
    max_answer_length: int = 500
    context_messages: int = 10
    retrieval_top_k: int = 8
    chunk_min_tokens: int = 300
    chunk_max_tokens: int = 800
    chunk_overlap_percent: float = 0.15
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
