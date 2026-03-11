from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WT_")

    config_path: str = "app/config/services.yaml"
    slack_webhook_url: str | None = None
    slack_cooldown_minutes: int = 15
    log_level: str = "INFO"
