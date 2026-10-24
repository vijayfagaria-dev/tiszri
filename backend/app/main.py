"""Application factory and the ASGI entry point (`app.main:app`)."""

import logging

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.middleware import add_middleware
from app.api.routes import router
from app.clients.base import DataSource
from app.clients.cache import CachedSource
from app.clients.elexon import ElexonClient
from app.clients.recorded import RecordedSource
from app.core.config import Settings, get_settings
from app.services.replay_service import ReplayService


def create_app(settings: Settings | None = None, source: DataSource | None = None) -> FastAPI:
    """Build the app. Tests pass their own settings and data source."""
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    elexon_client = None
    if source is None:
        if settings.source_mode == "fixtures":
            source = RecordedSource(settings.fixtures_dir)
        else:
            source = elexon_client = ElexonClient(settings)
        if settings.cache_enabled:
            source = CachedSource(source, settings.cache_ttl_s)

    app = FastAPI(
        title="Wind Forecast Intelligence API",
        version="1.0.0",
        # The contract lives in contracts/openapi.yaml; the generated docs are not exposed.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.elexon_client = elexon_client
    app.state.replay_service = ReplayService(source, settings.forecast_lookback_days)

    register_error_handlers(app)
    add_middleware(app, settings.rate_limit_per_minute)
    app.include_router(router)
    return app


app = create_app()
