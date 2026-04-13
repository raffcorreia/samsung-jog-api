"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from pi_deck.services.deck_control import DeckControlService


def get_deck(request: Request) -> DeckControlService:
    return request.app.state.deck
