"""Generate SIMULATED Kroger coupon events in Amplitude HTTP V2 format.

Writes out/events.jsonl.gz (sorted by user, then time) and out/users.csv.
Sends nothing. Run:  python simulate.py
"""
import gzip, hashlib, json, math, os, sys
from datetime import timedelta
import numpy as np
import config as C

rng = np.random.default_rng(C.SEED)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def pick(d):
    keys = list(d)
    return keys[rng.choice(len(keys), p=np.array(list(d.values())) / sum(d.values()))]


def variant_for(user_id, segment):
    if segment not in C.APP_SEGMENTS:
        return "not_enrolled"
    h = int(hashlib.sha256(f"{C.SEED}:{user_id}".encode()).hexdigest(), 16)
    return "auto_apply" if h % 2 else "control"


# ---------- coupon catalog
catalog = []
for i in range(C.N_COUPONS):
    cat = rng.choice(list(C.CATEGORIES))
    val = float(np.clip(C.DISCOUNT_MEDIAN * math.exp(rng.normal(0, C.DISCOUNT_SIGMA)), C.DISCOUNT_MIN, C.DISCOUNT_MAX))
    catalog.append(dict(
        coupon_id=f"CPN-{10000 + i}", category=str(cat), brand=str(rng.choice(C.CATEGORIES[cat])),
        discount_value=round(val * 4) / 4,  # coupons come in quarter-dollar steps
        offer_type="personalized" if rng.random() < C.PERSONALIZED_SHARE else "generic",
        eligible_size=str(rng.choice(C.SIZES)), product_id=f"PRD-{50000 + i}",
    ))

# ---------- users
seg_names = list(C.SEGMENTS)
seg_counts = {s: round(C.N_USERS * C.SEGMENTS[s]["share"]) for s in seg_names}
users = []
uid = 0
for s in seg_names:
    for _ in range(seg_counts[s]):
        uid += 1
        user_id = f"sim_u_{uid:05d}"
        users.append(dict(
            user_id=user_id, segment=s,
            boost_member=bool(rng.random() < C.USER_PROPS["boost_member"][s]),
            tenure_months=int(np.clip(rng.gamma(2.2, 18), 1, 120)),
            age_band=pick(C.USER_PROPS["age_band"][s]),
            banner=pick(C.USER_PROPS["banner"]),
            experiment_variant=variant_for(user_id, s),
            dataset=C.DATASET_LABEL,
        ))

# ---------- events
events = []
order_seq = 0


def ms(dt):
    return int(dt.timestamp() * 1000)


def emit(u, etype, t, props=None):
    n = len(events)
    if n >= C.EVENT_CAP:
        sys.exit(f"ABORT: event cap {C.EVENT_CAP:,} reached. Nothing written.")
    events.append(dict(
        user_id=u["user_id"], event_type=etype, time=ms(t),
        insert_id=hashlib.md5(f"{C.DATASET_LABEL}:{u['user_id']}:{etype}:{ms(t)}:{n}".encode()).hexdigest(),
        event_properties=props or {},
    ))


def outcome(u, coupon, late, treated):
    """Return failure_reason or None (applied). Order: H1 -> H2 -> H3 -> H4."""
    s = u["segment"]
    if rng.random() < C.H1_ELIGIBILITY[s]:
        return "eligibility_mismatch"
    if late and not (treated and C.TREATMENT_REMOVES_H2) and rng.random() < C.H2_FAIL_IF_LATE:
        return "sync_lag"
    if rng.random() < C.H3_LIMIT[s]:
        return "limit_reached"
    if rng.random() < C.H4_IDENTITY[s]:
        return "identity_mismatch"
    return None


