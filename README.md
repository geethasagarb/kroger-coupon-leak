# Kroger Coupon Savings Leak

**How much digital-coupon savings do shoppers lose, where, and what fixes it?**

A product-analytics case study in Amplitude and Python.

> **Simulated data.** Event data is simulated in Python (8,000 shoppers, 997k events). Effects were seeded in the simulator, so the numbers show the *method*, not Kroger's real figures. Customer evidence comes from real Google Play reviews. Independent project; not affiliated with The Kroger Co.

![Overview: 83.6% realization, 53.8% capture, $52.2k never clipped, $15.5k failed at checkout](images/00_overview.png)

## The problem

Shoppers clip digital coupons, but discounts don't always apply at the register, and many offers are never clipped. In 1,999 real Google Play reviews of the Kroger app, *Digital coupons fail to apply* ranks #10 of 686 feedback themes (54 reviews, 1.7★ vs the app's 4.4★).

**North Star:** Coupon Savings Realization Rate = savings applied ÷ (applied + failed).

## Results

| Question | Answer |
| --- | --- |
| How much qualifying savings do shoppers get? | **54%** ($78.7k of $146.4k in 6 weeks) |
| Where does the rest go? | **36% never clipped**, 11% failed at checkout |
| Why do clipped coupons fail? | Wrong size 32%, limits 29%, POS sync lag 26%, wrong account 13%; clips <15 min before checkout fail **59%** |
| Does a failure hurt the business? | **5.4% fewer trips** over 8 weeks, ≈$130k in sales, 8× the coupons' value |
| Who to fix it for first? | Casual app users in-store and non-app loyalists: **60%** of leaked dollars |
| Does auto-apply work? | A/B test: realization **83.3% → 87.3%** (95% CI +3.5 to +4.5 pts), capture 61% → 82%, guardrails hold |

## What Kroger could do better

![Five fixes ranked by where the money leaks, each with its evidence](images/what_kroger_could_do_better.png)

<details>
<summary><b>See the analysis, step by step (7 charts)</b></summary>

**1. Is this a real problem?** (real reviews)
![What reviewers blame when coupons fail](images/01_voice_of_customer.png)

**2. Is the North Star moving?**
![Realization rate by week and experiment arm](images/02_north_star.png)

**3. Where do the savings go?**
![Qualifying savings by shopper segment](images/03_where_savings_go.png)

**4. Why do clipped coupons fail?**
![Lost savings by failure cause, and failure rate by clip timing](images/04_why_coupons_fail.png)

**5. Does a failure cost future trips?**
![Change in weekly trips after a first coupon failure](images/05_trust_cost.png)

**6. Who should Kroger fix it for first?**
![Leak by segment and channel; capture by channel and age](images/06_who_to_target.png)

**7. Did auto-apply fix it?**
![Auto-apply experiment results with 95% intervals](images/07_auto_apply_experiment.png)

</details>

## How I'd validate this with real data

- **Check the biggest claim first:** do never-clipped savings really outweigh checkout failures? That decides whether to fix clipping or the POS.
- **Weigh the business trade-offs of auto-apply:** brand-funded coupons may be paid per clip, and clipping is a signal of shopper intent. Auto-apply could cost both.
- **Add the tracking gaps:** coupon value on cart events, plus app errors. App reliability is the top real complaint and isn't modeled here.

## Methods and tools

Tracking plan → Python simulator (validated) → funnel and failure breakdown → matched retention comparison (avoids Simpson's paradox) → behavior segmentation → A/B test with sample-ratio and A/A checks, bootstrap 95% CIs and guardrails (one false alarm diagnosed) → dashboards → write-up.

**Tools:** Amplitude (tracking plan, funnels, retention, dashboards, AI Feedback), Python (pandas, NumPy, SciPy), D3.js.

## Repo

```
docs/        tracking plan · analysis memo (start here) · experiment brief & readout · case summary
simulator/   config (every seeded rate) · simulate · validate · send_to_amplitude (dry run by default)
analysis/    build_results.py: recomputes every number in the docs and dashboard
data/        result CSVs + real review counts by cause
dashboard/   interactive page (reads data/) + recommendations graphic source
images/      README screenshots
```

**Reproduce:** deterministic; same seed, same results.

```bash
pip install -r requirements.txt
python simulator/simulate.py && python simulator/validate.py && python analysis/build_results.py
python -m http.server 8000          # dashboard at http://localhost:8000/dashboard/
```

To load into your own Amplitude project, set `AMPLITUDE_API_KEY` as an environment variable and run `python simulator/send_to_amplitude.py --send`.

## Author

**Geetha Sagar Bonthu** · Analytics Engineer · [LinkedIn](https://www.linkedin.com/in/gitageetha) · [Portfolio](https://geethasagarb.in)
