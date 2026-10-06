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

    # Abuse protection for the whole API
    api_requests_per_minute: int = 600      # per IP address
    max_request_bytes: int = 256 * 1024     # no legitimate request is bigger
    # API docs (/api/docs) are always on for this computer; set true to open them to everyone
    api_docs_public: bool = False
    # Extra origins the websites may call, when the API lives on another domain (CSP connect-src)
    csp_connect_extra: str = ""

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


def config_problems(s: Settings) -> tuple[list[str], list[str]]:
    """(errors that stop the server, warnings to fix) for the current environment variables."""
    errors: list[str] = []
    warnings: list[str] = []
    weak_secret = s.jwt_secret == DEV_SECRET or len(s.jwt_secret) < 32
    if s.is_production:
        if weak_secret:
            errors.append("JWT_SECRET must be a random value of at least 32 characters. "
                          'Make one with: python -c "import secrets; print(secrets.token_urlsafe(48))"')
        if "*" in s.cors_list:
            errors.append("CORS_ORIGINS can't be * in production. List your website addresses instead.")
        if any(o.startswith("http://") and "localhost" not in o and "127.0.0.1" not in o for o in s.cors_list):
            warnings.append("CORS_ORIGINS has a plain http:// address. Use https:// addresses in production.")
        if s.database_url.startswith("sqlite"):
            warnings.append("Production is using SQLite. Free hosts wipe their disk on redeploy; use Supabase or Neon.")
        if s.api_docs_public:
            warnings.append("API_DOCS_PUBLIC is on, so anyone can browse your API reference.")
    elif weak_secret:
        warnings.append("JWT_SECRET is the development default. start.bat writes a random one to backend/.env.")
    provider = s.ai_provider.lower().strip()
    if provider not in ("", "basic", "none"):
        if not s.ai_endpoint():
            warnings.append("AI_PROVIDER is set but AI_MODEL (or AI_BASE_URL) is missing, so the assistant stays in basic mode.")
        if provider in ("openrouter", "huggingface") and not s.ai_api_key:
            warnings.append(f"AI_PROVIDER is {provider} but AI_API_KEY is empty.")
    return errors, warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()
