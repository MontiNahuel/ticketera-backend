from typing import List, Any
import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Tickets API"
    MONGO_URI: str = "mongodb://localhost:27017/tickets_db"
    MONGO_DB_NAME: str = "tickets_db"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Límites de Seguridad y Rate Limiting
    MAX_DAILY_TICKETS_PER_EMAIL: int = 8
    TICKET_CREATION_COOLDOWN_SECONDS: int = 60
    ADMIN_EMAILS: List[str] = []

    @field_validator("ADMIN_EMAILS", mode="before")
    @classmethod
    def parse_admin_emails(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                try:
                    return json.loads(v_trimmed)
                except Exception:
                    pass
            return [email.strip() for email in v_trimmed.split(",") if email.strip()]
        return v or []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
