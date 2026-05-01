"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.display_service import DisplayService
from pi_deck.services.recordings import RecordingService
from pi_deck.services.strip_driver import StripDriver
from pi_deck.services.system_service import SystemService


def get_deck(request: Request) -> DeckControlService:
    return request.app.state.deck


def get_recordings(request: Request) -> RecordingService:
    return request.app.state.recordings


def get_display(request: Request) -> DisplayService:
    return request.app.state.display


def get_system(request: Request) -> SystemService:
    return request.app.state.system


def get_strip(request: Request) -> StripDriver:
    return request.app.state.strip
