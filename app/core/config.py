from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Blog"
    PROJECT_VERSION: str = "1.0.0"

    DATABASE_URL: str = Field(..., env="DBTAURL")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60 * 24, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    MAIL_USERNAME: str = Field(..., env="MAIL_USERNAME")
    MAIL_PASSWORD: str = Field(..., env="MAIL_PASSWORD")
    MAIL_FROM: str = Field(..., env="MAIL_FROM")
    MAIL_PORT: int = Field(..., env="MAIL_PORT")
    MAIL_SERVER: str = Field(..., env="MAIL_SERVER")
    MAIL_STARTTLS: bool = Field(True, env="MAIL_STARTTLS")
    MAIL_SSL_TLS: bool = Field(False, env="MAIL_SSL_TLS")

settings = Settings()  # ← ini cukup dideklarasikan di akhir, tanpa diimpor lagi
