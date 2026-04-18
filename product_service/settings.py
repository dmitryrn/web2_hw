from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://shop:shop@localhost:5433/products"
    order_service_url: str = "http://localhost:8001"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
