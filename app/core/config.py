from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Enterprise HR AI Assistant"
    api_version: str = "v1"
    secret_key: str = os.getenv("HR_AI_SECRET_KEY", "change-me-for-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    policy_dataset_path: Path = Path(__file__).resolve().parents[1] / "data" / "hr_policies.json"
    event_log_path: Path = Path(__file__).resolve().parents[2] / "data" / "events.jsonl"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
