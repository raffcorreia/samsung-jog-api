# Phase 25 Execution Record

## Purpose

Track **Phase 25: Custom LED Communication Receiver and Monitor UI** per the [Implementation Plan](./plan.md).

## Status

**In progress.** Implementation began 2026-10-31. Local decoder, API, frontend, and regression validation pass; live hardware validation is pending because the deck host is currently unreachable over SSH.

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

- 2026-10-31: Added callback-time physical GPIO level capture using `time.monotonic_ns()`, independent of the coalesced semantic observation path.
- 2026-10-31: Added bounded raw-edge and WebSocket queues, glitch and overrun counters, timing statistics, JSON export/replay, and start/stop/clear/status APIs.
- 2026-10-31: Added the polarity-independent 1007.8-compatible decoder for `FFFF 2DD4`, version/type `0x11`, sequence, layout/inputs, and CRC-8 polynomial `0x07`.
- 2026-10-31: Golden PBP and PIP frames decode successfully after leading garbage and under polarity inversion. Corrupt CRC and truncated-frame tests reject the input.
- 2026-10-31: Replaced Calendar and Notes on the home screen with the raw waveform, capture health, timing statistics, valid/missing frame counts, decoded state, export, and replay controls. The small semantic LED remains beside the JOG pad.
- 2026-10-31: Focused backend validation: 27 tests passed. Focused frontend validation: 4 tests passed. Production frontend build passed.
- 2026-10-31: Full backend collection remains blocked by the pre-existing `test_deploy_version.py` import of missing `_build_version`/`_read_deploy_counter`; full frontend run retains pre-existing SettingsPage mock failures. Neither failure is in the Phase 25 paths.
- 2026-10-31: Live deployment/1007.7 capture could not run because SSH timed out to both previously documented deck addresses, `10.0.0.11` and `10.0.0.116`.
- 2026-10-31: Deployed `0.1.12+r92` to the live `pi-deck5` host. The API and updated oscilloscope client are active.
- 2026-10-31: Added a bounded 4,096-edge browser history, fixed 0–1 level scale, 100 ms–60 s time zoom, pause/resume, clear, older/newer panning while paused, and return-to-live controls.
- 2026-10-31: Live GPIO capture is interrupt-driven and reports zero overruns. A 986-interval sample had a 21.1 ms minimum and roughly 790 ms median; it contained no interval below 15 ms, and replay across candidate 5–50 ms half-bit periods decoded no frame. A fresh post-deployment sample likewise had a 36.8 ms minimum. The client is therefore receiving transitions, but the conditioned GPIO input does not yet contain the specified dense 10/20 ms waveform.
- 2026-11-02: Updated the decoder for 1007.9 shared-sequence STATE (`0x11`) and LEVEL (`0x12`) frames, including CRC-valid unknown-type retention. The UI now updates immediately from validated frame events while displaying latest message and latest known STATE separately.
- 2026-11-02: Added 30 ms semantic LED classification: protocol bursts remain raw oscilloscope traffic, stable levels produce ordinary LED on/off events, valid messages produce one decoded log entry, and invalid bursts produce one summary.

## Host health snapshot

_Required before closing this phase. Paste the default text output from `python3 scripts/pi-deck-host-health.py`._
