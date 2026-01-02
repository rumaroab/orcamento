"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/budget_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = "ollama"  # Options: 'openai', 'ollama', 'disabled'
    LLM_DISABLED: bool = False  # Set to True to skip LLM calls for debugging (overrides provider)
    
    # OpenAI Configuration (for provider='openai')
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    # Ollama Configuration (for provider='ollama')
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:4b-instruct"  # Recommended: qwen2.5:3b-instruct, llama2, mistral, phi, etc.
    OLLAMA_USE_CHAT_API: Optional[bool] = None  # Auto-detect based on model name (instruct/chat models)
    
    # File storage
    STORAGE_PATH: str = "./storage"
    
    # API
    API_V1_PREFIX: str = "/api"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

