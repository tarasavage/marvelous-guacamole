from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    data_dir: str = "./data"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
