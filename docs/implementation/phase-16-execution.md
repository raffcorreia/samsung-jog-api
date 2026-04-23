# Phase 16 Execution Record

## Purpose

Track **Phase 16: Recording and Replay Subsystem** per [Implementation Plan](./plan.md).

## Status

**Started:** 2026-04-16.

**Parked:** 2026-04-20 — hardware access unavailable for live validation.

**Closed:** 2026-04-23.

## Working Goal

Add the tooling needed to record, store, replay, edit, and promote monitor interaction sequences.
Provide a complete recording workspace UI within the Phase 13 popup rules, fitting the fixed 1280×800 kiosk layout.

## Implementation Summary

### Backend

- `backend/src/pi_deck/models/recordings.py` — canonical domain models:
  - `RecordingFile` (V1 format, `extra="ignore"` for forward compatibility), `RecordingEvent` union (`hold`, `release`, `delay`, `led`, `wait_led`, `wait_ddc`), `RecordingSummary`, `RecordingStateOut`, `RecordingLibraryOut`.
  - `recording_duration_ms()` — computes total duration from `delay` events only; never stored in the file.
  - `ws_recording_state()` / `ws_recording_library()` — WS broadcast helpers.
- `backend/src/pi_deck/storage/recordings.py` — `RecordingStore`:
  - Writable base directory (env override, fallback to `~/.local/share/pi-deck/recordings`).
  - `write_new()` with suffix-deduplicated filenames.
  - `rename()` with file rename + JSON body update.
  - `replace()` — replaces body and bumps `updated_at` without changing filename.
  - `path_for_download()` for streaming download.
- `backend/src/pi_deck/services/recordings.py` — `RecordingService`:
  - `start_recording()` / `stop_recording()` — captures observation-bus events (hold, release, LED) after start; ignores pre-held inputs; skips leading setup delay; auto-saves with timestamp filename on stop.
  - `play_recording()` / `stop_playback()` — asyncio task runner (`_run_playback`); supports `hold`, `release`, `delay`, `led` (blocking or non-blocking), `wait_led`, `wait_ddc` (stubbed); interruptible via `_replay_stop` event; clean state broadcast in `finally` block regardless of error or natural completion.
  - `observe_event()` — wired to the observation bus; feeds snapshots and LED changes into the active recording session.
  - `websocket_sync()` — sends current state and library to a new WS client on connect.
  - Full `_broadcast_state()` / `_broadcast_library()` on every state-changing operation.
- `backend/src/pi_deck/api/router.py` — new recording routes:
  - `POST /api/v1/recordings/start`
  - `POST /api/v1/recordings/stop`
  - `GET  /api/v1/recordings/state`
  - `GET  /api/v1/recordings`
  - `POST /api/v1/recordings/upload`
  - `GET  /api/v1/recordings/{id}/download`
  - `GET  /api/v1/recordings/{id}/content`
  - `PUT  /api/v1/recordings/{id}/content`
  - `POST /api/v1/recordings/{id}/play`
  - `POST /api/v1/recordings/stop-playback`
  - `PATCH /api/v1/recordings/{id}` (rename)
  - `DELETE /api/v1/recordings/{id}`

### Frontend

- `frontend/src/components/RecordingWorkspace.tsx` — full recording workspace popup:
  - Hero bar: record/stop toggle (red), play/stop-playback toggle with circular progress icon, upload button.
  - Library pane: scrollable list of saved recordings; per-item inline play/stop button.
  - Detail pane: name (inline rename), created/updated timestamps, duration, event count, file size; edit, download, delete actions.
  - Text editor mode: raw JSON textarea with save, revert, close, and **save-and-play** actions; editor stays open during playback.
  - `isDraggingFile` state: document-level drag event ownership — overlay covers the entire workspace as soon as any file drag starts on the page, preventing the browser from handling missed drops. Drop accepted anywhere on the workspace.
  - Status cassette icon: animated spinning reels during recording (red) and replay (accent).
- `frontend/src/components/ConfirmDialog.tsx` — reusable centered yes/no confirmation dialog (used for delete and unsaved editor close).
- `frontend/src/hooks/useDeckEvents.ts` — added all recording actions: `startRecording`, `stopRecording`, `playRecording`, `stopRecordingPlayback`, `renameRecording`, `deleteRecording`, `uploadRecording`, `fetchRecordingContent`, `updateRecordingContent`, `recordingDownloadUrl`.
- `frontend/src/api/client.ts` — all recording API functions.
- `frontend/src/types.ts` — `RecordingState`, `RecordingSummary`, `RecordingLibrary`, `RecordingEvent` types.

### Design Document

- `docs/design/recording-syntax.md` — V1 format specification: file shape, all event types with semantics, LED rules, timing guidance, editing guidance, and compatibility notes.

### Post-Close Refinements

After the initial implementation, several correctness and UX issues were fixed:

