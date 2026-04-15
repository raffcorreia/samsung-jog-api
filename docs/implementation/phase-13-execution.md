# Phase 13 Execution Record

**Status:** complete

**Date:** 2026-04-15

## Summary

Phase 13 delivers the full-screen UI shell at `1280×800` with real functional widgets (JogPad, live log) and mocked placeholder panels (calendar, notes) that look and feel like the real product. It also establishes the foundational navigation and UI composition patterns — shared top bar, screen routing, popup template — that all future phases will build on.

The final Phase 13 build was deployed to the deck host as `0.1.0+r20`, verified on the target display, and committed in `9396745 Implement phase 13 deck UI shell` (included in merge commit `05089c1` on `main`).

## UI design decisions (pre-implementation brainstorm)

The following decisions were agreed before implementation began. They extend and refine the plan scope.

### Layout grid

```
┌─────────────────────────────────────────────────────┐  800px
│  TOP BAR  48px fixed                                │
├────────────┬────────────────────────────────────────┤
│            │                                        │
│  LEFT COL  │  RIGHT PANEL                           │
│  350px     │  (calendar + notes placeholders)       │
│            │                                        │
├────────────┴────────────────────────────────────────┤
│  LOG PANEL  200px fixed (development only)          │
└─────────────────────────────────────────────────────┘
```

Fixed geometry throughout — no panel resizes because another widget's content changed.

### Top bar

Always visible across every screen. Adapts per screen:

- **Home:** `[⏻ Power]  [HH:MM]  ·············  [⚙]`
- **Any other screen:** `[⏻ Power]  [HH:MM]  ← Screen Title  ·····  [⚙]`

Rules:
- Power button is far left.
- Clock (`HH:MM`, 24-hour, frontend-local `setInterval`) is immediately right of power.
- Screen title + `←` back navigation appear in the middle on non-home screens. Clicking navigates back to home.
- Settings cog is right-anchored and always visible. On the settings screen it is a no-op (already there).
- No title on the home screen.
- Clock uses the `DSEG7 Classic` seven-segment font from the `dseg` package, loaded with `font-display: block` to avoid the visible resize/fallback flash after refresh.
- Clock is maximized within the existing `48px` top bar and visually centered with a small vertical transform; the top bar height remains unchanged.

The top bar is a **shared layout component** — every screen is wrapped in it; it receives an optional `title` prop.

### Left column

- **Power button** (stub — no behavior yet): large, touch-friendly, uses `--danger` tint. Positioned in the **top bar** (far left), not in the body.
- **JogPad**: owns the left column body. The existing functional `JogPad` component is unchanged. The left column is its slot.

### LED indicator

A physical-style status circle overlaid near the top-left of the JogPad area:
- **Gray** = LED off (or unknown / stub)
- **Blue** = transient blink / active indication

Accepts a boolean prop (`on: boolean`). Stubbed to `false` (always gray) in Phase 13. Phase 15 wires it to real `KEY_LED` observation events. The indicator is intentionally **not** tied to the backend's steady `key_led_active` value in Phase 13 because the user expectation is gray by default and blue only during blink/feedback events.

### Record button

A record control stub was added in the upper-right of the JogPad column, matching the user's marked target area. It is visually present, logs `record — not wired yet`, and is reserved for the recording/replay subsystem in Phase 16.

### Right panel

Two side-by-side placeholder sub-panels: **Calendar** and **Notes**.

Placeholder style: realistic mock data (static month grid, hardcoded note entries) — no "coming soon" labels. Panels use `--surface-elevated` background and `--muted` text so they read as secondary content without being distractingly prominent.

Split ratio deferred — single panel or 50/50 to be decided during implementation.

### Log panel

- `200px` fixed height, existing `LiveLogWidget`, unchanged.
- **Temporary** — exists during active development. Will be refactored in Phase 14 (log moves to backend) and eventually replaced by a permanent bottom widget area.

### Navigation model

Two patterns for widgets:

1. **Full-screen navigation** — navigates to a new route (e.g. `⚙` → `/settings`). Requires a router (React Router).
2. **Popup** — floats over the current screen. Any widget can open one.

Routes for Phase 13:
- `/` — main deck (home)
- `/settings` — settings screen (stub content; top bar shows `← Settings`)

### Popup template

A reusable `<Popup>` component available to any widget. Rules:

- **`X` button** always rendered (top-right of popup).
- **Backdrop click** closes the popup — _except_ clicking on the **parent widget that spawned it** does not close it (so JogPad stays usable while its popup is open).
- **Preferred position**: caller can pass a position hint (e.g. `right`, `center`). Default is `center`. JogPad requests `right` so the popup does not cover the pad.
- Popup is rendered in a portal (appended to `document.body`) so it is never clipped by a parent's `overflow: hidden`.

### JogPad popup (stub for Phase 13, live in Phase 15)

- Opens automatically when a **bus activity WebSocket event** arrives (Phase 15).
- For Phase 13: opened via a small dev-trigger button on the JogWidget to validate layout and position.
- Content: a mock OSD screen representation — static placeholder grid matching the Samsung CJ791 OSD visual style.
- Positioned to the right of center so it does not cover the JogPad.
- The component accepts a reactive data prop; Phase 15 supplies live bus events.

### Dark mode

The entire design system is dark-first using CSS custom properties defined in `index.css`. All Phase 13 components use design tokens (`--bg`, `--surface`, `--surface-elevated`, `--border`, `--text`, `--muted`, `--accent`, `--danger`, etc.) — no hardcoded colors. A future light mode is a single `:root[data-theme="light"]` override block in settings.

## Done in repo

