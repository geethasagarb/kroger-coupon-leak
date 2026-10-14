# Kroger Coupon Leak · Analysis Memo

Oct 14, 2026 · Geetha Sagar Bonthu

## Bottom line

Kroger shoppers get only **54%** of the coupon savings they qualify for. The biggest leak isn't coupons failing at checkout (11%); it's coupons never clipped (36%, about $52k in six weeks). Fix it by applying offers automatically, starting with casual app users and non-app shoppers.

*Event data is simulated (8,000 shoppers, Jul 20 – Aug 30, 2026). Customer evidence is from real Google Play reviews.*

## Question

Where do shoppers lose digital-coupon savings, what does it cost Kroger, and what should be fixed first?

**Why now:** in all 1,999 Google Play reviews of the Kroger app collected, *Digital coupons fail to apply* ranks #10 of 686 feedback themes (complaints and requests) (54 reviews, 1.7★ vs the app's 4.4★). Reviewers say the app won't clip or scan coupons (37%), clipping is a chore and they want auto-apply (17%), and clipped coupons don't apply at the register (15%). Reviews say *what* goes wrong; this memo sizes it.

## What we found

1. **The leak is in dollars, not users.** 99.5% of app users get some coupon applied, but of $146.4k in qualifying savings only $78.7k reached receipts: $15.5k failed at checkout and $52.2k was never clipped.
2. **Wrong size is the top checkout failure.** Lost dollars split wrong size 32%, per-transaction limits 29%, POS sync lag 26%, wrong account 13%. Coupons clipped under 15 minutes before checkout fail 59% of the time vs about 12% otherwise. The service desk recovers only 7%.
3. **A failure costs future trips.** Compared with similar shoppers whose coupons worked, a first failure cuts trips by 5.4% over 8 weeks, about $130k in lost sales: 8× the face value of the coupons that failed.
4. **Behavior predicts the leak, not demographics.** Realization is flat at 83–84% for every age and Boost status. Casual app users shopping in-store (45% capture) and non-app loyalists (13% capture) hold 60% of leaked dollars. Age and Boost gaps vanish within a segment.
5. **Auto-apply works.** In a 6-week test, it raised realization from 83.3% to 87.3% (+4.0 points, 95% interval +3.5 to +4.5) and capture from 61% to 82%, at $0.84 more savings per order.

## Recommendation

| Who | What to do | Why |
| --- | --- | --- |
| Casual app users | Roll out auto-apply first | Biggest tested gain: capture 46% → 79% |
| Non-app loyalists | Auto-load top offers to the loyalty card | 13% capture; they won't open an app |
| In-store shoppers | Retry clips made in the last 15 minutes at checkout; warn on wrong size at the scanner | Sync lag and wrong size drive in-store failures |
| Every failure | Credit the coupon to the next order automatically | Service desk recovers 7%; failures cost 8× in later trips |
| App team | Fix clip, load and scan reliability | Top real complaint (37% of reviews) |

## Caveats

- **Simulated data.** Failure rates and effects were seeded in the simulator; the analysis recovers them, it doesn't discover them. Real Kroger rates will differ.
- **Never-clipped dollars are an estimate**, valued at each coupon's face value, because cart events carry no coupon value.
- **Trust cost is sales, not margin**, and it's diluted: shoppers in the comparison group can fail later too.
- **App reliability isn't modeled.** It's the top real complaint, so the true leak is likely larger.
- **Next step:** confirm with real Kroger data, starting with the gaps listed in the [tracking plan](01_tracking_plan.md).
