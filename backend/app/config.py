"""
Central place for reading environment/config values.
Everything here is read once at startup so a missing .env value fails loudly
and early, instead of causing a confusing error halfway through a request.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy backend/.env.example to backend/.env and fill it in."
        )
    return value


class Settings:
    # These are only required once you actually call an endpoint that needs them
    # (see require_* helpers below) -- this lets the server boot even before you've
    # added every key, so you can test pieces incrementally.
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "resumes")
    STAFF_NAMES = [
        name.strip()
        for name in os.getenv("STAFF_NAMES", "").split(",")
        if name.strip()
    ]

    @staticmethod
    def require_openai_key() -> str:
        return _require("OPENAI_API_KEY")

    @staticmethod
    def require_supabase() -> tuple[str, str]:
        return _require("SUPABASE_URL"), _require("SUPABASE_SERVICE_ROLE_KEY")


settings = Settings()
