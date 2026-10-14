# Kroger Coupon Leak · Auto-Apply Experiment Brief & Readout

Oct 14, 2026 · Geetha Sagar Bonthu

## Brief (written before launch)

**Hypothesis:** if eligible offers apply automatically, more of the savings shoppers qualify for reaches their receipt, because forgotten clips and last-minute sync failures go away.

| Item | Plan |
| --- | --- |
| Who | App users only; non-app shoppers excluded |
| Split | 50/50, randomized by shopper |
| Control | Manual clipping (today's experience) |
| Treatment | Eligible offers auto-applied at checkout |
| Dates | 6 weeks, Aug 31 – Oct 11, 2026 |
| Primary metric | Realization rate = savings applied ÷ (applied + failed) |
| Secondary | Capture rate (incl. never-clipped), savings per order |
| Guardrails | Net basket after savings, service desk visits per 1,000 orders, trips per shopper per week |
| Sample | ~2,800 shoppers per arm; detects a change of 0.84 points (80% power, 5% significance) |

**Decision rule:** ship if the primary metric's 95% interval is above zero and no guardrail gets significantly worse. If a guardrail trips, investigate before shipping.

## Readout

Auto-apply raised realization by **4.0 points** (83.3% → 87.3%), well above the 0.84 the test was sized to detect. Data is simulated.

| Metric | Role | Control | Auto-apply | Change (95% interval) | Verdict |
| --- | --- | --- | --- | --- | --- |
| Realization rate | Primary | 83.3% | 87.3% | +4.0 pts (+3.5 to +4.5) | Win |
| Capture rate | Secondary | 60.7% | 82.5% | +21.7 pts (+20.9 to +22.5) | Win |
| Savings per order | Secondary | $2.29 | $3.13 | +$0.84 (+$0.78 to +$0.90) | Expected cost |
| Trips per shopper per week | Guardrail | 0.94 | 0.94 | −0.1% (−2.5% to +2.3%) | Holds |
| Service desk visits per 1,000 orders | Guardrail | 42.3 | 38.9 | −8% (−19% to +3%) | Holds |
| Net basket after savings | Guardrail | $79.40 | $76.79 | −3.3% (−5.0% to −1.6%) | Flagged, then cleared |

**By segment:** casual app users gained most (capture 46% → 79%), then delivery/pickup (58% → 81%) and power clippers (75% → 86%).

**Checks:** arm sizes 2,766 vs 2,834 (sample-ratio p = 0.36); no gap between arms before launch. Intervals are user-level bootstrap.

## Decision and learnings

**Decision: ship auto-apply, starting with casual app users.** Keep 10% of shoppers on manual clipping for 4 more weeks to confirm basket size holds.

- **The basket flag was a false alarm.** The simulator gives auto-apply no effect on basket size, and before launch the weekly gap between arms already moved by about $2. A heavy-tailed metric produced a significant-looking dip by chance. In a real test: check it with a robust version (median or capped values), then decide.
- **The cost is real but small.** $0.84 more savings per order is money shoppers were already entitled to, and failures cost about 8× their value in lost trips.
- **Trips didn't move in 6 weeks.** The trust benefit likely needs a longer window to show up.
- **Effects were seeded.** The test recovers what the simulator built in; it proves the method, not Kroger's real numbers.
