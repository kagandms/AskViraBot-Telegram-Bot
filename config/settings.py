from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Required Fields (Will fail if missing in .env)
    TELEGRAM_BOT_TOKEN: SecretStr
    SUPABASE_URL: str
    SUPABASE_KEY: SecretStr

    # Optional Fields
    OPENWEATHERMAP_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    WEB_APP_BASE_URL: str | None = None
    ALLOW_LOCAL_WEBAPP_BYPASS: bool = False

    # Defaults
    TIMEZONE: str = "Europe/Istanbul"
    BOT_NAME: str = "Vira"
    NOTES_PER_PAGE: int = 5
    AI_DAILY_LIMIT: int = 30

    # Complex parsing handled via property or validator,
    # but for simple CSV string in env, we can just read as str and parse.
    ADMIN_IDS: str = ""

    @property
    def get_admin_ids(self) -> list[int]:
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip().isdigit()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars
    )


try:
    settings = Settings()
except Exception as e:
    print(f"❌ Kritisel Konfigürasyon Hatası: {e}")
    # In a real app we might raise, but here we let it crash naturally or handle gracefully
    raise e
