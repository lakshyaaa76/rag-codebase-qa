from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    github_token: str
    grok_api_key: str
    grok_model: str = "grok-3"
    grok_max_tokens: int = 1024
    grok_temperature: float = 0.2
    retrieval_top_k: int = 5
    max_files_per_repo: int = 500
    allowed_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file="../.env",        # single root .env â€” not backend/.env
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

settings = Settings()