for u in users:
    seg = C.SEGMENTS[u["segment"]]
    is_app = u["segment"] in C.APP_SEGMENTS
    trust_until, trust_mult = -1, 1.0
    auto_enabled_emitted = False
    f = C.H5_FORGOT[u["segment"]]
    exp_purchase = (1 - C.PERSONALIZED_SHARE) * C.PURCHASE_PROB["generic"] + C.PERSONALIZED_SHARE * C.PURCHASE_PROB["personalized"]
    unclipped_rate = seg["clips"] * exp_purchase * f / (1 - f)

    for w in range(C.N_WEEKS):
        mult = trust_mult if w <= trust_until else 1.0
        n_trips = rng.poisson(seg["trips"] * mult)
        treated = is_app and u["experiment_variant"] == "auto_apply" and w >= C.EXPERIMENT_START_WEEK
        for _ in range(n_trips):
            day = int(rng.integers(0, 7))
            checkout = C.START + timedelta(weeks=w, days=day, hours=int(rng.integers(8, 21)), minutes=int(rng.integers(0, 60)))
            channel = pick(seg["channels"])
            order_seq += 1
            order_id = f"ORD-{8_000_000 + order_seq}"

            # --- clips before this trip
            n_clips = rng.poisson(seg["clips"])
            n_unclipped = rng.poisson(unclipped_rate)
            # draw distinct coupons for this trip: a coupon can only be clipped/used once per order
            picks = rng.choice(C.N_COUPONS, size=n_clips + n_unclipped, replace=False)
            clip_picks, unclipped_picks = picks[:n_clips], picks[n_clips:]
            mins_since_start = int((checkout - C.START).total_seconds() // 60) - 5
            clips = []
            for k in clip_picks:
                c = catalog[int(k)]
                late = rng.random() < C.H2_LATE_CLIP_SHARE[channel]
                mins = int(rng.integers(1, 15)) if late else int(np.clip(rng.lognormal(math.log(720), 1.0), 15, 6 * 24 * 60))
                mins = max(1, min(mins, mins_since_start))  # keep every event inside the 12-week window
                bought = rng.random() < C.PURCHASE_PROB[c["offer_type"]]
                clips.append((c, late, mins, bought))

            if is_app and (n_clips or rng.random() < 0.5):
                first = max(checkout - timedelta(minutes=max([m for _, _, m, _ in clips], default=30) + 2), C.START)
                emit(u, "app_opened", first)
                if treated and not auto_enabled_emitted:
                    exp_start = C.START + timedelta(weeks=C.EXPERIMENT_START_WEEK)
                    emit(u, "auto_apply_enabled", max(first + timedelta(seconds=1), exp_start))
                    auto_enabled_emitted = True
                emit(u, "offers_viewed", first + timedelta(minutes=1),
                     dict(offer_count=int(rng.integers(15, 120)), source=pick({"home": .4, "weekly_ad": .3, "search": .2, "push": .1})))

            for c, late, mins, bought in clips:
                emit(u, "coupon_clipped", checkout - timedelta(minutes=mins), dict(
                    coupon_id=c["coupon_id"], category=c["category"], brand=c["brand"],
                    discount_value=c["discount_value"], offer_type=c["offer_type"],
                    minutes_before_checkout=mins if bought else None, eligible_size=c["eligible_size"]))

            # --- items in the basket
            cart_source = "pos" if channel == "in_store" else "app"
            item_t = checkout - timedelta(minutes=5)
            outcomes = []  # (coupon, reason or None)
            for c, late, mins, bought in clips:
                if not bought:
                    continue
                reason = outcome(u, c, late, treated)
                size = c["eligible_size"] if reason != "eligibility_mismatch" else str(rng.choice([s for s in C.SIZES if s != c["eligible_size"]]))
                emit(u, "item_added_to_cart", item_t, dict(
                    product_id=c["product_id"], category=c["category"], size=size,
                    qualifies_for_coupon=reason != "eligibility_mismatch", has_clipped_coupon=True,
                    coupon_id=c["coupon_id"], cart_source=cart_source))
                outcomes.append((c, reason))

            # H5: qualifying items bought without a clip (auto-loaded for treatment users)
            for k in unclipped_picks:
                c = catalog[int(k)]
                auto = treated and rng.random() < C.TREATMENT_H5_REDUCTION
                reason = outcome(u, c, False, True) if auto else None
                size = c["eligible_size"] if reason != "eligibility_mismatch" else str(rng.choice([s for s in C.SIZES if s != c["eligible_size"]]))
                emit(u, "item_added_to_cart", item_t, dict(
                    product_id=c["product_id"], category=c["category"], size=size,
                    qualifies_for_coupon=reason != "eligibility_mismatch", has_clipped_coupon=auto,
                    coupon_id=c["coupon_id"] if auto else None, cart_source=cart_source))
                if auto:
                    outcomes.append((c, reason))

            # a couple of ordinary items so baskets aren't all coupon items
            for _ in range(rng.poisson(1.0)):
                emit(u, "item_added_to_cart", item_t, dict(
                    product_id=f"PRD-{int(rng.integers(60000, 69999))}", category=str(rng.choice(list(C.CATEGORIES))),
                    size=str(rng.choice(C.SIZES)), qualifies_for_coupon=False, has_clipped_coupon=False,
                    coupon_id=None, cart_source=cart_source))

            basket = round(float(C.BASKET_MEDIAN[channel] * math.exp(rng.normal(0, C.BASKET_SIGMA))), 2)
            applied = [o for o in outcomes if o[1] is None]
            emit(u, "checkout_completed", checkout, dict(
                order_id=order_id, channel=channel, basket_value=basket,
                coupons_eligible=len(outcomes), coupons_applied=len(applied)))

            failed_any, recovered_any = False, False
            for c, reason in outcomes:  # exactly one applied OR failed per clipped/loaded coupon
                if reason is None:
                    emit(u, "coupon_applied", checkout + timedelta(seconds=1),
                         dict(coupon_id=c["coupon_id"], savings_amount=c["discount_value"], order_id=order_id))
                else:
                    failed_any = True
                    emit(u, "coupon_failed", checkout + timedelta(seconds=1), dict(
                        coupon_id=c["coupon_id"], failure_reason=reason, lost_savings=c["discount_value"], order_id=order_id))
                    if channel == "in_store" and rng.random() < C.SERVICE_DESK_SHARE:
                        recovered_any = True
                        emit(u, "service_desk_adjustment", checkout + timedelta(minutes=int(rng.integers(5, 40))),
                             dict(coupon_id=c["coupon_id"], recovered_amount=round(c["discount_value"] * C.SERVICE_DESK_RECOVERY, 2)))

            if is_app and rng.random() < (0.50 if failed_any else 0.22):
                emit(u, "receipt_viewed", checkout + timedelta(minutes=int(rng.integers(2, 180))), dict(order_id=order_id))

            if failed_any:
                trust_until = w + C.TRUST_LOSS_WEEKS
                trust_mult = C.RECOVERED_TRUST_MULT if recovered_any else C.TRUST_LOSS_MULT

# ---------- write
os.makedirs(OUT, exist_ok=True)
events.sort(key=lambda e: (e["user_id"], e["time"]))
props = {u["user_id"]: {k: v for k, v in u.items() if k != "user_id"} for u in users}
seen = set()
with gzip.open(os.path.join(OUT, "events.jsonl.gz"), "wt") as fh:
    for e in events:
        e["event_properties"] = {k: v for k, v in e["event_properties"].items() if v is not None}
        if e["user_id"] not in seen:  # user properties ride on each user's first event
            e["user_properties"] = props[e["user_id"]]
            seen.add(e["user_id"])
        fh.write(json.dumps(e) + "\n")
with open(os.path.join(OUT, "users.csv"), "w") as fh:
    cols = list(users[0])
    fh.write(",".join(cols) + "\n")
    for u in users:
        fh.write(",".join(str(u[c]) for c in cols) + "\n")
print(f"SIMULATED: {len(users):,} users, {len(events):,} events -> {OUT}")
