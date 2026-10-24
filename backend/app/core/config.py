"""Application settings, read from environment variables (or a local .env file)."""

from datetime import date, time
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_UPSTREAM_HOSTS = {"data.elexon.co.uk"}
DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "source"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "preview", "production"] = "development"
    log_level: str = "INFO"

    # Where data comes from: the live Elexon API, or recorded fixtures (never in production).
    source_mode: Literal["http", "fixtures"] = "http"
    fixtures_dir: Path = DEFAULT_FIXTURES_DIR
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    http_connect_timeout_s: float = 3.0
    http_read_timeout_s: float = 10.0
    upstream_max_retries: int = 1
    upstream_retry_backoff_s: float = 0.5
    max_upstream_response_bytes: int = 10 * 1024 * 1024

    cache_enabled: bool = True
    cache_ttl_s: int = 6 * 3600
    browser_max_age_s: int = 300
    cdn_max_age_s: int = 24 * 3600
    cdn_stale_while_revalidate_s: int = 7 * 24 * 3600
    rate_limit_per_minute: int = 60

    # Analysis rules.
    supported_date_from: date = date(2026, 1, 1)
    supported_date_to: date = date(2026, 2, 1)
    summary_default_from: date = date(2026, 1, 2)
    summary_default_to: date = date(2026, 2, 1)
    default_cutoff_day_offset: int = -1
    default_cutoff_local_time: time = time(9, 0)
    cutoff_min_day_offset: int = -7
    cutoff_max_day_offset: int = 2
    forecast_lookback_days: int = 4
    windfor_unit_status: Literal["VERIFIED", "PENDING_VERIFICATION"] = "VERIFIED"

    @model_validator(mode="after")
    def check_safety(self) -> "Settings":
        if self.app_env == "production" and self.source_mode == "fixtures":
            raise ValueError("Recorded fixtures cannot be used as the data source in production")
        host = urlparse(self.elexon_base_url).hostname
        if host not in ALLOWED_UPSTREAM_HOSTS:
            raise ValueError(f"Upstream host {host!r} is not allowed")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
