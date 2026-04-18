"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.recordings import RecordingService


def get_deck(request: Request) -> DeckControlService:
    return request.app.state.deck


def get_recordings(request: Request) -> RecordingService:
    return request.app.state.recordings
