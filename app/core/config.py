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
    
    # Email (Resend)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@bitewise.io")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "BiteWise")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_CALLBACK_URL: str = os.getenv("GOOGLE_CALLBACK_URL", "http://localhost:8000/api/v1/auth/google/callback")
    
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
    CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:3000", "https://bitewise-delta.vercel.app"]
    
    # Database
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOCAL_DATABASE_URL: str = os.getenv("LOCAL_DATABASE_URL", "postgresql://bitewise:your_password@localhost:5432/bitewise_dev")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

settings = Settings() 
