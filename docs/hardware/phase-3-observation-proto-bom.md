# Phase 3 Observation Proto BOM

## Purpose

This BOM defines the components for `phase-3-observation-proto`: a through-hole discrete prototype implementing Candidate D (comparator-based) observation of `KEY_ADC2`, `KEY_ADC1`, and `KEY_LED`.

The proto board takes its inputs from the buffered outputs of the `phase-3-observation-reva` op-amp board (test points `KEY_ADC2_BUF`, `KEY_ADC1_BUF`, `KEY_LED_BUF`) and outputs one-hot digital decoded directional states plus `KEY_ADC1` and `KEY_LED` states to the Raspberry Pi host.

All components are through-hole for protoboard assembly. This is a validation prototype, not a PCB order.

## Design Summary

- 6 discrete NPN differential pairs decode analog states into digital outputs
- 4 pairs decode `KEY_ADC2` into a thermometer code, then a 74HC86 XOR gate converts to one-hot
- 1 pair decodes `KEY_ADC1` (center press detect)
- 1 pair decodes `KEY_LED` state
- `UP` signal comes directly from the 4th comparator output (no XOR gate needed)

## Reference Voltage Generation

A 5-resistor ladder from 3.3V to GND generates 4 reference voltages for the `KEY_ADC2` differential pairs:

| Node   | Voltage | Threshold between         |
|--------|---------|---------------------------|
| Vref1  | 3.09V   | idle (3.29V) and left (2.88V) |
| Vref2  | 2.52V   | left (2.88V) and right (2.16V) |
| Vref3  | 1.76V   | right (2.16V) and down (1.35V) |
| Vref4  | 0.68V   | down (1.35V) and up (0.01V)    |

`Vref3` (1.76V) is reused as the `KEY_ADC1` threshold (idle 3.29V, center 0.01V — any value between 0.5V and 2.5V works).

`Vref4` (0.68V) is reused as the `KEY_LED` threshold (inactive 0V, active 2.7V — any value between 0.1V and 2.5V works).

## BOM

### Active Components

| RefDes   | Qty | Part     | Package | Purpose |
|----------|-----|----------|---------|---------|
| Q1–Q12   | 12  | BC547    | TO-92   | NPN differential pairs (6 pairs) |
| U1       | 1   | 74HC86   | DIP-14  | Quad XOR gate for thermometer-to-one-hot decode |

### Resistors (all axial, 1/4W or 1/8W)

| RefDes   | Qty | Value  | Purpose |
|----------|-----|--------|---------|
| RL1      | 1   | 620 Ω  | Ladder: 3.3V → Vref1 |
| RL2      | 1   | 1.8 kΩ | Ladder: Vref1 → Vref2 |
| RL3      | 1   | 2.2 kΩ | Ladder: Vref2 → Vref3 |
| RL4      | 1   | 3.3 kΩ | Ladder: Vref3 → Vref4 |
| RL5      | 1   | 2.2 kΩ | Ladder: Vref4 → GND |
| R6–R11   | 6   | 10 kΩ  | Collector pull-up resistors (Rc_a, output transistor of each pair) |
| R12–R17  | 6   | 10 kΩ  | Tail resistors (joined emitters to GND, one per pair) |

### Capacitors (ceramic)

| RefDes | Qty | Value  | Purpose |
|--------|-----|--------|---------|
| C1     | 1   | 100 nF | Decoupling on 3.3V near U1 |
| C2     | 1   | 100 nF | Decoupling on 3.3V near J2 |

### Connectors

| RefDes | Qty | Part                       | Purpose |
|--------|-----|----------------------------|---------|
| J1     | 1   | 1×4 pin header, 2.54mm     | Input from op-amp board: GND, KEY_ADC2_BUF, KEY_ADC1_BUF, KEY_LED_BUF |
| J2     | 1   | 1×8 pin header, 2.54mm     | Host output: 3V3, GND, LEFT, RIGHT, DOWN, UP, KEY1_IN, LED_IN |

## Differential Pair Mapping

| Pair | Q_a (signal) | Q_b (ref) | Signal input   | Reference | Output net | Output to |
|------|-------------|-----------|----------------|-----------|------------|-----------|
| 1    | Q1          | Q2        | KEY_ADC2_BUF  | Vref1     | OUT1       | U1 gate A input |
| 2    | Q3          | Q4        | KEY_ADC2_BUF  | Vref2     | OUT2       | U1 gates A, B inputs |
| 3    | Q5          | Q6        | KEY_ADC2_BUF  | Vref3     | OUT3       | U1 gates B, C inputs |
| 4    | Q7          | Q8        | KEY_ADC2_BUF  | Vref4     | OUT4       | U1 gate C input + J2.6 directly |
| 5    | Q9          | Q10       | KEY_ADC1_BUF  | Vref3     | KEY1_IN    | J2.7 |
| 6    | Q11         | Q12       | KEY_LED_BUF   | Vref4     | LED_IN     | J2.8 |

Output polarity per pair: Q_a collector is HIGH when signal < reference, LOW when signal > reference.

## Output Signal Polarities

| J2 Pin | Signal   | Active state |
|--------|----------|--------------|
| 3      | LEFT     | HIGH when KEY_ADC2 is in left state |
| 4      | RIGHT    | HIGH when KEY_ADC2 is in right state |
| 5      | DOWN     | HIGH when KEY_ADC2 is in down state |
| 6      | UP       | HIGH when KEY_ADC2 is in up state (OUT4 direct) |
| 7      | KEY1_IN  | HIGH when KEY_ADC1 center pressed |
| 8      | LED_IN   | LOW when KEY_LED is active (active-low) |

## XOR Decode Logic

```
OUT1 (Q1 collector) ─┬── XOR ── LEFT   (J2 pin 3)
OUT2 (Q3 collector) ─┘

OUT2 (Q3 collector) ─┬── XOR ── RIGHT  (J2 pin 4)
OUT3 (Q5 collector) ─┘

OUT3 (Q5 collector) ─┬── XOR ── DOWN   (J2 pin 5)
OUT4 (Q7 collector) ─┘

OUT4 (Q7 collector) ──────────── UP    (J2 pin 6, direct — no XOR)
```

The 4th XOR gate in the 74HC86 (pins 11, 12, 13) is spare; inputs tied to GND.

## Notes

- `Q_b` (reference transistor) collector connects directly to 3.3V — no collector resistor needed since current is limited by the tail resistor
- All `Rc_a` (R6–R11) and `Rtail` (R12–R17) are 10 kΩ, giving LOW output ≈ 0.65V and HIGH output ≈ 3.3V — compatible with 74HC86 CMOS input thresholds
- `LED_IN` polarity is inverted relative to physical LED state — software should treat it as active-low
- This proto board is intended to validate Candidate D before committing to a Rev B observation board

## KiCad Files

- Schematic: `hardware/kicad/phase-3-observation-proto/phase-3-observation-proto.kicad_sch`
- Project: `hardware/kicad/phase-3-observation-proto/phase-3-observation-proto.kicad_pro`
