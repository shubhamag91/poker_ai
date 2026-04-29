# Postflop Baseline v1

Reference frequencies for postflop decision spots. Hand-coded baselines with TODO markers to replace with measured/solver values later.

## Spot Count (v1)

| Type | Count |
|------|-------|
| CBET | 31 |
| DONK | 6 |
| PROBE | 8 |
| **Total** | **45** |

## CBET Baselines

### SRP IP PFR (shallow)

| Board Bucket | Small | Big | Check |
|--------------|-------|-----|-------|
| A_HIGH_DRY | 0.35 | 0.20 | 0.45 |
| BROADWAY_STATIC | 0.30 | 0.25 | 0.45 |
| MID_CONNECTED | 0.35 | 0.15 | 0.50 |
| PAIRED | 0.30 | 0.10 | 0.60 |
| MONOTONE | 0.25 | 0.10 | 0.65 |

### SRP IP PFR (deep)

| Board Bucket | Small | Big | Check |
|--------------|-------|-----|-------|
| A_HIGH_DRY | 0.30 | 0.25 | 0.45 |
| BROADWAY_STATIC | 0.25 | 0.25 | 0.50 |
| MID_CONNECTED | 0.30 | 0.15 | 0.55 |

### SRP OOP Defender (shallow)

All check on all textures (default OOP behavior in SRP).

### 3BP IP (shallow)

| Board Bucket | Small | Big | Check |
|--------------|-------|-----|-------|
| ACE_HIGH | 0.40 | 0.20 | 0.40 |
| KING_HIGH | 0.35 | 0.20 | 0.45 |
| LOW_STATIC | 0.30 | 0.15 | 0.55 |
| MID_DYNAMIC | 0.25 | 0.10 | 0.65 |
| PAIRED | 0.25 | 0.10 | 0.65 |
| MONOTONE | 0.20 | 0.05 | 0.75 |

### 3BP OOP (shallow)

All check on all textures.

### BVB IP PFR (shallow)

| Board Bucket | Small | Big | Check |
|--------------|-------|-----|-------|
| HIGH_CARD_STATIC | 0.40 | 0.20 | 0.40 |
| LOW_DISCONNECTED | 0.30 | 0.25 | 0.45 |
| LOW_CONNECTED | 0.35 | 0.15 | 0.50 |
| PAIRED | 0.30 | 0.10 | 0.60 |
| MONOTONE | 0.25 | 0.10 | 0.65 |

### BVB OOP (shallow)

All check on all textures.

## DONK Lead Baselines

| Spot | Small | Big | Check |
|------|-------|-----|-------|
| SRP OOP A_HIGH_DRY | 0.05 | 0.00 | 0.95 |
| SRP OOP BROADWAY_STATIC | 0.05 | 0.00 | 0.95 |
| SRP OOP MID_CONNECTED | 0.10 | 0.05 | 0.85 |
| SRP OOP PAIRED | 0.10 | 0.05 | 0.85 |
| SRP OOP MONOTONE | 0.15 | 0.05 | 0.80 |

## Probe Baselines (OOP PFR)

| Spot | Small | Big | Check |
|------|-------|-----|-------|
| SRP OOP A_HIGH_DRY | 0.10 | 0.05 | 0.85 |
| SRP OOP BROADWAY_STATIC | 0.10 | 0.05 | 0.85 |
| SRP OOP MID_CONNECTED | 0.15 | 0.10 | 0.75 |
| SRP OOP PAIRED | 0.15 | 0.05 | 0.80 |
| SRP OOP MONOTONE | 0.20 | 0.10 | 0.70 |

## Turn Barrel Baselines (v1.1)

| Spot | Position | Board | Barrel | Check Back |
|------|----------|-------|-------|-------------|
| srp_ip_pfr | IP | A_HIGH_DRY | 0.40 | 0.50 |
| srp_ip_pfr | IP | MID_CONNECTED | 0.25 | 0.60 |
| srp_oop_caller | OOP | A_HIGH_DRY | 0.15 | 0.70 |

## River Bet Baselines (v1.1)

| Spot | Position | Board | Bet | Check |
|------|----------|-------|-----|-------|
| srp_ip_pfr | IP | A_HIGH_DRY | 0.45 | 0.45 |
| srp_oop_caller | OOP | MID_CONNECTED | 0.20 | 0.65 |

## TODO

- [ ] Calibrate with solver data for each spot
- [x] Turn follow-through (C.3) - infrastructure added
- [ ] Add more turn/river baseline definitions for full coverage
- [ ] Add multiway variants
- [ ] Add 3bet pot variants

## API

```python
from postflop_baseline import get_cbet_baseline, compare_frequency

baseline = get_cbet_baseline("srp_ip_pfr", "IP", "A_HIGH_DRY", "shallow")
result = compare_frequency("small_bet", actual_freq, baseline)
```

## Version

v1.0 - 2026-04-29