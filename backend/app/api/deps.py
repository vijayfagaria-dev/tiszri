"""Dependencies injected into route handlers."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings
from app.services.replay_service import ReplayService


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_replay_service(request: Request) -> ReplayService:
    service: ReplayService = request.app.state.replay_service
    return service


SettingsDep = Annotated[Settings, Depends(get_settings)]
ReplayServiceDep = Annotated[ReplayService, Depends(get_replay_service)]