- **`frontend/src/components/TopBar.tsx`** — persistent top bar; power button (stub), 24h clock (frontend `setInterval`), back arrow + title on non-home screens, settings cog right-anchored.
- **`frontend/src/components/TopBar.module.css`** — fixed `48px` top bar, seven-segment `Deck Clock` styling at `2.38rem`, centered vertically without increasing top bar height.
- **`frontend/src/components/LedIndicator.tsx`** — 22px physical-style LED overlaid near the JogPad; gray by default, blue only when `on=true`. Stubbed to `false` — Phase 15 wires blink events.
- **`frontend/src/components/Popup.tsx`** — portal-based popup template; document-level `pointerdown` capture for dismissal; `ignoreRef` prevents dismissal when clicking the parent widget; visual backdrop has `pointer-events: none` so JogPad remains interactive.
- **`frontend/src/pages/HomePage.tsx`** — 1280×800 grid: 350px left column (JogPad + LED indicator + record stub + OSD dev trigger), right panel (Calendar + Notes), fixed 200px log band.
- **`frontend/src/pages/SettingsPage.tsx`** — settings stub with placeholder rows (Appearance, Control, About sections).
- **`frontend/src/widgets/CalendarWidget.tsx`** — static April 2026 month grid; today (15) highlighted; mock events with dots.
- **`frontend/src/widgets/NotesWidget.tsx`** — 4 mock project notes that look like real dev notes.
- **`frontend/src/widgets/OsdMockPanel.tsx`** — Samsung CJ791 OSD reproduction; 7 menu tabs (Eye Care, Picture, Color, Display, PBP/PiP, System, Information); realistic sub-items per tab; interactive tab/item selection.
- **`frontend/src/App.tsx`** — updated to `BrowserRouter` + `Routes`; `AppInner` derives title from `useLocation`; `ROUTE_TITLES` map for future routes.
- **`frontend/src/index.css`** — deck geometry variables, `DSEG7 Classic` font face, and fixed kiosk viewport assumptions.
- **Routing:** `/` → HomePage, `/settings` → SettingsPage. `StaticFiles(html=True)` in FastAPI already serves `index.html` as fallback — client-side routing works on hard refresh.
- **CSS variables added:** `--deck-topbar-height: 48px`, `--deck-log-height: 200px`, `--deck-left-col: 350px`.
- **Tests:** `TopBar` (6), `LedIndicator` (4), `Popup` (8), `SettingsPage` (2), `CalendarWidget` (4), `NotesWidget` (3), plus existing frontend coverage — `46` tests pass.
- **Build:** `npm run build` passes and emits the `DSEG7 Classic` clock font assets into backend static output.
- **Deployed:** `0.1.0+r20` on deck host, hardware live, `/api/v1/status` confirmed `"hardware":"live"`, `"operating_mode":"jog"`, `"control_state":"idle"`.

## Operational entry points

| Item | Role |
|------|------|
| `frontend/src/components/TopBar.tsx` | Shared persistent top bar — wraps every screen |
| `frontend/src/components/Popup.tsx` | Reusable popup template |
| `frontend/src/components/LedIndicator.tsx` | JogPad LED status circle (stubbed) |
| `frontend/src/pages/HomePage.tsx` | Fixed deck grid and JogPad column composition |
| `frontend/src/widgets/OsdMockPanel.tsx` | Samsung CJ791 OSD reproduction (stub) |
| `/settings` route | Settings screen (stub content) |

## Exit criteria (from plan)

| Criterion | Status |
|-----------|--------|
| Deck display shows complete intended layout at `1280×800` with correct proportions | Done — deployed and visually iterated on target display through `r20` |
| Real JogPad and live log functional (unchanged) | Done — existing JogPad behavior preserved; tests pass |
| Placeholder calendar and notes panels with realistic mock data | Done — static April 2026 grid + 4 mock project notes |
| Top bar persistent across screens; title + back navigation on non-home screens | Done — `TopBar` with `useLocation`-derived title in `App.tsx` |
| Settings route reachable via cog; back navigation returns home | Done — `/settings` route, back button navigates to `/` |
| Popup template implemented; JogPad popup stub validates position and dismissal | Done — portal Popup + OSD dev trigger in HomePage |
| LED indicator on JogPad stubbed gray | Done — `LedIndicator on={false}` overlay; blue reserved for blink state |
| All new components covered by Vitest tests | Done — frontend suite passes: 14 files, 46 tests |
| Host health gate | Done — snapshot below |

## Verification

Commands run from the dev machine:

```bash
cd frontend
npm test -- --run
npm run build
ssh rafael@10.0.0.11 'python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py'
```

Results:

- `npm test -- --run`: 14 test files passed, 46 tests passed.
- `npm run build`: Vite production build passed; generated backend static assets, including `DSEG7 Classic` font assets.
- Host health: passed; service active, kiosk display manager active, HTTP health endpoint OK, no throttling flags.

Deploy evidence from final Phase 13 deploy:

```json
{
  "version": "0.1.0+r20",
  "hardware": "live",
  "operating_mode": "jog",
  "control_state": "idle",
  "signals": {
    "key_adc1_active": true,
    "key_led_active": false
  }
}
```

## Host health snapshot

Output of `python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py` on the deck host:

```text
pi-deck host health  |  2026-04-15T16:51:54.078515+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.08  0.13  0.26

[memory]
  RAM:  total 0.90 GiB  available 0.55 GiB  (MemTotal/MemAvailable KiB: 942120 / 578008)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 941668)

[disk]  mount /
  size 56.49 GiB  used 4.98 GiB  avail 49.17 GiB  (8.82% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  45.5 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=46.0'C
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
