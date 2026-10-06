from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-change-me"

# Ready-made endpoints for the free AI options. All of them speak the OpenAI-style
# /chat/completions API with tool calling, so one client works for every provider.
AI_PRESETS = {
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "model": ""},
    "ollama": {"base_url": "http://localhost:11434/v1", "model": "llama3.1"},
    "huggingface": {"base_url": "https://router.huggingface.co/v1", "model": ""},
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite:///./crunch.db"
    jwt_secret: str = DEV_SECRET
    jwt_expire_minutes: int = 720
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    shop_timezone: str = "Asia/Kolkata"

    # AI assistant: "basic" works offline with no key. Set to openrouter, ollama,
    # huggingface or custom (with AI_BASE_URL) to use a language model.
    ai_provider: str = "basic"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_timeout_seconds: float = 45.0

    # First start on a fresh database: create this owner account if nobody exists yet.
    # Remove OWNER_PASSWORD from your host's settings after the first deploy.
    owner_email: str = ""
    owner_password: str = ""
    owner_name: str = "Owner"

    # Online ordering limits per phone/IP, to stop junk orders
    online_orders_per_window: int = 5
    online_order_window_seconds: int = 600

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    def ai_endpoint(self) -> tuple[str, str, str] | None:
        """(base_url, api_key, model) for the configured model, or None for basic mode."""
        provider = self.ai_provider.lower().strip()
        if provider in ("", "basic", "none"):
            return None
        preset = AI_PRESETS.get(provider, {"base_url": "", "model": ""})
        base_url = (self.ai_base_url or preset["base_url"]).rstrip("/")
        model = self.ai_model or preset["model"]
        api_key = self.ai_api_key or ("ollama" if provider == "ollama" else "")
        if not base_url or not model:
            return None
        return base_url, api_key, model


@lru_cache
def get_settings() -> Settings:
    return Settings()
