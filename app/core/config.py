import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings."""

    # Application
    PROJECT_NAME: str = "Bitewise API"
    PROJECT_DESCRIPTION: str = "Backend API for Bitewise"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    JWT_ALGORITHM: str = "HS256"
    LOGIN_OTP_THRESHOLD_DAYS: int = int(os.getenv("LOGIN_OTP_THRESHOLD_DAYS", "7"))  # Require OTP if last login > 7 days ago
    
    # Email (Resend)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@bitewise.io")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "BiteWise")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_CALLBACK_URL: str = os.getenv("GOOGLE_CALLBACK_URL", "http://localhost:8000/api/v1/auth/google/callback")
    
    # Frontend
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8080")
    
    # OpenAI API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")  # This should be the service_role key for server-side operations
    SUPABASE_BUCKET_NAME: str = os.getenv("SUPABASE_BUCKET_NAME", "chat-images")
    
    # File Upload
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))  # 10MB default
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    # YouTube API
    YOUTUBE_V3_API_KEY: str = os.getenv("YOUTUBE_V3_API_KEY", "")
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:3000", "http://localhost:8080", "https://bitewise-delta.vercel.app", "https://bitewise.twiggle.tech"]
    
    # Database
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOCAL_DATABASE_URL: str = os.getenv("LOCAL_DATABASE_URL", "postgresql://bitewise:your_password@localhost:5432/bitewise_dev")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Async Database Configuration
    @property
    def async_database_url(self) -> str:
        """Get async database URL based on environment."""
        if self.ENVIRONMENT == "development":
            base_url = self.LOCAL_DATABASE_URL
        else:
            base_url = self.DATABASE_URL
        
        # Convert postgresql:// to postgresql+asyncpg://
        if base_url.startswith("postgresql://"):
            return base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif base_url.startswith("postgres://"):
            return base_url.replace("postgres://", "postgresql+asyncpg://", 1)
        else:
            return base_url
    

    
    # Async Connection Pool Configuration - Optimized for Production
    ASYNC_DB_POOL_SIZE: int = int(os.getenv("ASYNC_DB_POOL_SIZE", "20"))
    ASYNC_DB_MAX_OVERFLOW: int = int(os.getenv("ASYNC_DB_MAX_OVERFLOW", "30"))  # Increased for burst capacity
    ASYNC_DB_POOL_RECYCLE: int = int(os.getenv("ASYNC_DB_POOL_RECYCLE", "3600"))  # 1 hour
    ASYNC_DB_POOL_PRE_PING: bool = os.getenv("ASYNC_DB_POOL_PRE_PING", "true").lower() == "true"
    ASYNC_DB_ECHO: bool = os.getenv("ASYNC_DB_ECHO", "false").lower() == "true"
    ASYNC_DB_POOL_TIMEOUT: int = int(os.getenv("ASYNC_DB_POOL_TIMEOUT", "30"))  # Connection timeout
    ASYNC_DB_COMMAND_TIMEOUT: int = int(os.getenv("ASYNC_DB_COMMAND_TIMEOUT", "60"))  # Query timeout
    ASYNC_DB_STATEMENT_TIMEOUT: int = int(os.getenv("ASYNC_DB_STATEMENT_TIMEOUT", "300000"))  # 5 minutes
    ASYNC_DB_IDLE_TIMEOUT: int = int(os.getenv("ASYNC_DB_IDLE_TIMEOUT", "600000"))  # 10 minutes
    
    # Connection Pool Health Monitoring
    ASYNC_DB_HEALTH_CHECK_INTERVAL: int = int(os.getenv("ASYNC_DB_HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes
    ASYNC_DB_METRICS_RESET_INTERVAL: int = int(os.getenv("ASYNC_DB_METRICS_RESET_INTERVAL", "3600"))  # 1 hour
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

settings = Settings() 
