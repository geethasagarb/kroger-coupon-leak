"""Simulation parameters for the Kroger Coupon Savings Leak case study.

ALL DATA PRODUCED FROM THESE SETTINGS IS SIMULATED. Nothing here is real Kroger data.
Every number below was agreed in Step 1 of the case study; change it here, not in the generator.
"""
from datetime import datetime, timezone

SEED = 42
DATASET_LABEL = "simulated_v1"

# 12 weeks: Mon Jul 20 2026 -> Sun Oct 11 2026 (falls inside Amplitude's "last 90 days")
START = datetime(2026, 7, 20, tzinfo=timezone.utc)
N_WEEKS = 12
EXPERIMENT_START_WEEK = 6          # 0-indexed -> weeks 7-12 are the test period

N_USERS = 8_000
EVENT_CAP = 1_500_000             # hard stop: never write/send more than this

APP_SEGMENTS = {"power_clipper", "casual_app_user", "delivery_pickup_user"}

SEGMENTS = {
    # share, trips/week, clips/trip, channel mix
    "power_clipper":        dict(share=0.20, trips=1.3, clips=5.0, channels={"in_store": .80, "pickup": .12, "delivery": .08}),
    "casual_app_user":      dict(share=0.35, trips=1.0, clips=2.0, channels={"in_store": .85, "pickup": .10, "delivery": .05}),
    # non-app loyalists occasionally clip on kroger.com / kiosk (no app events); this is how 15% of their savings get captured
    "non_app_loyalist":     dict(share=0.30, trips=0.9, clips=0.3, channels={"in_store": 1.0}),
    "delivery_pickup_user": dict(share=0.15, trips=0.8, clips=4.0, channels={"pickup": .55, "delivery": .45}),
}

# Probability a clipped coupon's item is actually bought on that trip
PURCHASE_PROB = {"generic": 0.66, "personalized": 0.86}     # personalized ~1.3x
PERSONALIZED_SHARE = 0.40

# ---- Seeded failure rates, evaluated in order H1 -> H2 -> H3 -> H4 per clipped coupon on a purchased item
H1_ELIGIBILITY = {"power_clipper": .03, "casual_app_user": .09, "non_app_loyalist": .06, "delivery_pickup_user": .06}
H2_LATE_CLIP_SHARE = {"in_store": .11, "pickup": .03, "delivery": .03}   # share of clips made <15 min before checkout
H2_FAIL_IF_LATE = 0.55
H3_LIMIT = {"power_clipper": .07, "casual_app_user": .03, "non_app_loyalist": .03, "delivery_pickup_user": .04}
H4_IDENTITY = {"power_clipper": .02, "casual_app_user": .02, "non_app_loyalist": .02, "delivery_pickup_user": .05}
# H5: share of qualifying purchased items bought WITHOUT a clipped coupon (missed savings)
H5_FORGOT = {"power_clipper": .10, "casual_app_user": .45, "non_app_loyalist": .85, "delivery_pickup_user": .30}

# ---- Trust loss and recovery
TRUST_LOSS_MULT = 0.88          # trip probability multiplier for 8 weeks after a coupon_failed
TRUST_LOSS_WEEKS = 8
SERVICE_DESK_SHARE = 0.15       # of in-store failures
SERVICE_DESK_RECOVERY = 0.70    # share of lost savings refunded
RECOVERED_TRUST_MULT = 0.94     # half the trust loss when the customer was made whole

# ---- Auto-apply experiment (app users only, weeks 7-12)
TREATMENT_H5_REDUCTION = 0.80   # 80% of would-be-missed coupons get auto-loaded
TREATMENT_REMOVES_H2 = True     # offers are preloaded to the loyalty ID, so no sync lag

# ---- Coupon catalog
N_COUPONS = 400
DISCOUNT_MEDIAN = 1.00
DISCOUNT_SIGMA = 0.55
DISCOUNT_MIN, DISCOUNT_MAX = 0.25, 5.00
CATEGORIES = {
    "dairy": ["Kroger", "Simple Truth", "Chobani", "Horizon"],
    "produce": ["Simple Truth", "Dole", "Driscoll's"],
    "snacks": ["Lay's", "Doritos", "Kroger", "Annie's"],
    "beverages": ["Coca-Cola", "Pepsi", "LaCroix", "Kroger"],
    "frozen": ["Private Selection", "DiGiorno", "Ben & Jerry's"],
    "pantry": ["Kroger", "Barilla", "Campbell's", "Simple Truth"],
    "household": ["Tide", "Bounty", "Kroger"],
    "personal_care": ["Dove", "Colgate", "Kroger"],
    "meat_seafood": ["Private Selection", "Tyson", "Simple Truth"],
    "bakery": ["Kroger", "Dave's Killer Bread", "Private Selection"],
}
SIZES = ["8oz", "12oz", "16oz", "24oz", "32oz", "64oz", "family_size"]

BASKET_MEDIAN = {"in_store": 58.0, "pickup": 92.0, "delivery": 104.0}
BASKET_SIGMA = 0.55

USER_PROPS = {
    "boost_member": {"power_clipper": .55, "casual_app_user": .25, "non_app_loyalist": .12, "delivery_pickup_user": .48},
    "age_band": {
        "power_clipper":        {"18-24": .06, "25-34": .24, "35-44": .30, "45-54": .22, "55-64": .12, "65+": .06},
        "casual_app_user":      {"18-24": .14, "25-34": .30, "35-44": .24, "45-54": .16, "55-64": .10, "65+": .06},
        "non_app_loyalist":     {"18-24": .03, "25-34": .07, "35-44": .12, "45-54": .20, "55-64": .26, "65+": .32},
        "delivery_pickup_user": {"18-24": .08, "25-34": .34, "35-44": .32, "45-54": .14, "55-64": .08, "65+": .04},
    },
    "banner": {"Kroger": .55, "Ralphs": .12, "Fred Meyer": .12, "King Soopers": .12, "Smith's": .09},
}
