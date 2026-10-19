import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "StudySphere AI"
    APP_ENV: str = "production"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str = "studysphere-super-secret-key-change-in-production"

    # Active Provider: "gemini" | "openai" | "ollama"
    DEFAULT_MODEL_PROVIDER: str = "gemini"

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Ollama / Local
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # RAG Settings
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    TOP_K_CHUNKS: int = 4
    SIMILARITY_THRESHOLD: float = 0.30

    # Paths
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploads")
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma_db")
    MAX_UPLOAD_SIZE_MB: int = 25

    # Simulation fallback when API key is missing
    ENABLE_SIMULATION_MODE: bool = True

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

# Ensure required storage directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
