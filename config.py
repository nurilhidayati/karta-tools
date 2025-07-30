import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # Database Configuration
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT: str = os.getenv("DATABASE_PORT", "5432")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "postgres")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "postgres")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "Nuril123!")

    # FastAPI Configuration
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # OpenAI Configuration for Chatbot
    OPENAI_API_KEY: Optional[str] = (
        os.getenv("OPENAI_API_KEY") or 
        os.getenv("DECLARAI_OPENAI_API_KEY") or
        "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"
    )
 
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

settings = Settings() 