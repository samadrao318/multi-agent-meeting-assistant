"""
Configuration settings using Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str = "gpt-4.1-mini"
    azure_openai_api_version: str = "2024-02-15-preview"
    
    # Google APIs (optional)
    google_calendar_credentials_path: str = "credentials.json"
    google_gmail_credentials_path: str = "credentials.json"
    
    # Data
    csv_file_path: str = "data/contacts.csv"
    
    # Agent settings
    temperature: float = 0.7
    max_tokens: int = 1500
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()