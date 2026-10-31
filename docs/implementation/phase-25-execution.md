# Phase 25 Execution Record

## Purpose

Track **Phase 25: Custom LED Communication Receiver and Monitor UI** per the [Implementation Plan](./plan.md).

## Status

**Planned.**

The firmware-side handoff defines a receiver-first milestone on the conditioned `KEY_LED` GPIO. This phase will implement raw transition capture and the operator-facing communication monitor before freezing any production protocol constants or adding structured joystick-bus transmission.

## Working goal

Capture every accepted `KEY_LED` transition with its physical level and monotonic timestamp, make captures observable and replayable without silent loss, characterize the monitor-to-deck timing boundary, and replace the Calendar and Notes placeholders with one large LED communication monitor while preserving ordinary LED semantics.

## Initial checklist

- Confirm the conditioned GPIO observation point remains electrically receive-only.
- Record the GPIO clock resolution, initial physical level, polarity configuration, filter setting, and buffer capacity with every capture.
- Add a raw callback-time timestamp/level path independent of observation coalescing.
- Add bounded buffering and explicit rejected-glitch and overrun counters.
- Define the versioned edge-log schema and deterministic replay path.
- Add capture lifecycle/status/export APIs and bounded batched WebSocket delivery.
- Add interval/jitter statistics and the configurable decoder/acquisition interfaces.
- Add differential-Manchester candidate decoding without freezing timing or framing constants.
- Replace Calendar and Notes on the home page with the large communication-monitor widget.
- Preserve the small JOG-adjacent semantic LED and existing `bus/led_changed` behavior.
- Add backend, frontend, replay, garbage-rejection, and regression tests.
- Run the firmware speed ladder beginning at the 200 ms baseline and retain raw evidence.
- Record the reliable boundary and choose no production timing without a long zero-error run and margin.
- Run and record the host health snapshot before closing the phase.

## Protocol values intentionally unresolved

- production half-bit duration and tolerance
- training length and sync word
- header field widths and maximum payload
- CRC polynomial and initialization parameters
- message numeric identifiers
- future joystick-bus input alphabet, resistance values, framing, and timing

## Evidence log

_Add dated implementation, test, deployment, capture, and characterization evidence here._

## Host health snapshot

_Required before closing this phase. Paste the default text output from `python3 scripts/pi-deck-host-health.py`._
