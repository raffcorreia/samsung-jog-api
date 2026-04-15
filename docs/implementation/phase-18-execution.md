# Phase 18 — Widget layout and settings (planned)

Deck chrome and per-widget decisions move here after stripping the legacy top status strip.

## Settings widget (to build)

- **Hardware mode** — Surface `status.hardware` (**live** vs **mock**) from `GET /api/v1/status` (and keep in sync with websocket status snapshots as needed).
- **Toggle** — Allow switching **live** / **mock** only if product/security allows (today this is typically `PI_DECK_HARDWARE` on the Pi + restart; a future option might be an operator action or a dev-only control — spell out in this phase before implementing).

## Version string

- Move **`status.version`** out of the removed strip; place it in a deliberate location (about/settings/footer) in this phase or a follow-up.

## Signal feedback

- **KEY_ADC1** / **KEY_LED** (`status.signals`) — Reflect in **jog / control affordances** (e.g. per-button or ring cues), not a global status label. Exact UX is part of this widget increment.

## Operating mode

- **Operating mode** (jog / ddc / blind) is out of scope for the current jog widget surface; handle when this widget is extended.
