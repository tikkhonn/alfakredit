from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./cabinet.db"
    jwt_secret: str = "hackathon-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 12
    key_rate: float = 16.5
    sign_code: str = "123456"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"


settings = Settings()
