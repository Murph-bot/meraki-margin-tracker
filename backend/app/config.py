import os
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def database_path_for_env(
    volume_mount: str | None = None,
    fallback: str = "data/meraki.db",
) -> str:
    mount = volume_mount if volume_mount is not None else os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    if mount:
        return str(Path(mount) / "meraki.db")
    return fallback


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_path: str = "data/meraki.db"
    secret_key: str
    stripe_api_key: str = ""
    viva_api_key: str = ""
    viva_client_id: str = ""
    frontend_url: str = "http://localhost:5173"
    sync_interval_hours: int = 24

    @model_validator(mode="before")
    @classmethod
    def prefer_railway_volume(cls, data):
        if isinstance(data, dict) or data is None:
            incoming = dict(data or {})
            mount = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
            if mount:
                incoming["database_path"] = database_path_for_env(mount)
            return incoming
        return data


settings = Settings()
