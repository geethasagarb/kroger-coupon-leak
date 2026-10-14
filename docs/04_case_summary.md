# Kroger Coupon Leak · Case Summary

Oct 14, 2026 · Geetha Sagar Bonthu

## The case in five lines

| | |
| --- | --- |
| **Problem** | Kroger shoppers clip digital coupons, but discounts don't always apply, and non-app shoppers miss digital savings entirely. |
| **Evidence** | Real Google Play reviews: *Digital coupons fail to apply* ranks #10 of 686 feedback themes across 1,999 reviews (54 reviews, 1.7★ vs the app's 4.4★). |
| **Analysis** | Shoppers got 54% of qualifying savings; 36% was never clipped and 11% failed at checkout. A failure cuts later trips 5.4%, costing 8× the coupon's value. |
| **Recommendation** | Auto-apply offers, starting with casual app users; auto-load offers to the card for non-app shoppers. |
| **Impact** | In a 6-week A/B test, auto-apply raised realization 83.3% → 87.3% and capture 61% → 82%, at $0.84 more savings per order. |

*Event data is simulated (8,000 shoppers, 997k events); reviews are real. Independent portfolio project, not affiliated with The Kroger Co.*

## What I did

1. Wrote a tracking plan: 10 events, 7 user properties, loaded into Amplitude.
2. Built a Python simulator (8,000 shoppers, 12 weeks) with seeded failure causes, validated it, and loaded 997k events.
3. Pulled 1,999 real Play Store reviews with Amplitude AI Feedback and hand-tagged the 54 coupon-failure reviews by cause.
4. Sized the leak with funnels, failure breakdowns, a matched retention comparison and segmentation.
5. Designed and read out an auto-apply A/B test with guardrails, and caught a false-alarm guardrail.

**Tools:** Amplitude (tracking plan, charts, dashboards, AI Feedback), Python (pandas, NumPy), bootstrap statistics.

## Documents

- [Tracking plan](01_tracking_plan.md)
- [Analysis memo](02_analysis_memo.md)
- [Experiment brief & readout](03_experiment_brief_and_readout.md)
