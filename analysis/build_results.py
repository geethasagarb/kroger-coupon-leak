"""Recompute every number in the case study from the SIMULATED event file.

Reads  simulator/out/events.jsonl.gz and simulator/out/users.csv (run simulator/simulate.py first).
Writes data/results/*.csv (the dashboard's source files) and data/results/headline_numbers.json.

Windows (UTC):  baseline = weeks 1-6 = Jul 20 - Aug 30, 2026;  experiment = weeks 7-12 = Aug 31 - Oct 11, 2026.
Run:  python analysis/build_results.py
"""
import gzip, json, os, sys
import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "simulator"))
import config as C  # noqa: E402

OUT = os.path.join(ROOT, "data", "results")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- load
rows = [json.loads(l) for l in gzip.open(os.path.join(ROOT, "simulator", "out", "events.jsonl.gz"), "rt")]
ev = pd.json_normalize(rows)
ev.columns = [c.replace("event_properties.", "") for c in ev.columns]
users = pd.read_csv(os.path.join(ROOT, "simulator", "out", "users.csv"))
ev = ev.merge(users[["user_id", "segment", "experiment_variant", "age_band", "boost_member"]], on="user_id")
ev["ts"] = pd.to_datetime(ev.time, unit="ms", utc=True)
ev["week"] = ((ev.ts - pd.Timestamp(C.START)).dt.days // 7) + 1

checkouts = ev[ev.event_type == "checkout_completed"][["order_id", "channel", "user_id", "time", "basket_value", "week", "experiment_variant", "segment"]]
order_channel = checkouts[["order_id", "channel"]].rename(columns={"channel": "ch"})
discount = ev[ev.event_type == "coupon_clipped"].groupby("coupon_id").discount_value.first()
product_to_coupon = {f"PRD-{50000 + i}": f"CPN-{10000 + i}" for i in range(C.N_COUPONS)}

outcomes = (ev[ev.event_type.isin(["coupon_applied", "coupon_failed"])]
            .drop(columns=["channel"]).merge(order_channel, on="order_id"))
outcomes["applied"] = outcomes.savings_amount.fillna(0)
outcomes["lost"] = outcomes.lost_savings.fillna(0)

# never-clipped qualifying items, valued at the coupon's face value (cart events carry no coupon value)
missed = ev[(ev.event_type == "item_added_to_cart") & (ev.qualifies_for_coupon == True) & (ev.has_clipped_coupon == False)].copy()  # noqa: E712
missed["missed"] = missed.product_id.map(product_to_coupon).map(discount)
missed = missed.drop(columns=["channel"]).assign(ctime=missed.time + 300_000).merge(
    checkouts[["user_id", "time", "channel"]].rename(columns={"time": "ctime", "channel": "ch"}), on=["user_id", "ctime"], how="left")
assert missed.ch.notna().all(), "every never-clipped item must belong to a checkout"

base = lambda d: d[d.week <= 6]
H = {}  # headline numbers

# ---------------------------------------------------------------- 1. headline + dollar flow (weeks 1-6)
a = base(outcomes).groupby("segment")[["applied", "lost"]].sum()
m = base(missed).groupby("segment").missed.sum()
flow = a.join(m).rename(columns={"lost": "failed", "missed": "never_clipped"})
flow["total_qualifying"] = flow.sum(axis=1)
flow["capture_rate"] = flow.applied / flow.total_qualifying
flow["realization_rate"] = flow.applied / (flow.applied + flow.failed)
tot = flow[["applied", "failed", "never_clipped", "total_qualifying"]].sum()
flow.loc["ALL"] = list(tot) + [tot.applied / tot.total_qualifying, tot.applied / (tot.applied + tot.failed)]
flow.round(4).reset_index().to_csv(os.path.join(OUT, "dollar_flow_by_segment.csv"), index=False)
sd = base(ev)[base(ev).event_type == "service_desk_adjustment"].recovered_amount.sum()
H.update(qualifying=tot.total_qualifying, applied=tot.applied, failed=tot.failed, never_clipped=tot.never_clipped,
         realization=tot.applied / (tot.applied + tot.failed), capture=tot.applied / tot.total_qualifying,
         share_applied=tot.applied / tot.total_qualifying, share_failed=tot.failed / tot.total_qualifying,
         share_never_clipped=tot.never_clipped / tot.total_qualifying, never_clipped_vs_failed=tot.never_clipped / tot.failed,
         service_desk_recovered=sd, service_desk_share=sd / tot.failed, events=len(ev), users=len(users))
pd.DataFrame([dict(window="Jul 20 - Aug 30, 2026 (weeks 1-6)", qualifying=H["qualifying"], applied=H["applied"], failed=H["failed"],
                   never_clipped=H["never_clipped"], realization=H["realization"], capture=H["capture"],
                   service_desk_recovered=H["service_desk_recovered"], service_desk_share=H["service_desk_share"],
                   users=H["users"], events=H["events"])]).to_csv(os.path.join(OUT, "kpis.csv"), index=False)

# user-level funnel check (app users, weeks 1-6): users who viewed offers vs users with any coupon_applied
app_pre = base(ev)[base(ev).segment != "non_app_loyalist"]
viewers = set(app_pre[app_pre.event_type == "offers_viewed"].user_id)
H["funnel_users_viewed_to_applied"] = len(viewers & set(app_pre[app_pre.event_type == "coupon_applied"].user_id)) / len(viewers)

# ---------------------------------------------------------------- 2. North Star weekly by arm
ns = []
for w, d in outcomes.groupby("week"):
    r = {"week": int(w), "week_start": (pd.Timestamp(C.START) + pd.Timedelta(weeks=int(w) - 1)).strftime("%b %d"),
         "overall": d.applied.sum() / (d.applied.sum() + d.lost.sum())}
    for v in ["control", "auto_apply"]:
        x = d[d.experiment_variant == v]
        r[v] = x.applied.sum() / (x.applied.sum() + x.lost.sum())
    ns.append(r)
pd.DataFrame(ns).round(4).to_csv(os.path.join(OUT, "north_star_weekly.csv"), index=False)

# ---------------------------------------------------------------- 3. failures by reason x channel, clip timing
f = base(outcomes)[base(outcomes).event_type == "coupon_failed"]
fr = f.pivot_table(index="failure_reason", columns="ch", values="lost", aggfunc="sum", fill_value=0)
fr["total"] = fr.sum(axis=1); fr["coupons"] = f.groupby("failure_reason").size(); fr["share"] = fr.total / fr.total.sum()
fr.sort_values("total", ascending=False).round(4).reset_index().to_csv(os.path.join(OUT, "failures_by_reason_channel.csv"), index=False)
H["failure_share"] = fr.share.round(4).to_dict()
H["failed_in_store_share"] = fr.in_store.sum() / fr.total.sum()

clip = base(ev)[(base(ev).event_type == "coupon_clipped") & base(ev).minutes_before_checkout.notna()][["user_id", "coupon_id", "time", "minutes_before_checkout"]]
o = base(outcomes)[["user_id", "coupon_id", "time", "event_type"]].rename(columns={"time": "otime"})
mm = clip.merge(o, on=["user_id", "coupon_id"])
mm = mm[(mm.otime > mm.time) & ((mm.otime - mm.time) <= (mm.minutes_before_checkout * 60000 + 5000))]
mm["bucket"] = pd.cut(mm.minutes_before_checkout, [0, 15, 60, 1440, 1e9], labels=["Under 15 min", "15-60 min", "1-24 hours", "Over 24 hours"], right=False)
ct = mm.groupby("bucket", observed=True).agg(coupons=("coupon_id", "size"), failure_rate=("event_type", lambda s: (s == "coupon_failed").mean()))
ct.round(4).reset_index().to_csv(os.path.join(OUT, "clip_timing_failure.csv"), index=False)
H["fail_rate_under_15min"] = ct.loc["Under 15 min", "failure_rate"]

# ---------------------------------------------------------------- 4. capture by cut, segment x channel
cuts = []
for dim, label in [("ch", "Channel"), ("age_band", "Age band"), ("boost_member", "Boost member")]:
    a = base(outcomes).groupby(dim)[["applied", "lost"]].sum(); m = base(missed).groupby(dim).missed.sum()
    for k in a.index:
        ap, lo, mi = a.loc[k, "applied"], a.loc[k, "lost"], m.get(k, 0)
        cuts.append(dict(dimension=label, value=str(k).replace("in_store", "In-store").replace("pickup", "Pickup").replace("delivery", "Delivery"),
                         realization_rate=ap / (ap + lo), capture_rate=ap / (ap + lo + mi), applied=ap, failed=lo, never_clipped=mi))
pd.DataFrame(cuts).round(4).to_csv(os.path.join(OUT, "capture_by_cut.csv"), index=False)
sc = base(outcomes).groupby(["segment", "ch"])[["applied", "lost"]].sum().join(base(missed).groupby(["segment", "ch"]).missed.sum()).fillna(0)
sc["capture_rate"] = sc.applied / (sc.applied + sc.lost + sc.missed); sc["leak"] = sc.lost + sc.missed; sc["leak_share"] = sc.leak / sc.leak.sum()
sc.round(4).reset_index().to_csv(os.path.join(OUT, "segment_channel_capture.csv"), index=False)
H["top2_leak_share"] = sc.loc[("casual_app_user", "in_store"), "leak_share"] + sc.loc[("non_app_loyalist", "in_store"), "leak_share"]

# ---------------------------------------------------------------- 5. trust loss: matched comparison, 8-week follow-up
FU = 8; res = []
ck = checkouts
for seg in ["casual_app_user", "delivery_pickup_user", "non_app_loyalist", "power_clipper"]:
    su = set(users[users.segment == seg].user_id)
    for w in [1, 2, 3, 4]:
        wk = outcomes[outcomes.week == w]
        prior = set(outcomes[(outcomes.week < w) & (outcomes.event_type == "coupon_failed")].user_id)
        exposed = (set(wk.user_id) - prior) & su
        failed = set(wk[wk.event_type == "coupon_failed"].user_id)
        for g, ids in [("failed", sorted(exposed & failed)), ("clean", sorted(exposed - failed))]:  # sorted: deterministic bootstrap
            c = ck[ck.user_id.isin(ids) & (ck.week > w) & (ck.week <= w + FU)]
            n = c.groupby("user_id").size().reindex(list(ids), fill_value=0)
            b = c.groupby("user_id").basket_value.sum().reindex(list(ids), fill_value=0)
            for uid in ids:
                res.append((seg, g, n[uid] / FU, b[uid] / FU))
r = pd.DataFrame(res, columns=["segment", "group", "trips_wk", "spend_wk"])
rng = np.random.default_rng(1)
names = {"casual_app_user": "Casual app user", "delivery_pickup_user": "Delivery/pickup", "non_app_loyalist": "Non-app loyalist", "power_clipper": "Power clipper"}
tl = []
for seg, d in r.groupby("segment"):
    fv = d[d.group == "failed"].trips_wk.values; cv = d[d.group == "clean"].trips_wk.values
    bs = [rng.choice(fv, len(fv)).mean() / rng.choice(cv, len(cv)).mean() - 1 for _ in range(1000)]
    fs = d[d.group == "failed"].spend_wk.mean(); cs = d[d.group == "clean"].spend_wk.mean()
    tl.append(dict(segment=names[seg], failing_shoppers=len(fv), clean_shoppers=len(cv), trips_per_week_failed=fv.mean(), trips_per_week_clean=cv.mean(),
                   trip_change=fv.mean() / cv.mean() - 1, ci_low=np.percentile(bs, 2.5), ci_high=np.percentile(bs, 97.5), spend_gap_8wk_per_shopper=(fs - cs) * FU))
tl = pd.DataFrame(tl).sort_values("trip_change")
tl.round(4).to_csv(os.path.join(OUT, "trust_loss_matched.csv"), index=False)
n = tl.failing_shoppers.sum()
H["trust_weighted_trip_change"] = (tl.trip_change * tl.failing_shoppers).sum() / n
H["trust_failing_shoppers"] = int(n)
H["trust_lost_sales"] = -(tl.spend_gap_8wk_per_shopper * tl.failing_shoppers).sum()
H["trust_lost_sales_per_shopper"] = H["trust_lost_sales"] / n
H["trust_multiple_of_failed"] = H["trust_lost_sales"] / H["failed"]

# ---------------------------------------------------------------- 6. experiment (app users, weeks 7-12)
app = ev[ev.experiment_variant.isin(["control", "auto_apply"])]
def per_user(d):
    a = d[d.event_type == "coupon_applied"].groupby("user_id").savings_amount.sum()
    f = d[d.event_type == "coupon_failed"].groupby("user_id").lost_savings.sum()
    it = d[(d.event_type == "item_added_to_cart") & (d.qualifies_for_coupon == True) & (d.has_clipped_coupon == False)]  # noqa: E712
    m = it.product_id.map(product_to_coupon).map(discount).groupby(it.user_id).sum()
    c = d[d.event_type == "checkout_completed"]
    U = users[users.experiment_variant.isin(["control", "auto_apply"])].set_index("user_id")[["experiment_variant", "segment"]]
    return U.join(pd.DataFrame({"applied": a, "failed": f, "missed": m, "orders": c.groupby("user_id").size(),
                                "basket": c.groupby("user_id").basket_value.sum(),
                                "sd": d[d.event_type == "service_desk_adjustment"].groupby("user_id").size()})).fillna(0)
pre, post = per_user(app[app.week <= 6]), per_user(app[app.week >= 7])
rng = np.random.default_rng(7)
def boot_diff(t, fn, B):
    c = t[t.experiment_variant == "control"]; x = t[t.experiment_variant == "auto_apply"]
    out = []
    for _ in range(B):
        cs = c.iloc[rng.integers(0, len(c), len(c))]
        xs = x.iloc[rng.integers(0, len(x), len(x))]
        out.append(fn(xs) - fn(cs))
    return np.percentile(out, [2.5, 97.5]), np.std(out)
real = lambda t: t.applied.sum() / (t.applied.sum() + t.failed.sum())
cap = lambda t: t.applied.sum() / (t.applied.sum() + t.failed.sum() + t.missed.sum())
metrics = [("Realization rate", "Realization rate (primary)", "primary", real, "Win"),
           ("Capture rate", "Capture rate", "secondary", cap, "Win"),
           ("Savings per order", "Savings applied per order ($)", "secondary", lambda t: t.applied.sum() / t.orders.sum(), "Expected cost"),
           ("Net basket after savings", "Net basket after savings ($)", "guardrail", lambda t: (t.basket.sum() - t.applied.sum()) / t.orders.sum(), "Flag: false alarm (no basket effect in simulator)"),
           ("Service desk adjustments", "Service desk adjustments per 1,000 orders", "guardrail", lambda t: t.sd.sum() / t.orders.sum() * 1000, "No significant change"),
           ("Trips per shopper", "Trips per shopper per week", "guardrail", lambda t: t.orders.sum() / len(t) / 6, "No significant change")]
_, se_pre = boot_diff(pre, real, 800)
aa_ci, _ = boot_diff(pre, real, 800)
er = []
for label, metric, role, fn, verdict in metrics:
    c = fn(post[post.experiment_variant == "control"]); x = fn(post[post.experiment_variant == "auto_apply"])
    ci, _ = boot_diff(post, fn, 1500)
    er.append(dict(label=label, metric=metric, role=role, control=c, auto_apply=x, diff=x - c, ci_low=ci[0], ci_high=ci[1],
                   rel_lift=(x - c) / c, rel_ci_low=ci[0] / c, rel_ci_high=ci[1] / c, verdict=verdict))
er = pd.DataFrame(er); er.round(4).to_csv(os.path.join(OUT, "experiment_results.csv"), index=False)
nv = post.experiment_variant.value_counts()
pd.DataFrame([dict(users_control=int(nv["control"]), users_auto=int(nv["auto_apply"]), srm_p=stats.chisquare([nv["control"], nv["auto_apply"]]).pvalue,
                   aa_diff_ci_low=aa_ci[0], aa_diff_ci_high=aa_ci[1], mde_pp=2.8 * se_pre, weeks=6, start="Aug 31, 2026", end="Oct 11, 2026")]
             ).round(4).to_csv(os.path.join(OUT, "experiment_design.csv"), index=False)
seg_names = {"casual_app_user": "Casual app user", "delivery_pickup_user": "Delivery/pickup", "power_clipper": "Power clipper"}
pd.DataFrame([dict(segment=seg_names[s], realization_control=real(g[g.experiment_variant == "control"]), realization_auto=real(g[g.experiment_variant == "auto_apply"]),
                   capture_control=cap(g[g.experiment_variant == "control"]), capture_auto=cap(g[g.experiment_variant == "auto_apply"]))
              for s, g in post.groupby("segment")]).round(4).to_csv(os.path.join(OUT, "experiment_by_segment.csv"), index=False)
H["experiment"] = er.set_index("label")[["control", "auto_apply", "diff", "ci_low", "ci_high", "rel_lift", "rel_ci_low", "rel_ci_high"]].round(4).to_dict("index")
H["experiment_users"] = {k: int(v) for k, v in nv.items()}
H["experiment_mde_pp"] = 2.8 * se_pre

# ---------------------------------------------------------------- write
json.dump({k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in H.items()},
          open(os.path.join(OUT, "headline_numbers.json"), "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in H.items() if k != "experiment"}, indent=1, default=float))
print("experiment:", json.dumps(H["experiment"], indent=1))
