# Generator 3.0.0: before and after

Written by `python -m scripts.generator_3_0_0_report` (ADR 0047). Generator 2.x held
each load at `source value × Σ original shape` and fitted its amplitude; 3.0 binds the
source value (commercial, shared water) or uses ResStock units (apartments).

## Commercial loads (every 10th recipe, seeds 42 and 51)

| Load | Loads | Annual 3.0 / 2.x, p05 / median / p95 | 2.x peak above rating | 2.x peak / rating, max |
|---|---:|---|---:|---:|
| electric_equipment | 162 | 0.746 / 0.910 / 1.357 | 45% | 1.29 |
| gas_equipment | 2 | 0.901 / 0.930 / 0.958 | 0% | 0.21 |
| lighting | 184 | 0.792 / 0.837 / 1.140 | 62% | 1.21 |

## Shared hot-water services (every variant, seed 42)

306 variants: annual volume 3.0 / 2.x 0.726 / 0.886 / 1.288 (p05 / median / p95); the 2.x peak flow exceeded the source peak in 29% (max 2.11×). In 3.0 the peak is the source peak × the schedule maximum.

## Apartment units (Hickory NC, 4A, 80 m², 25 units per resident count, seed 42)

| Programme | Residents | Electricity kWh/yr, p05 / median / p95 | Other fuels kWh/yr, median | Hot water m³/yr, median |
|---|---|---|---:|---:|
| 90.1-2007 Midrise | 2.x prototype | 4042 | 0 | 54.8 |
| 90.1-2007 Midrise | 1 | 1903 / 3352 / 5204 | 0 | 24.2 |
| 90.1-2007 Midrise | 2 | 1991 / 3388 / 5695 | 0 | 48.4 |
| 90.1-2007 Midrise | 3 | 2696 / 3612 / 4602 | 727 | 72.6 |
| 90.1-2007 Midrise | 4 | 2257 / 3964 / 7422 | 821 | 96.8 |
| 90.1-2007 Highrise | 2.x prototype | 3683 | 0 | 54.8 |
| 90.1-2007 Highrise | 1 | 1976 / 3463 / 5204 | 0 | 24.2 |
| 90.1-2007 Highrise | 2 | 2041 / 3388 / 5789 | 0 | 48.4 |
| 90.1-2007 Highrise | 3 | 2794 / 3769 / 5476 | 0 | 72.6 |
| 90.1-2007 Highrise | 4 | 2535 / 4156 / 7670 | 0 | 96.8 |

The 2.x prototype figures are per unit regardless of residents; 2.x had no gas in units.
