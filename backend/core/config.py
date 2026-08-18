import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Base paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

# Load environment variables from root .env and backend .env
env_path = os.path.join(ROOT_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
backend_env = os.path.join(BACKEND_DIR, ".env")
if os.path.exists(backend_env):
    load_dotenv(backend_env, override=True)


class Settings(BaseSettings):
    # Supabase (Loaded from environment / .env, defaulting to cjzsyyzjcendnldhxfdn)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://cjzsyyzjcendnldhxfdn.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNqenN5eXpqY2VuZG5sZGh4ZmRuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcwMjkxNDgsImV4cCI6MjEwMjYwNTE0OH0.BFZ8moRHnu6-JfzDdW3ildICkv2oDYy4CCbvfupHcAM")

    # Groq LLM
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # SMTP Email Credentials Configuration (Loaded directly from environment / .env file)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "727823tuad122@skct.edu.in")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "kqyf yrhd jgpo pspb")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", "727823tuad122@skct.edu.in"))
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", os.getenv("SMTP_USER", "727823tuad122@skct.edu.in"))
    APP_URL: str = os.getenv("APP_URL", "http://localhost:5173")

    BASE_DIR: str = BACKEND_DIR

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
