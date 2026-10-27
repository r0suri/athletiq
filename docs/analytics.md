# AthletIQ analytics engine

Deterministic, pure-Python calculations in `backend/app/domain/`. No I/O and no clock
reads: every result is computed relative to an explicit `as_of` date (the user's local
"today"), so the same inputs always give the same outputs.

> **Disclaimer.** The load and wellness indicators are heuristic estimates based on logged
> sessions and self-reported wellness. They are not medical measurements, are not medically
> validated, and do not predict injury.

## Modules

| Module | Responsibility |
|---|---|
| `models.py` | Framework-free domain types: `WorkoutRecord`, `DailyCheckIn`, `Goal` |
| `analytics.py` | Validation, windows, volume, load, consistency, wellness, `compute_summary` |
| `heuristics.py` | Rule-based flags with observed value, threshold and explanation |
| `goals.py` | Goal-specific targets and template-based progress summaries |

## Windows (inclusive)

| Window | Days |
|---|---|
| Current 7 days | `as_of - 6` .. `as_of` |
| Previous 7 days | `as_of - 13` .. `as_of - 7` |
| 28 days | `as_of - 27` .. `as_of` |
| Chronic baseline | `as_of - 27` .. `as_of - 7` (21 days, excludes the current week) |

Rolling windows avoid the "Monday cliff" of calendar weeks; calendar (ISO) weeks are used
only for history charts.

## Formulas

| Metric | Formula |
|---|---|
| Session load (AU) | `duration_min × RPE` (Foster session-RPE, RPE 1–10) |
| Weekly duration | `Σ duration_min` in the current 7 days |
| Run / ride distance | `Σ distance_km` per type; sessions without distance are counted in `sessions_missing_distance`, never as 0 km |
| Sessions | count of valid workouts |
| Training days | count of distinct dates with ≥ 1 valid workout |
| Rest days | `7 − training_days` |
| 7-day load `L7` | `Σ load` in the current 7 days |
| 28-day load `L28` | `Σ load` in the 28-day window |
| Weekly change % | `(L7 − L7_prev) / L7_prev × 100`; `null` when `L7_prev = 0` |
| Chronic weekly load | `Σ load(chronic baseline) / 3`; `null` with < 28 days of history |
| ACWR | `L7 / chronic`; `null` when chronic is `null` or 0 |
| Consistency % | 7-day blocks (of the last 4 that overlap the history) with ≥ goal target sessions ÷ blocks evaluated × 100 |
| Wellness averages | mean over **reported** days only; `null` when none reported |

Goal targets: strength 3, endurance 4, general fitness 3 sessions per 7 days.

**Uncoupled ACWR.** The chronic baseline excludes the current week. Including it (the
"coupled" form) lets a spike partially inflate its own denominator, a known criticism of ACWR.

## Validation

Workouts are excluded and counted by reason when: duration ≤ 0, > 24 h or not a number
(`non_positive_duration`, `duration_exceeds_24h`); RPE outside 1–10 (`rpe_out_of_range`);
negative distance (`invalid_distance`); date after `as_of` (`future_date`).
Wellness values outside their scale (sleep 0–24 h, fatigue/soreness 1–5) are treated as
missing and counted in `checkin_values_ignored`.

## Heuristic flags

| Flag | Triggered when | Evaluated only if |
|---|---|---|
| `weekly_load_jump` | weekly change > 30 % | previous-week load ≥ 150 AU |
| `acwr_spike` | ACWR > 1.5 | ACWR computable |
| `sustained_fatigue` | fatigue or soreness ≥ 4 on ≥ 3 days | ≥ 3 days with fatigue or soreness reported |
| `short_sleep` | mean sleep < 6.0 h | ≥ 3 nights reported |

Overall status: `insufficient_data` (nothing evaluable), `no_flags`, `caution` (1 triggered),
`elevated` (2+ triggered).

## Worked example (verify by hand)

`as_of` = 2026-10-27, goal = endurance. Reproduce with
`cd backend && python -m scripts.analytics_example`.

**Baseline weeks** (Sep 30–Oct 6, Oct 7–13, Oct 14–20), each containing:
run 40 min @ RPE 5, 7 km (200 AU) · strength 50 min @ 6 (300 AU) · ride 60 min @ 5, 25 km (300 AU)
→ **800 AU per week**.

**Current week** (Oct 21–27):

| Date | Workout | Load |
|---|---|---|
| Oct 21 | run 45 min @ 6, 8 km | 270 |
| Oct 22 | strength 60 min @ 7 | 420 |
| Oct 24 | ride 90 min @ 6, 40 km | 540 |
| Oct 24 | run 30 min @ 4, 5 km | 120 |
| Oct 26 | run 50 min @ 8, 10 km | 400 |

| Metric | Hand calculation | Result |
|---|---|---|
| Sessions / training days / rest days | 5 workouts on Oct 21, 22, 24, 26 | 5 / 4 / 3 |
| Duration | 45 + 60 + 90 + 30 + 50 | 275 min |
| `L7` | 270 + 420 + 540 + 120 + 400 | 1750 AU |
| `L7_prev` | baseline week Oct 14–20 | 800 AU |
| `L28` | 3 × 800 + 1750 | 4150 AU |
| Weekly change | (1750 − 800) / 800 × 100 | +118.75 % |
| Chronic | 2400 / 3 | 800 AU |
| ACWR | 1750 / 800 | 2.1875 |
| Run / ride distance | 8 + 5 + 10 / 40 | 23 km / 40 km |
| Consistency | target 4: only current week has ≥ 4 sessions → 1 / 4 | 25 % |
| Avg sessions per week | (3 + 3 + 3 + 5) / 4 | 3.5 |

**Check-ins:** Oct 24 fatigue 4 · Oct 25 sleep 5.0 h, fatigue 5, soreness 3 · Oct 26 sleep 5.5 h, fatigue 4.

| Metric | Hand calculation | Result |
|---|---|---|
| Avg fatigue | (4 + 5 + 4) / 3 | 4.33 |
| Avg soreness | one report | 3.0 |
| Avg sleep | (5.0 + 5.5) / 2 | 5.25 h (2 nights) |

**Flags:** `weekly_load_jump` triggered (118.75 > 30) · `acwr_spike` triggered (2.19 > 1.5) ·
`sustained_fatigue` triggered (3 days ≥ 4) · `short_sleep` insufficient data (2 nights < 3)
→ overall **elevated**.
