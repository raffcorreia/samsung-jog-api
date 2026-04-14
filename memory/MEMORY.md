# Memory Index

- [Project Overview](project_overview.md) — CJ791 JOG emulator: 2-board Phase 7 design (Controller + HDMI DDC), Pi 2B, GPIO map, connectors, power budget all settled

**Deck UI (kiosk):** Fixed widget geometry on **1280×800** — JOG and log regions do **not** resize each other when log text grows (scroll inside log). No portal/landing-page chrome; `pi-deck` naming lives in the status bar. See `docs/design/solution-overview.md` (Deck shell and widget geometry).

**JOG input:** The electrical jog path is **one direction at a time** (same as `JogDrive.release_all` before assert). The UI is **not** multitouch-parallel: a second finger is ignored while the first gesture is active. That matches hardware; it is not a multitouch gesture surface.
