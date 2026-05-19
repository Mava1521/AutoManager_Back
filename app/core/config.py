from typing import List
from pydantic import computed_field, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Configuración del Modelo (Pydantic V2 Standard) ──────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False  # Tolera variaciones de mayúsculas en el archivo .env
    )

    # ── Base de Datos ────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./automanager.db"

    # ── Seguridad y JWT ──────────────────────────────────────────────────────
    secret_key: str                   
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ── CORS e Integraciones ─────────────────────────────────────────────────
    # Cadena separada por comas en el .env. Ejemplo: "http://localhost:5173,http://localhost:3000"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    frontend_url: str = "http://localhost:5173"

    # ── Infraestructura de Correo (Gmail SMTP) ──────────────────────────────
    # Validadas de forma estricta para garantizar la operatividad del AutoBot
    gmail_user: EmailStr              # Valida formato real de correo
    gmail_app_password: str           # Contraseña de 16 caracteres de Google
    
    @computed_field
    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @computed_field
    @property
    def email_display_name(self) -> str:
        return f"AutoManager <{self.gmail_user}>"


# Instancia única global (Patrón Singleton implícito)
settings = Settings()