"""
CrisisWatch Configuration Settings
Loads environment variables and provides typed configuration.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Provider Keys
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    
    # Search & Fact-Check API Keys
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    google_factcheck_api_key: str = Field(default="", alias="GOOGLE_FACTCHECK_API_KEY")
    newsapi_key: str = Field(default="", alias="NEWSAPI_KEY")
    
    # Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_language: Literal["en", "hi"] = Field(default="en", alias="DEFAULT_LANGUAGE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def has_gemini(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.gemini_api_key and self.gemini_api_key != "your_gemini_api_key_here")
    
    @property
    def has_tavily(self) -> bool:
        """Check if Tavily API key is configured."""
        return bool(self.tavily_api_key and self.tavily_api_key != "your_tavily_api_key_here")
    
    @property
    def has_google_factcheck(self) -> bool:
        """Check if Google Fact Check API key is configured."""
        return bool(self.google_factcheck_api_key and self.google_factcheck_api_key != "your_google_factcheck_api_key_here")
    
    @property
    def has_newsapi(self) -> bool:
        """Check if NewsAPI key is configured."""
        return bool(self.newsapi_key and self.newsapi_key != "your_newsapi_key_here")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
