from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    product_service_url: str
    jwt_secret: str = Field(min_length=32)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