| Fix | Description |
|-----|-------------|
| `duration_ms` removed from file body | Was a confusing calculated field stored redundantly. Removed from `RecordingFile`; `ConfigDict(extra="ignore")` added so old files still load. `RecordingSummary.duration_ms` (calculated at list time) is unchanged. |
| Play button race condition | `playRecordingAction` polled `refreshRecordingState()` after starting playback. For fast recordings, the stale HTTP "replaying" response arrived after the WS "idle" event, overwriting it and leaving the button stuck. Fix: removed the poll from the success path; WS event is the sole authority for the idle transition. |
| Drag overlay stuck visible | `stopPropagation()` on workspace drop handler prevented the document-level `drop` handler from clearing `isDraggingFile`. Fix: removed `stopPropagation()`; document handler correctly clears state on both valid and missed drops. |
| Save-and-play from editor | When the text editor was open, no play button was accessible. Added a play button to the editor actions row that saves if dirty then starts playback. |
| Timing guidance | Observed minimum reliable hold/inter-event timing of 50 ms on the CJ791 hardware; documented in `recording-syntax.md`. |

### Tests

- `backend/tests/test_phase16_recordings.py` — 15 tests:
  - Start/stop recording saves correct observation sequence
  - LED changes recorded as non-blocking events
  - Rename and delete
  - WebSocket sync on connect
  - Pre-held inputs ignored at recording start
  - Initial setup delay not persisted
  - Upload and download round-trip (including old files with `duration_ms` field)
  - Content load and replace
  - Empty recording returns idle immediately on play
  - Stop-playback interrupts long delay recording
  - Stale `duration_ms` in uploaded file is ignored
  - Concurrent operations rejected while busy
  - Delete while replaying succeeds; playback continues from in-memory copy
  - Interleaved LED and hold/release events preserve ordering
  - Upload rejects unsupported version

**Final test results:** 15/15 backend tests passed.

## Live Validation

Deployed as **r110** to `pi-deck` (Raspberry Pi 2B, `hardware=live`).

### Hardware timing observation

Observed on the CJ791 monitor JOG hardware:

- **Minimum hold duration:** 50 ms. Holds shorter than 50 ms are not reliably registered by the monitor firmware.
- **Minimum delay between inputs:** 50 ms. Delays shorter than 50 ms between a `release` and the next `hold` risk the monitor treating them as a single gesture or missing the second input.

This is now documented in `docs/design/recording-syntax.md` under "Timing Guidance."

### Recording workspace validation

Validated on live hardware at r110:

- Record button captures JOG hold/release/LED events from the observation bus.
- Captured recordings appear in the library list immediately on stop.
- Selected recording can be played back; progress circle tracks playback duration.
- Stop-playback button interrupts playback cleanly.
- Rename inline editor commits new name and renames the underlying file.
- Delete with confirmation removes the recording from library and disk.
- Upload via button and drag-and-drop (anywhere on workspace) accepts V1 JSON files.
- Download retrieves the raw JSON file from the browser.
- Text editor opens raw JSON; save/revert/close work; save-and-play saves and starts playback in one action.
- Drag overlay appears immediately on file drag enter; clears on drop (valid or missed) and on drag cancel.

## Host Health Snapshot

Run on the deck host 2026-04-23 after r110 deployment:

```text
pi-deck host health  |  2026-04-23T03:10:34.412823+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 1.50  0.76  0.64

[memory]
  RAM:  total 0.90 GiB  available 0.54 GiB  (MemTotal/MemAvailable KiB: 942120 / 563996)
  swap: total 0.90 GiB  free 0.87 GiB  (KiB: 942076 / 911988)

[disk]  mount /
  size 56.49 GiB  used 5.05 GiB  avail 49.11 GiB  (8.94% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  44.4 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=44.4'C
  voltage core: volt=1.3125V
  voltage sdram_c: volt=1.2000V
  voltage sdram_i: volt=1.2000V
  voltage sdram_p: volt=1.2250V
  get_throttled: throttled=0x0
  flags set: (none)

[systemd]
  pi-deck.service: active
  lightdm.service: active

[pi-deck HTTP]
  GET http://127.0.0.1:8756/health
  ok: True  body: '{"status":"ok","version":"0.1.0"}'
```

Health is clean. `get_throttled=0x0`, no flags, temperature within normal range. Swap usage slightly elevated (31 MB used) relative to Phase 19 baseline — within normal bounds for a kiosk session with the recording workspace open. No regressions.

## Exit Criteria Review

| Criterion | Status |
|-----------|--------|
| Sequences can be recorded from the observation bus | Done. `start_recording` / `stop_recording` captures hold, release, LED events; ignores pre-held inputs; skips leading setup delay. |
| Sequences can be replayed against live hardware | Done. `play_recording` drives JOG hold/release via `DeckControlService`; delay, blocking-led, and wait_led events handled; wait_ddc stubbed with clear error. |
| Playback can be stopped mid-sequence | Done. `stop_playback` sets `_replay_stop` event; runner checks it at each event boundary and after each sleep slice (≤ 50 ms granularity). |
| Concurrent operations are rejected | Done. `_ensure_idle()` returns 409 for start-while-busy, play-while-recording, record-while-replaying. |
| Sequences are validated before execution | Done. `RecordingFile` Pydantic model validates structure and event types on upload and before play. Unsupported version → 400. |
| Recording workspace fits 1280×800 kiosk layout | Done. Two-pane grid layout validated on the Waveshare DSI panel. |
| Upload, download, rename, delete, content edit all work | Done. All operations validated on live hardware at r110. |
| Host health gate passes | Done. See host health snapshot above. |
