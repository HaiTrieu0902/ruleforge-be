from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    # File upload settings
    max_file_size: int = 10485760  # 10MB
    upload_folder: str = "uploads"
    allowed_extensions: List[str] = ["pdf", "docx", "txt"]
    
    # Database settings - these will be loaded from .env file
    database_url: str
    
    # Database connection settings - these will be loaded from .env file
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    
    # OpenAI settings - these will be loaded from .env file
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    
    # Google Cloud AI settings - these will be loaded from .env file
    google_api_key: str = ""
    google_model: str = "gemini-pro"
    
    # Hugging Face model settings
    hf_model_summarization: str = "facebook/bart-large-cnn"
    hf_model_text_generation: str = "microsoft/DialoGPT-medium"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()