from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    business_timezone: str = "Asia/Colombo"  # defines the "business day" for daily summaries


settings = Settings()
