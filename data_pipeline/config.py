"""Typed configuration, read once from `.env`.

`docs/conventions.md` forbids scattering `os.environ` lookups through modules. Every setting
the pipeline needs is declared here with a type, so a missing or malformed value fails
immediately with a clear message instead of surfacing as an obscure error deep inside a
stage that has already spent Earth Engine quota.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives in data_pipeline/, so the repo root is one level up. Deriving it from
# __file__ rather than the working directory means stages behave the same whether they are
# launched from the repo root, from notebooks/, or by a scheduler.
REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Pipeline settings. Field names match `.env` keys case-insensitively."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        # .env also carries backend, LLM and frontend keys this package has no business
        # reading. Ignoring them keeps the pipeline's config surface honest.
        extra="ignore",
    )

    # Empty default, not required — the same reasoning as gemini_api_key below: the deployed
    # backend (Phase 6) shares this same Settings class but never touches Earth Engine, so it
    # must still boot without this set. A pipeline stage that actually calls ee.Initialize()
    # with an empty project id fails loudly at that call, not silently — the right place for
    # this to surface is point-of-use, same as every other Phase 4+ credential here.
    gee_project_id: str = Field(default="", description="Cloud project registered for Earth Engine")
    data_dir: Path = Field(default=Path("data"))
    model_dir: Path = Field(default=Path("models"))

    # --- Backend (Phase 3+) ---
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="http://localhost:5173")  # comma-separated

    # --- LLM / agents (Phase 4+) ---
    # Empty default, not required: pipeline and backend tests must still run on a fresh
    # clone with no LLM key configured (docs/conventions.md — every service degrades, never
    # hard-fails, when a free-tier credential is missing).
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-flash-latest")
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    chroma_dir: Path = Field(default=Path("backend/rag/chroma_db"))

    # --- Supabase (Phase 6+) ---
    # Empty defaults for the same reason as gemini_api_key above: a fresh clone with no
    # Supabase project yet must still boot and run every non-auth endpoint.
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    supabase_service_key: str = Field(default="")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("data_dir", "model_dir", "chroma_dir")
    @classmethod
    def _resolve_against_repo_root(cls, value: Path) -> Path:
        """`.env` ships relative paths like `./data`, only correct from the repo root."""
        return value if value.is_absolute() else (REPO_ROOT / value).resolve()

    @property
    def raw_dir(self) -> Path:
        """Unmodified source downloads. Regenerable, gitignored."""
        return self.data_dir / "raw"

    @property
    def interim_dir(self) -> Path:
        """Per-stage intermediates, so a failed stage does not force a full rebuild."""
        return self.data_dir / "interim"

    @property
    def processed_dir(self) -> Path:
        """Pipeline outputs the API and the models read."""
        return self.data_dir / "processed"

    def ensure_dirs(self) -> None:
        for directory in (self.raw_dir, self.interim_dir, self.processed_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached so `.env` is parsed once per process, not once per import site."""
    return Settings()
