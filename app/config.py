import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    embed_model: str = "text-embedding-3-large"
    
    # Telegram Configuration
    telegram_bot_token: str = ""
    telegram_webhook_base: str = ""
    
    # Admin Configuration
    admin_token: str = ""
    owner_telegram_id: int = 5822224802
    
    # Database Configuration
    database_url: str = ""
    pgvector_enabled: bool = True
    
    # Storage Configuration
    file_storage_dir: str = "./data"
    
    # Logging Configuration
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


# Create settings instance
settings = Settings()
