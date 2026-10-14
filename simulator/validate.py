"""Validate the SIMULATED event file against the approved plan before anything is sent.
Prints a report and exits non-zero if any hard check fails.  Run:  python validate.py
"""
import gzip, json, os, sys
import pandas as pd
import config as C

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
rows = [json.loads(l) for l in gzip.open(os.path.join(OUT, "events.jsonl.gz"), "rt")]
users = pd.read_csv(os.path.join(OUT, "users.csv"))
ev = pd.json_normalize(rows, sep=".")
ev.columns = [c.replace("event_properties.", "") for c in ev.columns]
ev = ev.merge(users[["user_id", "segment", "experiment_variant"]], on="user_id")
ev["ts"] = pd.to_datetime(ev["time"], unit="ms", utc=True)
ev["week"] = ((ev["ts"] - pd.Timestamp(C.START)).dt.days // 7) + 1

fails = []
def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        fails.append(name)

print("\n== SIMULATED DATA VALIDATION ==")
print(f"events: {len(ev):,}   users with events: {ev.user_id.nunique():,} / {len(users):,}")
print(ev.event_type.value_counts().to_string(), "\n")

print("Structural checks")
plan = {"app_opened", "offers_viewed", "coupon_clipped", "item_added_to_cart", "checkout_completed", "coupon_applied",
        "coupon_failed", "receipt_viewed", "service_desk_adjustment", "auto_apply_enabled"}
check("only planned event names", set(ev.event_type) <= plan, f"{sorted(set(ev.event_type) - plan)}")
check("volume under cap", len(ev) <= C.EVENT_CAP, f"{len(ev):,} <= {C.EVENT_CAP:,}")
end = pd.Timestamp(C.START) + pd.Timedelta(weeks=C.N_WEEKS)
check("all events inside the 12-week window",
      ev.ts.min() >= pd.Timestamp(C.START) and ev.ts.max() < end + pd.Timedelta(days=1),
      f"{ev.ts.min():%Y-%m-%d} -> {ev.ts.max():%Y-%m-%d}")
check("insert_id unique", ev.insert_id.is_unique)
check("every user's first event carries user_properties", ev.groupby("user_id").head(1)["user_properties.segment"].notna().all())

ck = ev[ev.event_type == "checkout_completed"]
outc = ev[ev.event_type.isin(["coupon_applied", "coupon_failed"])]
per_order = outc.groupby("order_id").size()
check("one outcome per coupon: outcomes == coupons_eligible per order",
      (ck.set_index("order_id").coupons_eligible.reindex(per_order.index) == per_order).all()
      and ck.coupons_eligible.sum() == len(outc), f"{ck.coupons_eligible.sum():,} eligible vs {len(outc):,} outcomes")
dup = outc.groupby(["order_id", "coupon_id"]).event_type.nunique()
check("no coupon both applied and failed on one order", (dup <= 1).all())
cf = ev[ev.event_type == "coupon_failed"]
check("failure_reason values in enum", set(cf.failure_reason) <= {"eligibility_mismatch", "sync_lag", "limit_reached", "identity_mismatch"})
check("non-app users have no app_opened", ev[(ev.segment == "non_app_loyalist") & (ev.event_type == "app_opened")].empty)
check("auto_apply_enabled only for treatment, weeks 7+",
      set(ev[ev.event_type == "auto_apply_enabled"].experiment_variant) == {"auto_apply"}
      and ev[ev.event_type == "auto_apply_enabled"].week.min() >= C.EXPERIMENT_START_WEEK + 1)

print("\nSegment shares (target vs actual)")
share = users.segment.value_counts(normalize=True)
for s, cfg in C.SEGMENTS.items():
    check(f"{s:22s}", abs(share[s] - cfg["share"]) < 0.005, f"target {cfg['share']:.0%}  actual {share[s]:.1%}")

print("\nSeeded rates, pre-period weeks 1-6 (target vs actual, tolerance ±1pp)")
pre = outc[outc.week <= C.EXPERIMENT_START_WEEK]
pre_f = pre[pre.event_type == "coupon_failed"]
cp = ev[(ev.event_type == "coupon_clipped")]
late_ids = set()
def rate(seg, reason):
    d = pre[pre.segment == seg]
    return (d.failure_reason == reason).mean() if len(d) else float("nan")
# H1, H3, H4 effective rates are conditional on earlier hypotheses not firing; compute expected that way
for seg in C.SEGMENTS:
    d = pre[pre.segment == seg]
    if len(d) < 200:
        continue
    h1 = C.H1_ELIGIBILITY[seg]
    check(f"H1 eligibility  {seg:22s}", abs(rate(seg, "eligibility_mismatch") - h1) < 0.01, f"target {h1:.1%} actual {rate(seg, 'eligibility_mismatch'):.1%}")
for seg in ["power_clipper", "casual_app_user", "delivery_pickup_user"]:
    print(f"    H2 sync_lag   {seg:22s} actual {rate(seg, 'sync_lag'):.1%}")
    print(f"    H3 limit      {seg:22s} actual {rate(seg, 'limit_reached'):.1%}  (seeded {C.H3_LIMIT[seg]:.0%} after H1/H2)")
    print(f"    H4 identity   {seg:22s} actual {rate(seg, 'identity_mismatch'):.1%}  (seeded {C.H4_IDENTITY[seg]:.0%} after H1-H3)")

# H2 conditional check: failure rate among late clips that were bought
bought = cp[cp.minutes_before_checkout.notna() & (cp.week <= C.EXPERIMENT_START_WEEK)]
late_share = (bought.minutes_before_checkout < 15).mean()
print(f"    share of bought clips made <15 min before checkout: {late_share:.1%}")

print("\nH5 missed-savings share (qualifying items bought without a coupon, pre-period)")
it = ev[(ev.event_type == "item_added_to_cart") & (ev.week <= C.EXPERIMENT_START_WEEK)]
q = it[(it.qualifies_for_coupon == True) | (it.has_clipped_coupon == True)]
for seg in C.SEGMENTS:
    d = q[q.segment == seg]
    miss = (d.has_clipped_coupon == False).mean()
    check(f"H5 forgot {seg:22s}", abs(miss - C.H5_FORGOT[seg]) < 0.02, f"target {C.H5_FORGOT[seg]:.0%} actual {miss:.1%}")

print("\nNorth Star: Realization Rate = applied $ / (applied $ + lost $)")
def rr(d):
    a = d.savings_amount.sum(); l = d.lost_savings.sum()
    return a / (a + l)
print(f"    overall, pre-period: {rr(pre):.1%}")
for seg in C.SEGMENTS:
    print(f"    {seg:22s} {rr(pre[pre.segment == seg]):.1%}")

print("\nExperiment sanity (weeks 7-12, app users)")
post = outc[(outc.week > C.EXPERIMENT_START_WEEK) & outc.experiment_variant.isin(["control", "auto_apply"])]
for v in ["control", "auto_apply"]:
    print(f"    {v:10s} realization {rr(post[post.experiment_variant == v]):.1%}   users {users[users.experiment_variant == v].shape[0]:,}")
pre_ab = pre[pre.experiment_variant.isin(["control", "auto_apply"])]
a, b = rr(pre_ab[pre_ab.experiment_variant == "control"]), rr(pre_ab[pre_ab.experiment_variant == "auto_apply"])
check("A/A in pre-period: arms within 1pp", abs(a - b) < 0.01, f"control {a:.1%} vs auto_apply {b:.1%}")

print("\nTrust loss (matched): users whose FIRST coupon_failed is in week w vs users who used coupons cleanly in week w")
print("  trips/week over the next 6 weeks, same segment, weeks 2-4 pooled")
uids = {s: set(users[users.segment == s].user_id) for s in C.SEGMENTS}
for seg in ["power_clipper", "casual_app_user", "delivery_pickup_user"]:
    acc = {"failed": [], "clean": []}
    for w in [2, 3, 4]:
        wk = outc[outc.week == w]
        prior = set(outc[(outc.week < w) & (outc.event_type == "coupon_failed")].user_id)
        exposed = (set(wk.user_id) - prior) & uids[seg]
        failed = set(wk[wk.event_type == "coupon_failed"].user_id)
        for g, ids in [("failed", exposed & failed), ("clean", exposed - failed)]:
            n = ck[ck.user_id.isin(ids) & (ck.week > w) & (ck.week <= w + 6)].groupby("user_id").size().reindex(list(ids), fill_value=0)
            acc[g].extend((n / 6).tolist())
    f, c = sum(acc["failed"]) / len(acc["failed"]), sum(acc["clean"]) / len(acc["clean"])
    check(f"trust loss {seg:22s}", f < c, f"failed {f:.2f} vs clean {c:.2f} ({f/c-1:+.1%}; seeded -12%, diluted because clean users fail later too)")

print(f"\nRESULT: {'ALL HARD CHECKS PASSED' if not fails else 'FAILED: ' + ', '.join(fails)}  (data is SIMULATED)")
sys.exit(1 if fails else 0)
