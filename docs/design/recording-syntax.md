# Recording Syntax

This document defines the Phase 16 recording file syntax used by the Pi deck macro system.

## Purpose

Recording files are the portable representation of an observed hardware interaction sequence.

The recorder captures real observation-bus semantics:

- `hold`
- `release`
- `delay`
- `led`
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
  "events": [
    { "type": "hold", "action": "center" },
    { "type": "delay", "duration_ms": 88 },
    { "type": "release", "action": "center" },
    {
      "type": "led",
      "active": true,
      "blocking": false
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
- `duration_ms` is derived from explicit event timing, so removing a leading delay reduces the recording length.
- If a macro intentionally needs an initial wait before doing anything, add a leading `delay` event manually to the JSON file.

### `led`

Represents an observed LED state transition from the observation bus.

```json
{
  "type": "led",
  "active": true,
  "blocking": false
}
```

Notes:

- normal recorded LED observations should use `blocking: false`
- this preserves the observed cue without blocking later events
- if a macro needs LED-gated continuation, set `blocking: true` and provide timeout settings
- `led` should be the default form used by the recorder for observed `KEY_LED` changes

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

- `led` is the normal recorded observation event for LED changes.
- `wait_led` is an observation gate.
- It does not command the hardware LED to blink or change state.
- It only blocks until the observed LED state matches the expected condition or times out.

## LED Rules

The LED rules for Phase 16 are:

- LED changes should be recorded as observation events.
- Recorded LED changes should not block later events by default.
- LED does not represent an output command channel.
- The system must never interpret recorded LED events as instructions to drive the monitor LED.
- Blocking LED behavior is explicit, not implied.

That means:

- use `led` for normal recorded LED state changes
- use `wait_led` when a macro step must pause until a target LED state is observed
- or set `blocking: true` on a `led` event when editing a recording and you want that specific LED event to behave as a gate

## When To Use `wait_led`

Use `wait_led` only when the next event must not continue until LED feedback reaches a known state.

Good uses:

- waiting for an LED cue that indicates an input transition has settled
- pausing until the monitor returns to an idle LED state
- synchronizing a later action to a known LED feedback moment

Bad uses:

- recording every LED change as a blocking wait
- treating LED events as if they were commands
- adding `wait_led` when the sequence can safely continue without it

In short:

- `led` preserves observation
- `wait_led` enforces synchronization

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
- changing an observed `led` event to `blocking: true` when a macro should wait on LED
- changing or removing `wait_led` gates

Unsafe edits include:

- mismatching `hold` and `release` pairs
- using unsupported `action` values
- introducing invalid timestamps or negative durations

## Compatibility

- New files are written with `version: "V1"`.
- Older numeric `version: 1` files are accepted for compatibility with files that predate the string format.
