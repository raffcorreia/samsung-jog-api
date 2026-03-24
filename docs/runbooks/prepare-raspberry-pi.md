# Prepare Raspberry Pi

## Purpose

Prepare the Raspberry Pi host so it starts from a clean, predictable baseline before control-deck software is installed.

This runbook is the operational output of `Phase 1: Host Preparation and Conservative OS Cleanup`.

## Principles

- keep cleanup conservative
- capture the host state before and after changes
- do not remove packages or disable services without documenting why
- keep generated host artifacts out of git
- prefer repeatable scripts over undocumented one-off shell history

## Generated artifacts

Phase 1 host-preparation artifacts are expected to live under:

- `artifacts/host-prep/`

That directory is ignored by git because it may contain machine-specific details such as private IP addresses, package inventories, and service lists.

## Preparation checklist

1. verify the Raspberry Pi hardware, storage, power supply, and network connectivity
2. capture a pre-cleanup host baseline
3. review cleanup candidates conservatively
4. apply only the approved cleanup decisions
5. capture a post-cleanup baseline
6. run a smoke check
7. create a backup image once the baseline is accepted

## Scripts

The repo now includes these Phase 1 helper scripts:

- `scripts/host/capture_host_state.sh`
- `scripts/host/review_cleanup_candidates.sh`
- `scripts/host/apply_conservative_cleanup.sh`
- `scripts/host/post_cleanup_smoke_check.sh`

There is also a cleanup-config template at:

- `config/host-prep/cleanup.conf.example`

Copy that template to a host-local path before editing it for the actual Raspberry Pi.

## Recommended workflow

### 1. Capture the pre-cleanup baseline

Run:

```bash
scripts/host/capture_host_state.sh
```

This writes a timestamped snapshot under `artifacts/host-prep/`.

### 2. Review the default cleanup candidates

Run:

```bash
scripts/host/review_cleanup_candidates.sh
```

This report is only a review aid. It does not remove anything.

### 3. Create a host-local cleanup config

Start from:

```bash
cp config/host-prep/cleanup.conf.example /etc/samsung-jog-api/cleanup.conf
```

Then edit the package and service lists for the actual Raspberry Pi.

### 4. Dry-run the cleanup

Run:

```bash
scripts/host/apply_conservative_cleanup.sh --config /etc/samsung-jog-api/cleanup.conf
```

Review the proposed commands before making any change.

### 5. Apply the approved cleanup

Run:

```bash
scripts/host/apply_conservative_cleanup.sh --config /etc/samsung-jog-api/cleanup.conf --apply
```

### 6. Capture the post-cleanup baseline

Run:

```bash
scripts/host/capture_host_state.sh
```

### 7. Run the smoke check

Run:

```bash
scripts/host/post_cleanup_smoke_check.sh
```

### 8. Create a backup image

Once the host baseline is accepted:

- create a backup image of the SD card
- label it with the date and Phase 1 completion state
- keep a short note describing what changed between the stock image and the accepted baseline

## Notes

- this checklist is operational guidance, not a product requirement
- changes should be documented so the host can be rebuilt consistently later
- host cleanup is not the same thing as kiosk bring-up; kiosk setup belongs later in the implementation plan
