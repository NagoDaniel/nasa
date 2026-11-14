from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # backend/.env, whatever the working directory. Read once at startup: restart the server
    # after editing it (uvicorn --reload only watches .py files).
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_prefix="S2F_", extra="ignore")

    data_dir: Path = BASE_DIR / "data"
    db_url: str = f"sqlite:///{BASE_DIR / 'app.db'}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Re-read JSON files when they change on disk (handy while iterating on data).
    json_hot_reload: bool = True

    # --- AI assistant (app/assistant). The key stays on the server; without it the assistant
    # still answers navigation / help requests with deterministic code.
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_thinking_budget: int = 0  # 0 = no thinking (fast, cheap); -1 = model default
    assistant_max_chars: int = 500  # per user message
    assistant_max_history: int = 6  # previous turns sent back to the model
    rate_ip_per_min: int = 6  # chat messages per client IP
    rate_ip_per_day: int = 60
    rate_global_llm_per_day: int = 500  # messages that reach Gemini, all users together (UTC day)
    llm_concurrency: int = 2  # Gemini calls in flight at once
    llm_timeout_s: float = 20.0
    llm_max_rounds: int = 4  # tool-calling rounds per message
    trust_forwarded_for: bool = False  # only behind a reverse proxy you control
    # HMAC key that signs assistant replies so a client cannot forge earlier assistant turns.
    # Random per process when unset (history from before a restart is then simply dropped).
    assistant_secret: SecretStr | None = None

    # --- Drawn fields (app/field). HLS needs an Earthdata login: ~/.netrc (machine
    # urs.earthdata.nasa.gov) or a bearer token here. Sentinel-2 needs no account.
    earthdata_token: SecretStr | None = None
    rate_field_jobs_per_min: int = 4  # imagery jobs per client IP
    rate_field_jobs_per_day: int = 60
    max_saved_fields: int = 300


settings = Settings()
