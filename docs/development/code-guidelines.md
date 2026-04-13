# Code Guidelines

## Purpose

This document defines lightweight development guidelines for `samsung-jog-api`.

The goal is not to create a heavy style manual. The goal is to keep implementation aligned with the architecture so the codebase stays understandable as hardware, backend, and frontend work grow together.

## General principles

- keep architecture boundaries visible in the code
- prefer clear names over clever abstractions
- avoid leaking low-level hardware terms into higher-level UI and workflow layers unless necessary
- make logging and error handling consistent
- keep implementation pragmatic and easy to debug

## Code style

- keep functions and methods focused on a single responsibility
- if a function becomes hard to scan or mixes concerns, split it
- prefer descriptive names over abbreviations
- name objects and types by their domain meaning rather than temporary implementation detail
- keep side effects obvious
- avoid deep nesting where a flatter structure is clearer
- prefer explicit data shapes over loose dictionaries where practical
- avoid comments that merely restate obvious code
- add comments only where intent, hardware nuance, or non-obvious behavior would otherwise be unclear
- do not add arbitrary line-count rules if they make the code worse; optimize for readability and maintainability

## Backend guidelines

The Python import package is **`pi_deck`** (directory `backend/src/pi_deck/`; PyPI / `pip` name **`pi-deck`** in `backend/pyproject.toml`). Repository layout: see [Architecture — Repository layout](../architecture.md#repository-layout).

Top-level packages inside **`pi_deck`** (each is a real directory with an `__init__.py`):

| Package | Role |
|---------|------|
| `api` | FastAPI routes, HTTP/WebSocket boundary |
| `services` | Workflows, arbitration, sequences |
| `hardware` | GPIO, `JOG`, `LED`, `DDC` adapters — **only** layer that touches signals |
| `storage` | Recordings, settings, local files |
| `models` | Domain types and validation models |
| `cli` | Console tools (e.g. bench probe); **not** loaded by the web app unless explicitly invoked |

### Lifecycle across implementation phases

This matches the system model in [Solution Overview](../design/solution-overview.md): *UI → API → monitor-control services → **hardware interface** (+ DDC) → monitor*.

- **Phases 9+ (platform, API, UI, recording):** the **`hardware/`** tree is **not** throwaway scaffolding. It is the **custom hardware interface** layer: `jog_drive`, `jog_observe`, `led_observe`, later `ddc`, etc. **`services`** and **`api`** (Phases 10–12) **import and orchestrate** this layer; they do not replace it each phase.
- **Phase 9 (kiosk, `systemd`, logging)** mostly configures **how the host runs** the eventual backend process. It does **not** imply rewriting or discarding the hardware modules—only **starting** the same package under supervision when the API exists.
- **What may change later:** GPIO numbers and possibly concrete classes when moving from **Phase 6** wiring to **Phase 7** boards ([deferred migration](../implementation/plan.md#deferred-integrated-board-gpio-and-software-migration))—that is **remapping and adaptation**, not deleting the backend and starting over.

### Language and framework

- use `Python`
- use `FastAPI` for HTTP and websocket interfaces

### Module boundaries

Keep the backend split conceptually into:

- `api`
- `services`
- `hardware`
- `storage`
- `models`

Responsibilities:

- `api`
  - request and response handling
  - websocket endpoints
  - validation at the boundary
- `services`
  - monitor workflow logic
  - command arbitration
  - sequence execution orchestration
  - widget-oriented application services
- `hardware`
  - `jog_drive`
  - `jog_observe`
  - `led_observe`
  - `ddc`
  - `display_power`
- `storage`
  - recordings
  - settings
  - local persisted state
- `models`
  - typed domain objects
  - schema and validation models
  - error types

### Backend design rules

- keep low-level monitor signal details inside `hardware`
- keep monitor workflows inside `services`
- keep API routes thin
- do not let route handlers embed monitor workflow logic
- do not let UI-facing layers manipulate GPIO or `DDC` directly
- treat sequences as validated domain objects, not loose dictionaries passed everywhere

### Error handling

- use explicit error categories
- prefer structured failures over generic exceptions at API boundaries
- log operational context when commands fail
- keep failure reasons meaningful enough for the UI to present useful feedback

### Logging

- produce one event per line
- include timestamp, type, and message
- keep log categories consistent across modules
- do not log secrets, credentials, usernames, or private network details

## Frontend guidelines

### Language and framework

- use `React`
- use `TypeScript`

### Frontend design rules

- keep one UI for kiosk and LAN browser access
- optimize layout first for `1024x600`, while remaining responsive
- keep primary control actions visually dominant
- treat monitor control as the primary interaction surface
- keep dashboard widgets secondary in layout weight

### Component boundaries

- keep presentational components small and focused
- keep workflow and API coordination out of leaf components
- avoid letting unrelated widgets interfere with one another
- keep advanced/settings tooling separate from primary controls in the layout, not as a separate product

### Navigation and URLs

Browser navigation behavior should work properly outside kiosk use.

That means:

- back and forward browser actions should behave correctly
- important screens and views should have stable URLs
- the current URL should be copyable and usable to return directly to the same place later
- routing should not depend on kiosk-only assumptions

The kiosk may not expose browser controls, but the application should still behave like a real web app when accessed from a full browser.

### State and live updates

- use normal API fetches for data that does not require live push
- use websocket-driven updates for live control and status behavior
- keep websocket event handling centralized rather than scattering it across many components
- do not duplicate the same live state in multiple unrelated places without a clear owner

## Domain-model guidelines

- prefer logical action names such as `press`, `wait_led`, and `wait_ddc`
- do not expose low-level bus names such as `KEY_ADC1` and `KEY_ADC2` in UI-facing sequence definitions unless truly necessary
- keep logical actions separate from hardware mapping
- keep start-state and end-state assumptions explicit where relevant

## Recording and sequence guidelines

- store recordings as structured JSON files
- validate recordings before execution
- keep recordings editable by humans
- use meaningful names for promoted recordings
- treat timeout behavior as part of sequence correctness, not as an edge case

## Settings guidelines

- prefer toggles and simple choices
- avoid typed settings where possible
- assume no hardware keyboard is present
- design for touch-first interaction

## Security and repository hygiene

- do not commit passwords
- do not commit keys
- do not commit usernames
- do not commit private IP addresses or environment-specific secrets

## When in doubt

- keep low-level hardware concerns low in the stack
- keep the UI working like a normal web app
- prefer explicit structure over hidden coupling
- favor debuggability over premature cleverness
