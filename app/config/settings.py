"""
Application Settings
Environment-based configuration management
"""

from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Application
    APP_NAME: str = "RickQueue API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development, staging, production
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/rickqueue"
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:19006",  # Expo
        "https://rickqueue.com",
        "https://app.rickqueue.com"
    ]
    
    # AI Configuration
    AI_SCHEDULER_INTERVAL_SECONDS: int = 30
    AI_PROBABILITY_THRESHOLD_LOW: int = 20
    AI_PROBABILITY_THRESHOLD_HIGH: int = 80
    AI_MIN_WAIT_TIME_SECONDS: int = 180  # 3 minutes
    AI_MAX_WAIT_TIME_SECONDS: int = 600  # 10 minutes
    
    # WebSocket
    WEBSOCKET_PING_INTERVAL: int = 25
    WEBSOCKET_PING_TIMEOUT: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/rickqueue.log"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Background Jobs
    HISTORICAL_DATA_REBUILD_HOUR: int = 2  # 2 AM daily
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


def get_database_url(override_url: str = None) -> str:
    """
    Get database URL with fallback logic
    """
    if override_url:
        return override_url
    
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    
    # Construct from parts if DATABASE_URL not set
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "rickqueue")
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "postgres")
    
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


def ensure_log_directory():
    """
    Create log directory if it doesn't exist
    """
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)


def print_settings():
    """
    Print current settings (for debugging)
    Hides sensitive values
    """
    print("\n" + "="*60)
    print("🔧 RICKQUEUE CONFIGURATION")
    print("="*60)
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"Host: {settings.HOST}:{settings.PORT}")
    print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Not configured'}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"CORS Origins: {len(settings.CORS_ORIGINS)} configured")
    print(f"AI Scheduler: Every {settings.AI_SCHEDULER_INTERVAL_SECONDS}s")
    print("="*60 + "\n")