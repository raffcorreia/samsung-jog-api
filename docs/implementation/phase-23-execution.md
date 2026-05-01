# Phase 23 Execution Record

## Purpose

Track **Phase 23: Documentation Reorganization, Versioning, and Deploy Harness** per [Implementation Plan](./plan.md).

## Status

**Complete.**

## Work completed

### Version UX and deploy harness improvements

- Removed `dev` from all version strings; format is `0.1.0+r<N>` (main) or `0.1.0+r<N>-branch-slug` (branch)
- `scripts/deploy.sh` auto-tags HEAD on `main` (patch bump, pushed to origin) before computing version so `git describe` picks up the new tag immediately; branch deploys are never tagged
- Added `VersionPanel` to `SettingsPage` as the topmost section (before Network), fetching version via `fetchStatus()`
- Expanded `scripts/deploy.sh` header and `docs/runbooks/platform-bring-up.md` with SSH key setup steps, `~/.ssh/config` alias pattern, and full env var reference (`PI_TARGET`, `FORCE_BUILD`)
- Added log-reduction and SD card IO/corruption-risk task to Phase 32 Stabilization

### KiCad project renames

### Documentation reorganization

Renamed all phase-scoped living reference documents to artifact-based names:

| Old path | New path |
|---|---|
| `docs/hardware/phase-3-observation-bom.md` | `docs/hardware/observation-bom.md` |
| `docs/hardware/phase-4-analog-drive-bom.md` | `docs/hardware/analog-drive-bom.md` |
| `docs/hardware/phase-5-hdmi-ddc-transport.md` | `docs/hardware/hdmi-ddc-transport.md` |
| `docs/hardware/phase-6-protoboard-bom.md` | `docs/hardware/protoboard-bom.md` |
| `docs/hardware/phase-6-protoboard-schematic.md` | `docs/hardware/protoboard-schematic.md` |
| `docs/hardware/phase-20-pi5-gpio-schema.md` | `docs/hardware/pi5-gpio-schema.md` |
| `docs/runbooks/phase-9-platform-bring-up.md` | `docs/runbooks/platform-bring-up.md` |
| `docs/assets/hardware/phase-3-observation-schematic.svg` | `docs/assets/hardware/observation-schematic.svg` |
| `docs/assets/hardware/phase-4-analog-drive-schematic.svg` | `docs/assets/hardware/analog-drive-schematic.svg` |
| `docs/assets/hardware/phase-5-hdmi-ddc-transport-diagram.svg` | `docs/assets/hardware/hdmi-ddc-transport-diagram.svg` |
| `docs/assets/hardware/phase-6-raspberry-pi-pinout.svg` | `docs/assets/hardware/raspberry-pi-pinout.svg` |
| `hardware/kicad/phase-3-observation-reva/` | `hardware/kicad/observation-reva/` |
| `hardware/kicad/phase-4-analog-drive/` | `hardware/kicad/analog-drive/` |
| `hardware/kicad/phase-5-hdmi-ddc-intermediary/` | `hardware/kicad/hdmi-ddc-intermediary/` |
| `hardware/kicad/phase-6-protoboard-validation/` | `hardware/kicad/protoboard-validation/` |
| `hardware/kicad/phase-7-controller-board/` | `hardware/kicad/controller-board/` |
| `hardware/kicad/phase-7-hdmi-ddc-board/` | `hardware/kicad/hdmi-ddc-board/` |

All inbound links in execution records, the implementation plan, and internal document references updated to match. KiCad files within each directory renamed to match (e.g. `phase-4-analog-drive.kicad_sch` → `analog-drive.kicad_sch`); internal `(project "phase-N-...")` instance-tracking references updated throughout.

Added `docs/hardware/README.md` — index of all hardware reference documents with one-line descriptions and the naming rule.

**Naming rule (now documented):**
- `docs/hardware/` — artifact-named living references: BOMs, schematics, GPIO maps, signal characterization
- `docs/implementation/phase-*-execution.md` — frozen phase history; phase names stay here because they *are* the artifact
- `docs/assets/hardware/` — diagrams and images referenced by the above

### Versioning

- Added `backend/src/pi_deck/_version.py` to `.gitignore` (generated at deploy time)
- Updated `backend/src/pi_deck/__init__.py` to import `__version__` from `_version.py` with fallback to `"0.0.0-dev"` for local runs
- Added `os_version` and `python_version` fields to `StatusOut` (populated from `platform.platform(terse=True)` and `sys.version`)
- Updated `scripts/deploy.sh` to compute version from `git describe --tags --always` + branch name + deploy counter, write `_version.py` before rsync
- Created initial git tag `v0.1.0` on commit `0d5ce9b`

Version format:
- Main: `0.1.0+r<N>` (tag is always the displayed version; no "dev" suffix)
- Non-main branch: `0.1.0+r<N>-phase-x-implementation` (branch slug appended after counter)
- No tags, main: `0.0.0+r<N>`
- No tags, branch: `0.0.0+r<N>-branch-slug`

### Tagging workflow (automated by deploy.sh)

`scripts/deploy.sh` auto-tags on every deploy from `main`:

- If HEAD already has a `vX.Y.Z` tag, it is reused.
- Otherwise the latest tag's patch is incremented (`v0.1.0` → `v0.1.1`), the new tag is created locally and pushed to `origin` before the deploy proceeds.

Branch deploys are never auto-tagged. CI/CD automation is a future phase.

### Deploy harness

- Added SSH connectivity pre-check at the top of `scripts/deploy.sh`: one attempt, 5 s timeout, fail-fast
- Unreachable host prints an actionable `export PI_TARGET=…` message and exits immediately — no silent retry or continued execution

## Host health gate

*N/A — this phase is documentation, tooling, and non-functional backend metadata only; no new hardware paths or service behavior introduced.*
