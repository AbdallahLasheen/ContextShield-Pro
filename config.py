"""
ContextShield — Unified Configuration
======================================
Central settings for all system components:
  - FastAPI Backend  (api.py)
  - Streamlit Frontend  (app_streamlit_v2.py)
  - Telegram Bot  (telegram_bot.py)

All values are read from environment variables with safe local defaults.

Usage:
    from config import settings
    print(settings.API_URL)       # http://localhost:8000
    print(settings.ANALYZE_ENDPOINT)  # http://localhost:8000/analyze
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # ── FastAPI ───────────────────────────────────────────────────────────────
    API_HOST: str  = field(default_factory=lambda: os.getenv("API_HOST", "localhost"))
    API_PORT: int  = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    API_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("API_TIMEOUT", "30")))

    # ── Telegram ──────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )

    # ── Risk Thresholds ───────────────────────────────────────────────────────
    FLAG_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("FLAG_THRESHOLD", "0.55"))
    )

    # ── Derived Properties ────────────────────────────────────────────────────
    @property
    def API_URL(self) -> str:
        return f"http://{self.API_HOST}:{self.API_PORT}"

    @property
    def ANALYZE_ENDPOINT(self) -> str:
        return f"{self.API_URL}/analyze"

    @property
    def HEALTH_ENDPOINT(self) -> str:
        return f"{self.API_URL}/health"


# Singleton — import this everywhere
settings = Settings()
