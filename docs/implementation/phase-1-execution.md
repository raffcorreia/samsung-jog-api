# Phase 1 Execution Record

## Purpose

This document records the actual execution of `Phase 1: Host Preparation and Conservative OS Cleanup` on the current Raspberry Pi host.

It complements:

- [Implementation Plan](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/implementation/plan.md)
- [Prepare Raspberry Pi](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/runbooks/prepare-raspberry-pi.md)

## Target Host

- hostname: `pi-deck`
- access path: remote `ssh`
- operating system: `Raspbian GNU/Linux 13 (trixie)`
- kernel: `Linux 6.18.18-v7+ #1964 SMP Wed Mar 18 19:01:55 GMT 2026 armv7l`
- execution date: `2026-03-24`

## Scope of this execution

This execution focused on the conservative cleanup portion of Phase 1.

It did not include:

- kiosk/browser bring-up
- application installation
- backup image creation

## Baseline Findings

### Before metrics

Captured at `2026-03-24T16:45:35-0400`.

- uptime: `20 min`
- load average: `0.67`, `0.38`, `0.17`
- root filesystem: `57G` size, `3.1G` used, `52G` available, `6%` used
- memory: `920Mi` total, `136Mi` used, `480Mi` free, `372Mi` buff/cache, `783Mi` available
- swap: `919Mi`, `0B` used

### Before enabled service footprint

Services relevant to the cleanup decision:

- `avahi-daemon.service` enabled
- `bluetooth.service` enabled
- `cloud-init-local.service` enabled
- `cloud-init-main.service` enabled
- `cloud-init-network.service` enabled
- `ModemManager.service` enabled
- `udisks2.service` enabled
- `NetworkManager.service` enabled
- `ssh.service` enabled
- `systemd-timesyncd.service` enabled
- `wpa_supplicant.service` enabled

### Before installed cleanup candidates

- `avahi-daemon`
- `bluez`
- `cloud-guest-utils`
- `cloud-init`
- `modemmanager`
- `rpi-cloud-init-mods`
- `rpi-connect-lite`
- `udisks2`

Also present after cleanup analysis:

- `bluez-firmware`

### Before key filesystem state

- `/etc/cloud` present
- `/etc/netplan` present
- `/etc/netplan/90-NM-75a1216a-9d1a-30cd-8aca-ace5526ec021.yaml` present
- `/etc/netplan/90-NM-a0bbdc8c-c561-33e1-a83c-200a7848df5e.yaml` present

## Cleanup Decisions

The following packages were approved for removal because they were not needed for the control-deck role and did not support the intended kiosk or hardware-control path:

- `avahi-daemon`
- `bluez`
- `cloud-guest-utils`
- `cloud-init`
- `modemmanager`
- `rpi-cloud-init-mods`
- `rpi-connect-lite`
- `udisks2`

The following supporting components were intentionally preserved:

- `NetworkManager`
- `ssh`
- `systemd-timesyncd`
- `wpa_supplicant`
- Raspberry Pi hardware and GPIO tooling already installed for the project

`bluez-firmware` remained installed because it was not an active service and was not part of the minimal conservative purge set.

## Commands Executed

The cleanup was executed with:

```bash
sudo apt-get update
sudo apt-get purge -y avahi-daemon bluez modemmanager rpi-connect-lite udisks2 cloud-init cloud-guest-utils rpi-cloud-init-mods
sudo apt-get autoremove -y --purge
```

## Package and Service Changes

### Explicitly purged packages

From `apt` history:

- `avahi-daemon`
- `bluez`
- `cloud-guest-utils`
- `cloud-init`
- `modemmanager`
- `rpi-cloud-init-mods`
- `rpi-connect-lite`
- `udisks2`

### Autoremoved packages

Follow-up autoremove purged dependencies no longer required by the removed stack, including:

- `libavahi-*`
- `libblockdev-*`
- `libmbim-*`
- `libqmi-*`
- `libudisks2-0`
- `libnss-mdns`
- `libnss3`
- several `cloud-init` Python dependencies such as `python3-jinja2`, `python3-jsonschema`, and related helper packages

### Final package count

- after cleanup: `595` installed packages

The before package count was not captured as a standalone number, but the `apt` history and explicit before/after package presence above capture the Phase 1 cleanup set accurately.

## Files and Directories Changed

### Removed by package purge

These configuration directories no longer exist after cleanup:

