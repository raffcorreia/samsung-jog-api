# Test Strategy

## Purpose

This document defines the testing strategy for `samsung-jog-api`.

The goal is to make testing an intentional part of the project rather than something deferred until late implementation. Because this project spans UI, backend logic, monitor communication, and custom hardware, the test strategy must cover more than unit tests.

## Testing goals

- verify correctness of backend logic and command arbitration
- verify correctness of frontend behavior and user feedback
- verify low-level hardware behavior and monitor interaction
- verify sequence validation, execution, timeout, and abort behavior
- verify productized monitor workflows such as source switching and `PiP`
- verify reboot, recovery, and daily-use stability

## Test layers

The project should use multiple test layers.

### 1. Backend tests

Purpose:

- validate API behavior
- validate service logic
- validate command arbitration
- validate error handling
- validate settings and storage behavior

Examples:

- reject same-bus command conflicts
- accept simultaneous cross-bus actions where supported
- return correct error type when a bus is busy
- reject invalid sequence files
- stop a running sequence when a manual abort is requested

### 2. Frontend tests

Purpose:

- validate control interactions
- validate websocket-driven updates
- validate visible success/failure feedback
- validate advanced/settings flows
- validate responsive behavior for the intended layout model

Examples:

- button press shows active feedback
- rejected command shows failure feedback
- live log panel updates when new log events arrive
- recording tools appear in advanced/settings
- mode-specific controls change correctly between `DDC` and `Blind`

#### Playwright integrated E2E (`frontend/`)

End-to-end tests run **Chromium** against the built SPA served by **`pi-deck`** on port 8756 (same origin for REST and `/ws/events`, no dev proxy). `npm run test:e2e` runs `vite build` first so `backend/src/pi_deck/static/` matches the UI under test, then starts mock-hardware `pi-deck` if needed. This catches REST + WebSocket + UI integration that Vitest/jsdom cannot.

To hit a **running deck** instead (e.g. Raspberry Pi on the LAN):

```bash
cd frontend
E2E_BASE_URL=http://10.0.0.11:8756 npm run test:e2e
```

When `E2E_BASE_URL` is set, Playwright does not start local servers—ensure `websockets` is installed on the Pi and `pi-deck` is running.

### 3. Sequence validation tests

Purpose:

- validate recording schema correctness
- validate domain-object parsing
- validate event ordering rules
- validate wait-event semantics

Examples:

- valid `press`, `delay`, `wait_led`, and `wait_ddc` events are accepted
- missing required fields fail validation
- unsupported event types fail validation
- invalid timeout or polling values fail validation

### 4. Sequence runner tests

Purpose:

- validate execution logic independent of the physical monitor where possible
- validate timeout behavior
- validate abort behavior
- validate rejection of concurrent sequence execution

Examples:

- a sequence stops when `wait_led` times out
- a sequence stops when `wait_ddc` times out
- manual abort stops a running sequence immediately
- a second sequence request fails while one is already running

### 5. Hardware-facing verification tests

Purpose:

- validate low-level monitor interaction
- validate observe-path behavior
- validate drive-path behavior
- validate `DDC` and `LED` assumptions against the real monitor

Examples:

- each low-level `JOG` action is interpreted correctly by the monitor
- idle bus state is observed correctly
- `KEY_LED` transitions are captured when expected
- supported `DDC` reads return expected values
- supported `DDC` writes succeed where confirmed

### 6. Integration tests

Purpose:

- validate user-facing monitor workflows end to end
- validate coordination between UI, backend, sequence execution, and monitor feedback

Examples:

- source switch in `DDC` mode
- source switch in `Blind` mode
- `PiP` enable flow
- `PiP` source selection flow
- replay of a shipped validated sequence

### 7. End-to-end and endurance tests

Purpose:

- validate regular-use stability
- validate recovery after reboot or crashes
- validate repeated monitor workflows over time

Examples:

- reboot returns to kiosk UI
- repeated source switching remains reliable
- repeated sequence execution does not leave the system stuck
- log retention and restart behavior operate as intended

### 8. Deck host health snapshots

Purpose:

- capture CPU, memory, disk, thermals, Raspberry Pi throttling/voltage, and `pi-deck` service health on the real deck when closing feature phases (see [Host health gate](../implementation/plan.md#host-health-gate-feature-phases-1019))

Tool: `scripts/pi-deck-host-health.py` — paste the **default text output** into the **Markdown** phase execution record (not JSON as the primary write-up; `--json` is optional for tooling or archives). Complements automated tests for resource and power regressions. For how that snapshot relates to **JOG kiosk / LAN UI** behavior, see [JOG UI performance](ui-performance.md).

## Test environment model

The project should assume more than one test environment.

### Local development environment

Used for:

- backend tests
- frontend tests
- schema validation tests
- some sequence-runner tests with mocks or stubs

### Hardware-attached development environment

Used for:

- low-level `JOG` verification
- `LED` observation testing
- `DDC` validation
- integration testing against the real monitor

### Daily-use validation environment

Used for:

- repeated workflow testing
- reboot recovery validation
- endurance testing

In practice, these may all be the same Raspberry Pi and monitor setup, but the test intent should remain distinct.

## Mock vs real-hardware boundary

The test strategy should explicitly separate what can be mocked from what must be proven on real hardware.

Suitable for mocks or stubs:

- API validation
- websocket event shape
- sequence schema parsing
- sequence-runner control flow
- settings persistence
- widget data-provider logic

Must be validated on real hardware:

- analog `JOG` action reproduction
- physical bus observation
- `KEY_LED` behavior
- real `DDC` timing and reliability
- interaction between physical `JOG` use and app-driven control

## Sequence-specific test design

Because sequences are central to the project, they need explicit validation rules.

Each promoted sequence should be checked for:

- valid schema
- meaningful name
- known start-state assumptions
- timeout behavior for any wait events
- success criteria
- expected failure behavior

Promoted sequences should not be treated as production-ready just because they replay once successfully.

## Error classes that tests should cover

The test design should cover at least these failure categories:

- bus busy
- overlapping same-bus command rejected
- sequence already running
- timeout waiting for `LED`
- timeout waiting for `DDC`
- `DDC` unavailable
- invalid start-state assumption
- manual abort
- internal hardware/control error

## Logging and observability tests

Because logs are part of the operational model, testing should also cover:

- event formatting
- log type/category labeling
- live log streaming to the UI
- file rotation by day
- retention behavior over time
- ability to disable persistent logging

## Completion gates

No phase should be treated as complete unless the relevant testing work for that phase has been done.

At minimum:

- backend-facing features need backend tests
- frontend-facing features need frontend tests
- hardware assumptions need hardware verification
- promoted monitor workflows need integration validation

## Recommended next test-design artifacts

After this strategy document, the project should eventually add:

- sequence schema validation rules
- hardware verification checklist
- integration test checklist for monitor workflows
- stabilization checklist for daily-use readiness
