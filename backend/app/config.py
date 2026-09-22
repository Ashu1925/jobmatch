from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    serpapi_api_key: str
    searchapi_api_key: str
    database_url: str
    jwt_secret_key: str
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  
