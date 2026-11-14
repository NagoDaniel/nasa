from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="S2F_")

    data_dir: Path = BASE_DIR / "data"
    db_url: str = f"sqlite:///{BASE_DIR / 'app.db'}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Re-read JSON files when they change on disk (handy while iterating on data).
    json_hot_reload: bool = True


settings = Settings()
