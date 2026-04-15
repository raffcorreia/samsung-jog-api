# Memory Index

- [Project Overview](project_overview.md) — CJ791 JOG emulator: 2-board Phase 7 design (Controller + HDMI DDC), Pi 2B, GPIO map, connectors, power budget all settled; Phase 14 live log backend complete

**Deck UI (kiosk):** Phase 13 complete. Fixed widget geometry on **1280×800** — top bar `48px`, left JOG column `350px`, bottom log band `200px`. JOG and log regions do **not** resize each other when log text grows (scroll inside log). No portal/landing-page chrome; `pi-deck` naming lives in the status/version area, not duplicated as marketing chrome.

**Phase 13 UI decisions:** Clock uses `DSEG7 Classic` seven-segment font and is vertically centered within the unchanged top bar. Settings cog is top-right. LED is gray by default and blue only for future blink/feedback state, not steady `key_led_active`. Record button is a visual stub in the upper-right of the JOG widget column. OSD popup is a reusable portal-based template opened by the JOG dev trigger.

**Phase 14 live log:** Complete. Backend owns live log history in `LiveLogService` with a bounded `220`-entry replay buffer. WebSocket clients receive backend `log/entry` events and replay on connect; frontend only renders received backend entries. UI-originated stub messages go through `POST /api/v1/log`.

**JOG input:** The electrical jog path is **one direction at a time** (same as `JogDrive.release_all` before assert). The UI is **not** multitouch-parallel: a second finger is ignored while the first gesture is active. That matches hardware; it is not a multitouch gesture surface.