- `/etc/cloud`
- `/etc/avahi`
- `/etc/bluetooth`

### Preserved

- `/etc/netplan`
- both `NetworkManager` netplan YAML files under `/etc/netplan`

### Manual cleanup after package removal

After reviewing the residual `cloud-init` state, the following manual cleanup was also performed:

- removed `/var/lib/cloud`

This was stale bootstrap state from the removed `cloud-init` stack, not an active runtime dependency.

## After State

### After metrics

Captured at `2026-03-24T16:49:13-0400`.

- uptime: `24 min`
- load average: `1.10`, `0.89`, `0.43`
- root filesystem: `57G` size, `3.1G` used, `52G` available, `6%` used
- memory: `920Mi` total, `136Mi` used, `362Mi` free, `489Mi` buff/cache, `783Mi` available
- swap: `919Mi`, `0B` used

### After relevant services

Still enabled and expected:

- `NetworkManager.service`
- `ssh.service`
- `systemd-timesyncd.service`
- `wpa_supplicant.service`

Still running and expected:

- `NetworkManager.service`
- `ssh.service`
- `systemd-timesyncd.service`
- `wpa_supplicant.service`

No failed systemd units were reported after cleanup.

### Removed services no longer present in the enabled-service list

- `avahi-daemon.service`
- `bluetooth.service`
- `cloud-init-local.service`
- `cloud-init-main.service`
- `cloud-init-network.service`
- `ModemManager.service`
- `udisks2.service`

## Validation Results

The following checks passed after cleanup:

- `ssh` access remained available throughout the cleanup
- `NetworkManager` remained enabled and running
- `wpa_supplicant` remained enabled and running
- `systemd-timesyncd` remained enabled and running
- no failed systemd units were reported
- target cleanup packages were absent after cleanup

## Observations

- The host was already relatively lean before cleanup: only `3.1G` used on the root filesystem.
- The biggest Phase 1 value here was reducing unnecessary services and cloud/remote-access tooling, not reclaiming massive disk space.
- `cloud-init` had clearly been used to bootstrap this image and left both configuration and state behind.
- `bluez-firmware` remains installed even though `bluez` was removed. This is acceptable for the current conservative cleanup pass.

## Pi 5 Host Differences (Phase 20 findings — 2026-04-28)

When repeating Phase 1 on a Raspberry Pi 5 (`pi-deck5`, Debian 13 Trixie, kernel 6.12.75+rpt-rpi-2712 aarch64), the following differences apply:

### IPv6 absent — apt fails before any operation

The Pi 5 on this network has no IPv6 connectivity. `apt-get update` attempts IPv6 first and hangs. Fix this before any apt operation:

```bash
echo 'Acquire::ForceIPv4 "true";' | sudo tee /etc/apt/apt.conf.d/99force-ipv4
```

This file must exist before running any `apt` command, including the initial cleanup.

### Package baseline

- Pi 5 starting package count: **645** (vs Pi 2 baseline not captured; Pi 2 was ~595 post-cleanup)
- Pi 5 post-cleanup count: **583**
- `rpi-connect-lite` was present on the Pi 5 image and was included in the purge set. If it is absent on a given image, omit it from the purge command.

### Packages purged on Pi 5

```bash
sudo apt-get purge -y avahi-daemon bluez modemmanager rpi-connect-lite udisks2 cloud-init cloud-guest-utils rpi-cloud-init-mods
sudo apt-get autoremove -y --purge
```

### EEPROM bootloader update (Pi 5 only)

The Pi 5 EEPROM bootloader should be updated during host preparation. The Pi 2 does not have an EEPROM bootloader:

```bash
sudo rpi-eeprom-update -a
# Then reboot to apply.
```

On this bring-up the bootloader was updated from `1746713597` (2025-05-08) to `1765222194` (2025-12-08).

## Open Issues

- A backup image still needs to be created after this cleaned baseline is accepted.
- The repo-side helper scripts in `scripts/host/` are still uncommitted as of this execution record.

## Phase 1 Exit Decision

Phase 1 is operationally close to complete.

What is complete:

- host state assessed
- conservative cleanup applied
- residual `cloud-init` state removed
- before and after state documented
- core network, SSH, and time-sync services preserved

What still remains before the phase can be treated as fully complete:

- create and store the backup image of the cleaned host
- commit the host-preparation scripts if they are accepted
