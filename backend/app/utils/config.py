from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    cors_origins: str = "http://localhost:5173"
    distance_provider: str = "haversine"
    amap_web_service_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()


def get_distance_provider():
    from app.utils.distance import get_provider
    return get_provider(settings.distance_provider, settings.amap_web_service_key)
