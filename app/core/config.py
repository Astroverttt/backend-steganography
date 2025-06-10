# app/core/config.py
import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# load_dotenv() # Anda bisa memindahkannya ke main.py jika ingin memastikan semua env dimuat diawal

# Ini harus mulai dari kolom pertama, TANPA SPASI DI DEPAN
class Settings(BaseSettings):
    # Ini harus terindentasi (misalnya 4 spasi)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Ini juga harus terindentasi dengan level yang sama
    PROJECT_NAME: str = "Blog"
    PROJECT_VERSION: str = "1.0.0"

    DATABASE_URL: str = Field(..., env="DBTAURL")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60 * 24, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    SMTP_SERVER: str = Field(..., env="SMTP_SERVER")
    SMTP_PORT: int = Field(..., env="SMTP_PORT")
    EMAIL_SENDER: str = Field(..., env="EMAIL_SENDER")
    EMAIL_PASSWORD: str = Field(..., env="EMAIL_PASSWORD")

# Ini juga harus mulai dari kolom pertama, TANPA SPASI DI DEPAN
settings = Settings()