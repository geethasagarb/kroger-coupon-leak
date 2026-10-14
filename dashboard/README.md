# Dashboard

`index.html` is a self-contained interactive page (D3.js, vendored in `vendor/`). It reads the CSVs that `analysis/build_results.py` writes to `../data/results/`, plus `../data/playstore_review_causes.csv`, so it always shows the latest results.

Browsers block CSV loading from `file://`, so serve the repo root:

```bash
python -m http.server 8000
# open http://localhost:8000/dashboard/
```

Sections, in reading order:

1. What real shoppers say (Google Play reviews, real)
2. North Star: Coupon Savings Realization Rate
3. Where qualifying savings go
4. Why clipped coupons fail
5. What a failure costs in later trips
6. Who to target first
7. Auto-apply experiment
8. Recommendations

All event-based charts are labeled **simulated**. `what_kroger_could_do_better.html` is the source of the recommendations graphic in the main README.
