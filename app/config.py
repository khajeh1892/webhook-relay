from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DB
    DATABASE_URL: str = "postgresql+psycopg2://kataeinnorabadi@localhost:5432/relay"

    # Auth
    API_KEY_HEADER: str = "X-API-Key"
    APP_SECRET: str = "change-me"

    # Celery / Redis (برای tasks.py لازم است)
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
