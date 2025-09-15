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
    
    # Database settings
    database_url: str = "postgresql://postgres:040202005173@localhost:5432/ruleforge"
    
    # Database connection settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ruleforge"
    db_user: str = "postgres"
    db_password: str = "040202005173"
    
    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    
    # Google Cloud AI settings
    google_api_key: str = ""
    google_model: str = "gemini-pro"
    
    # Hugging Face model settings
    hf_model_summarization: str = "facebook/bart-large-cnn"
    hf_model_text_generation: str = "microsoft/DialoGPT-medium"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()