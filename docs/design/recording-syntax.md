# Recording Syntax

This document defines the Phase 16 recording file syntax used by the Pi deck macro system.

## Purpose

Recording files are the portable representation of an observed hardware interaction sequence.

The recorder captures real observation-bus semantics:

- `hold`
- `release`
- `delay`
- `wait_led`
- `wait_ddc`

The recorder does not invent higher-level actions such as `click center`.

## File Shape

Current files use version `V1`.

```json
{
  "name": "recording_2026-04-16_21-42-49",
  "version": "V1",
  "source": "observation",
  "created_at": "2026-04-16T21:42:49Z",
  "updated_at": "2026-04-16T21:43:02Z",
  "duration_ms": 13140,
  "events": [
    { "type": "hold", "action": "center" },
    { "type": "delay", "duration_ms": 88 },
    { "type": "release", "action": "center" },
    {
      "type": "wait_led",
      "match": { "active": true },
      "poll_interval_ms": 50,
      "timeout_ms": 2000
    }
  ]
}
```

## Top-Level Fields

- `name`
  Human-facing recording name. Used as the default filename stem.
- `version`
  Syntax version. Current value: `V1`.
- `source`
  Capture origin. Current value: `observation`.
- `created_at`
  Recording creation timestamp in ISO-8601 UTC form.
- `updated_at`
  Last modification timestamp in ISO-8601 UTC form.
- `duration_ms`
  Total wall-clock duration represented by the saved recording.
- `events`
  Ordered list of executable macro events.

## Event Semantics

### `hold`

Represents an observed press start for a JOG action.

```json
{ "type": "hold", "action": "left" }
```

Allowed `action` values:

- `up`
- `down`
- `left`
- `right`
- `center`

### `release`

Represents an observed press end for a JOG action.

```json
{ "type": "release", "action": "left" }
```

### `delay`

Represents elapsed time between two semantic events.

```json
{ "type": "delay", "duration_ms": 120 }
```

Notes:

- The recorder does not persist the initial setup delay before the first captured event.
- Internal timing between recorded events is preserved.
- If a macro intentionally needs an initial wait before doing anything, add a leading `delay` event manually to the JSON file.

### `wait_led`

Blocks playback until the observed LED state matches the requested condition.

```json
{
  "type": "wait_led",
  "match": { "active": false },
  "poll_interval_ms": 50,
  "timeout_ms": 1800
}
```

Important:

- `wait_led` is an observation gate.
- It does not command the hardware LED to blink or change state.
- It only blocks until the observed LED state matches the expected condition or times out.

### `wait_ddc`

Reserved for future DDC synchronization gates.

```json
{
  "type": "wait_ddc",
  "match": {},
  "poll_interval_ms": 100,
  "timeout_ms": 2000
}
```

Phase 16 does not execute `wait_ddc` on the live hardware path yet.

## Recording Rules

- The recorder captures observation-bus events, not inferred gestures.
- Pre-held inputs present when recording starts are ignored.
- The first persisted event is the first real semantic event seen after recording begins.
- Initial user hesitation before starting the sequence is intentionally not stored as a leading delay.
- A tap is represented as:
  `hold` -> optional `delay` -> `release`

## Editing Guidance

Manual JSON edits are allowed for advanced use.

Safe edits include:

- renaming `name`
- adding an initial `delay`
- adjusting intermediate `delay.duration_ms`
- changing or removing `wait_led` gates

Unsafe edits include:

- mismatching `hold` and `release` pairs
- using unsupported `action` values
- introducing invalid timestamps or negative durations

## Compatibility

- New files are written with `version: "V1"`.
- Older numeric `version: 1` files are still accepted for compatibility during Phase 16.
