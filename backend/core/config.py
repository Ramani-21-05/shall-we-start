from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Supabase (from .env or env vars)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://cjzsyyzjcendnldhxfdn.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNqenN5eXpqY2VuZG5sZGh4ZmRuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcwMjkxNDgsImV4cCI6MjEwMjYwNTE0OH0.BFZ8moRHnu6-JfzDdW3ildICkv2oDYy4CCbvfupHcAM")

    # Groq LLM (read from .env or Render environment variable)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # SMTP Email Credentials Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "727823tuad122@skct.edu.in"
    SMTP_PASSWORD: str = "kqyf yrhd jgpo pspb"
    SMTP_FROM_EMAIL: str = "noreply@pharmacast.com"
    APP_URL: str = "http://localhost:5173"

    # Base paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
