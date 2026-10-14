# Kroger Coupon Leak · Tracking Plan

Oct 14, 2026 · Geetha Sagar Bonthu

## Purpose

This plan defines the 10 events and 7 user properties used to measure the Coupon Savings Realization Rate in Amplitude. All event data is **simulated** (Python, seed 42); every user carries `dataset = simulated_v1`.

**Conventions:** event names are `object_action` in snake_case; property names are snake_case; enums are lowercase. Each clipped coupon on a purchased item produces exactly one `coupon_applied` or one `coupon_failed`, so the North Star's denominator is complete.

## Events

| Event | Fires when | Properties (type) | Example |
| --- | --- | --- | --- |
| `app_opened` | App comes to the foreground | none | none |
| `offers_viewed` | Shopper opens a coupon list | `offer_count` (number), `source` (home / weekly_ad / search / push) | 42, weekly_ad |
| `coupon_clipped` | Shopper taps Clip | `coupon_id`, `category`, `brand` (string); `discount_value` (number); `offer_type` (personalized / generic); `minutes_before_checkout` (number); `eligible_size` (string) | CPN-10482, dairy, $1.50, personalized, 8, 32oz |
| `item_added_to_cart` | Item added in app or scanned at the register | `product_id`, `category`, `size` (string); `qualifies_for_coupon`, `has_clipped_coupon` (boolean); `coupon_id` (string); `cart_source` (app / pos) | PRD-55120, 16oz, true, false, pos |
| `checkout_completed` | Order paid | `order_id` (string); `channel` (in_store / pickup / delivery); `basket_value` (number); `coupons_eligible`, `coupons_applied` (number) | ORD-8812734, in_store, $86.40, 5, 3 |
| `coupon_applied` | A clipped coupon applies at checkout | `coupon_id`, `order_id` (string); `savings_amount` (number) | $1.50 |
| `coupon_failed` | A clipped coupon on a bought item does not apply | `coupon_id`, `order_id` (string); `failure_reason` (eligibility_mismatch / sync_lag / limit_reached / identity_mismatch); `lost_savings` (number) | sync_lag, $2.00 |
| `receipt_viewed` | Shopper opens the digital receipt | `order_id` (string) | ORD-8812734 |
| `service_desk_adjustment` | Store refunds a failed coupon | `coupon_id` (string); `recovered_amount` (number) | $1.40 |
| `auto_apply_enabled` | Treatment shopper's first app open in the test | none | none |

## User properties

| Property | Type | Values |
| --- | --- | --- |
| `segment` | enum | power_clipper, casual_app_user, non_app_loyalist, delivery_pickup_user |
| `boost_member` | boolean | true / false |
| `tenure_months` | number | 1 to 120 |
| `age_band` | enum | 18-24, 25-34, 35-44, 45-54, 55-64, 65+ |
| `banner` | enum | Kroger, Ralphs, Fred Meyer, King Soopers, Smith's |
| `experiment_variant` | enum | control, auto_apply, not_enrolled |
| `dataset` | constant | simulated_v1 |

## Known gaps

These limits forced some analysis outside Amplitude. A real implementation should add them.

- Add `coupon_value` to `item_added_to_cart`, so never-clipped savings can be measured directly instead of estimated.
- Add `channel` and `minutes_since_clip` to `coupon_failed`, so failures can be split by channel and clip timing without a join.
- Track app load, clip and scan errors as events. Real reviews say app reliability is the top coupon complaint, and this plan doesn't capture it.
