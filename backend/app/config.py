from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Incident Tracker API"
    app_version: str = "dev"
    environment: str = "local"
    site_title: str = "Incident Tracker"
    database_url: str = "postgresql+psycopg://incidents:incidents@localhost:5432/incidents"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
