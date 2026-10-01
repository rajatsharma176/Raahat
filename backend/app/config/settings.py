"""
RAAHAT - Autonomous Continuity Engine
Configuration Settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # LLM Configuration
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gemini-2.5-flash", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=8192, alias="LLM_MAX_TOKENS")

    # Application
    app_name: str = "RAAHAT Autonomous Continuity Engine"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./raahat.db", alias="DATABASE_URL")

    # Safety limits
    max_replans: int = Field(default=5, alias="MAX_REPLANS")
    max_tool_retries: int = Field(default=3, alias="MAX_TOOL_RETRIES")
    max_workflow_steps: int = Field(default=50, alias="MAX_WORKFLOW_STEPS")

    # RAG
    rag_top_k: int = Field(default=3, alias="RAG_TOP_K")
    rag_chunk_size: int = Field(default=512, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=64, alias="RAG_CHUNK_OVERLAP")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")

    # Paths
    knowledge_base_path: str = Field(default="knowledge", alias="KNOWLEDGE_BASE_PATH")
    faiss_index_path: str = Field(default="data/faiss_index", alias="FAISS_INDEX_PATH")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Demo timing (seconds between actions in demo mode)
    demo_action_delay: float = Field(default=1.5, alias="DEMO_ACTION_DELAY")

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}


# Singleton settings instance
settings = Settings()
