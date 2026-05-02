# DDC VCP Scan — Phase 24 Investigation

Monitor: **Samsung C34J79x** (`SAM`, product code `0x0F1C`)
Host: Raspberry Pi 5 — I2C bus 13 (HDMI0 / `card2-HDMI-A-1`)
Tool: `scripts/ddc-scan.py`

## Methodology

Three independent passes were run to rule out any order-dependent or state-dependent response behaviour.
The retry policy in each pass: if the previous command succeeded but the current one fails, wait 5 s and retry once before moving on.

| Pass | File | Order | Codes scanned | Codes responding |
|------|------|-------|---------------|-----------------|
| 1 | `ddc-scan-20260501-153903` | Ascending (0x00→0xFF) | 256 | **32** |
| 2 | `ddc-scan-20260501-161242` | Descending (0xFD→0x00) — only the 224 that did not respond in Pass 1 | 224 | **0** |
| 3 | `ddc-scan-20260501-161655` | Random (all 256) | 256 | **32** |

**Conclusion: the monitor exposes exactly 32 VCP codes regardless of scan order.** No codes are shy or order-dependent. The capability string returned nothing in all three passes — brute-force was the only reliable method.

## Responding Codes (ground truth)

| Code | Name | Type | Current (Pass 1) | Max / SL |
|------|------|------|-----------------|----------|
| `0x02` | New Control Value | CNC | — | x00 xff x00 x02 |
| `0x0B` | Color Temperature Increment | CNC | — | xff xff x00 x32 |
| `0x0C` | Color Temperature Request | C | 40 | 170 |
| `0x10` | Brightness | C | 59 | 100 |
| `0x12` | Contrast | C | 75 | 100 |
| `0x14` | Select Color Preset | SNC | — | x04 |
| `0x16` | Red Video Gain | C | 70 | 100 |
| `0x18` | Green Video Gain | C | 70 | 100 |
| `0x1A` | Blue Video Gain | C | 70 | 100 |
| `0x52` | Active Control | CNC | — | x00 xff x00 x00 |
| `0x60` | Input Source | SNC | — | x04 (value meaning TBD) |
| `0x62` | Audio Speaker Volume | C | 3 | 100 |
| `0x6C` | Video Black Level: Red | C | 50 | 100 |
| `0x6E` | Video Black Level: Green | C | 50 | 100 |
| `0x70` | Video Black Level: Blue | C | 50 | 100 |
| `0x8D` | Audio Mute | SNC | — | x02 |
| `0xAA` | Screen Orientation | SNC | — | x00 |
| `0xAC` | Horizontal Frequency | C | 23364 | 65281 |
| `0xAE` | Vertical Frequency | C | 6000 | 65535 |
| `0xB2` | Flat Panel Sub-Pixel Layout | SNC | — | x01 |
| `0xB6` | Display Technology Type | SNC | — | x03 |
| `0xC0` | Display Usage Time | C | 200 | 65535 |
| `0xC6` | Application Enable Key | CNC | — | xff xff x00 x6f |
| `0xC8` | Display Controller ID | CNC | — | xff xff x00 x12 |
| `0xC9` | Display Firmware Level | CNC | — | xff xff x01 x20 |
| `0xCA` | OSD/Button Control | SNC | — | x02 |
| `0xCC` | OSD Language | SNC | — | x02 (English) |
| `0xD6` | Power Mode | SNC | — | x01 (On) |
| `0xDC` | Display Application | SNC | — | x02 |
| `0xDF` | VCP Version | CNC | — | x02 x01 (v2.1) |
| `0xFE` | Unknown — manufacturer-specific | CNC | — | x00 x02 x00 x02 |
| `0xFF` | Unknown — manufacturer-specific | CNC | — | x00 x01 x00 x00 |

## Notable observations

- **No capability string** — the monitor does not advertise supported codes; brute-force was required.
- **Retry logic fired heavily** — a successful read frequently causes the next query to fail. The 5 s retry is necessary for accurate results.
- **`0xAE` Vertical Frequency** read as `6000` in Pass 1 and `6010` in Pass 3 — minor variance, likely centihz (60.00 / 60.10 Hz).
- **`0xFE` and `0xFF`** respond but are not defined in the MCCS standard — manufacturer-specific, worth further investigation.
- **`0x60` Input Source** current value `x04` — exact Samsung mapping TBD (next step).
- **`0xD6` Power Mode** current value `x01` = On (MCCS standard: 1=On, 2=Standby, 3=Suspend, 4=Off).

## Next steps

1. Decode `0x60` Input Source: enumerate valid values by switching inputs and reading back.
2. Test `0xD6` Power Mode writes for standby/wake control.
3. Investigate `0xFE` and `0xFF` manufacturer-specific codes.
