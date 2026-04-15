# Phase 13 Execution Record

**Status:** in progress — implementation deployed to deck host (r7); pending visual confirmation and host health snapshot

**Date:** 2026-04-15

## Summary

Phase 13 delivers the full-screen UI shell at `1280×800` with real functional widgets (JogPad, live log) and mocked placeholder panels (calendar, notes) that look and feel like the real product. It also establishes the foundational navigation and UI composition patterns — shared top bar, screen routing, popup template — that all future phases will build on.

## UI design decisions (pre-implementation brainstorm)

The following decisions were agreed before implementation began. They extend and refine the plan scope.

### Layout grid

```
┌─────────────────────────────────────────────────────┐  800px
│  TOP BAR  48px fixed                                │
├────────────┬────────────────────────────────────────┤
│            │                                        │
│  LEFT COL  │  RIGHT PANEL                           │
│  ~260px    │  (calendar + notes placeholders)       │
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

The top bar is a **shared layout component** — every screen is wrapped in it; it receives an optional `title` prop.

### Left column

- **Power button** (stub — no behavior yet): large, touch-friendly, uses `--danger` tint. Positioned in the **top bar** (far left), not in the body.
- **JogPad**: owns the left column body. The existing functional `JogPad` component is unchanged. The left column is its slot.

### LED indicator

A small status circle overlaid on the top-left of the JogPad area:
- **Gray** = LED off (or unknown / stub)
- **Blue** = LED on

Accepts a boolean prop (`ledOn: boolean`). Stubbed to `false` (always gray) in Phase 13. Phase 15 wires it to real `KEY_LED` observation events.

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

- **`frontend/src/components/TopBar.tsx`** — persistent top bar; power button (stub), 24h clock (frontend `setInterval`), back arrow + title on non-home screens, settings cog.
- **`frontend/src/components/LedIndicator.tsx`** — 10px status circle overlaid at top-left of JogPad; gray (off) / blue (on). Stubbed to `false` — Phase 15 wires `KEY_LED`.
- **`frontend/src/components/Popup.tsx`** — portal-based popup template; document-level `pointerdown` capture for dismissal; `ignoreRef` prevents dismissal when clicking the parent widget; visual backdrop has `pointer-events: none` so JogPad remains interactive.
- **`frontend/src/pages/HomePage.tsx`** — 1280×800 grid: left column (JogPad + LED indicator + OSD dev trigger), right panel (Calendar + Notes), fixed 200 px log band.
- **`frontend/src/pages/SettingsPage.tsx`** — settings stub with placeholder rows (Appearance, Control, About sections).
- **`frontend/src/widgets/CalendarWidget.tsx`** — static April 2026 month grid; today (15) highlighted; mock events with dots.
- **`frontend/src/widgets/NotesWidget.tsx`** — 4 mock project notes that look like real dev notes.
- **`frontend/src/widgets/OsdMockPanel.tsx`** — Samsung CJ791 OSD reproduction; 7 menu tabs (Eye Care, Picture, Color, Display, PBP/PiP, System, Information); realistic sub-items per tab; interactive tab/item selection.
- **`frontend/src/App.tsx`** — updated to `BrowserRouter` + `Routes`; `AppInner` derives title from `useLocation`; `ROUTE_TITLES` map for future routes.
- **Routing:** `/` → HomePage, `/settings` → SettingsPage. `StaticFiles(html=True)` in FastAPI already serves `index.html` as fallback — client-side routing works on hard refresh.
- **CSS variables added:** `--deck-topbar-height: 48px`, `--deck-left-col: 260px`.
- **Tests:** `TopBar` (6), `LedIndicator` (4), `Popup` (8), `SettingsPage` (2), `CalendarWidget` (4), `NotesWidget` (3) — all pass.
- **Deployed:** r7 on deck host, hardware live, `/api/v1/status` confirms `"version":"0.1.0+r7"`.

## Operational entry points

| Item | Role |
|------|------|
| `frontend/src/components/TopBar.tsx` | Shared persistent top bar — wraps every screen |
| `frontend/src/components/Popup.tsx` | Reusable popup template |
| `frontend/src/components/LedIndicator.tsx` | JogPad LED status circle (stubbed) |
| `frontend/src/widgets/OsdMockPanel.tsx` | Samsung CJ791 OSD reproduction (stub) |
| `/settings` route | Settings screen (stub content) |

## Exit criteria (from plan)

| Criterion | Status |
|-----------|--------|
| Deck display shows complete intended layout at `1280×800` with correct proportions | Deployed r7 — visual confirmation pending from deck display |
| Real JogPad and live log functional (unchanged) | Verified — existing tests pass, JogPad props unchanged |
| Placeholder calendar and notes panels with realistic mock data | Done — static April 2026 grid + 4 mock project notes |
| Top bar persistent across screens; title + back navigation on non-home screens | Done — `TopBar` with `useLocation`-derived title in `App.tsx` |
| Settings route reachable via cog; back navigation returns home | Done — `/settings` route, back button navigates to `/` |
| Popup template implemented; JogPad popup stub validates position and dismissal | Done — portal Popup + OSD dev trigger in HomePage |
| LED indicator on JogPad stubbed gray | Done — `LedIndicator on={false}` overlay |
| All new components covered by Vitest tests | Done — 27 new tests, all pass |
| Host health gate | Pending — paste snapshot below after visual confirmation |

## Host health snapshot

*(Paste output of `python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py` on the deck host after deploy.)*
