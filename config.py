"""All settings live here and come from environment variables / .env.
Business thresholds (85 %, N20M) are configuration, never hard-coded in logic."""
import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    COMPANY_NAME = os.getenv("COMPANY_NAME", "Zigbe Nigeria Limited")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "instance/fco_bonus.db")
    TIMEZONE = os.getenv("TIMEZONE", "Africa/Lagos")          # WAT
    CALC_HOUR = int(os.getenv("CALC_HOUR", "12"))            # 12 PM
    MIN_BONUS_PERCENT = Decimal(os.getenv("MIN_BONUS_PERCENT", "85"))
    MIN_DISBURSEMENT = Decimal(os.getenv("MIN_DISBURSEMENT", "20000000"))
    DATA_SOURCE = os.getenv("DATA_SOURCE", "local")
    ENABLE_SCHEDULER = _flag("ENABLE_SCHEDULER")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _flag("SESSION_COOKIE_SECURE")

    @staticmethod
    def db_path() -> str:
        p = Path(os.getenv("DATABASE_PATH", "instance/fco_bonus.db"))
        return str(p if p.is_absolute() else BASE_DIR / p)
