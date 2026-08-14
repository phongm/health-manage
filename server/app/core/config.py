from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "health-manage"
    debug: bool = False
    secret_key: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/health_manage"

    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_mock_login: bool = True
    wechat_mock_openid: str = "dev_openid_001"


settings = Settings()
