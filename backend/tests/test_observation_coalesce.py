"""Coalescing for thread → asyncio observation scheduling (no RPi.GPIO required)."""

from __future__ import annotations

from pi_deck.services.observation_coalesce import CoalesceGate


def test_coalesce_gate_single_thread_requests_coalesce() -> None:
    g = CoalesceGate()
    assert g.request_from_thread() is True
    assert g.request_from_thread() is False
    assert g.should_continue_after_round() is True
    assert g.should_continue_after_round() is False


def test_coalesce_gate_resets_worker_after_last_round() -> None:
    g = CoalesceGate()
    assert g.request_from_thread() is True
    assert g.should_continue_after_round() is False


def test_coalesce_gate_reset_clears_pending() -> None:
    g = CoalesceGate()
    assert g.request_from_thread() is True
    assert g.request_from_thread() is False
    g.reset()
    assert g.request_from_thread() is True


def test_coalesce_many_requests_while_worker_running_one_extra_round() -> None:
    """IRQ storm while the async worker is 'in flight' collapses to one pending bit."""
    g = CoalesceGate()
    assert g.request_from_thread() is True
    for _ in range(50):
        assert g.request_from_thread() is False
    assert g.should_continue_after_round() is True
    assert g.should_continue_after_round() is False
