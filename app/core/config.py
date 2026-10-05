import json
import os
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])
    ENV: str = "development"
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_BUCKET_NAME: str
    EMAIL: str
    EMAIL_PASSWORD: str
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    FRONTEND_URL: str
    SCHOOL_ADMIN_FRONTEND_URL: str = ""
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return ["*"]
        if isinstance(value, str):
            stripped = value.strip()
            origins = (
                json.loads(stripped)
                if stripped.startswith("[")
                else stripped.split(",")
            )
        elif isinstance(value, (list, tuple, set)):
            origins = list(value)
        else:
            raise ValueError("CORS_ORIGINS must be a list or comma-separated string")

        normalized: list[str] = []
        seen: set[str] = set()
        for origin in origins:
            item = str(origin).strip().strip('"').strip("'")
            if not item:
                continue
            if item != "*":
                item = item.rstrip("/")
            if item not in seen:
                seen.add(item)
                normalized.append(item)
        return normalized or ["*"]

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


settings = Settings()

# Prisma reads DATABASE_URL from the process environment, not from Settings.
os.environ["DATABASE_URL"] = settings.DATABASE_URL
