from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str = "https://lsqpkqflqhwlcvtkoowr.supabase.co"
    SUPABASE_KEY: str = "sb_publishable_FTmqAvJnNEx36CvCii16zQ_gK1s_P7i"

    # Groq LLM
    GROQ_API_KEY: str = ""

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
