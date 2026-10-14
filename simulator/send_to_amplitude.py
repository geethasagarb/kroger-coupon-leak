"""Send the SIMULATED events to Amplitude via the Batch Event Upload API.

Safety:
  * Dry run by default. Nothing is sent unless you pass --send.
  * The API key is read ONLY from the AMPLITUDE_API_KEY environment variable. Never paste it anywhere else.
  * Refuses to send more than config.EVENT_CAP events.
  * Every event has a stable insert_id, so retries and resumed runs cannot double-count.
  * Progress is checkpointed in out/sent_offset.txt, so an interrupted run resumes where it stopped.

Usage:
  python send_to_amplitude.py                  # dry run: counts and a sample payload
  python send_to_amplitude.py --send --users 1 # smoke test: one user's events
  python send_to_amplitude.py --send           # full upload (resumes from checkpoint)
"""
import argparse, gzip, json, os, sys, time, urllib.error, urllib.request
import config as C

URL = "https://api2.amplitude.com/batch"
BATCH = 1000
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out", "events.jsonl.gz")
CKPT = os.path.join(HERE, "out", "sent_offset.txt")

ap = argparse.ArgumentParser()
ap.add_argument("--send", action="store_true", help="actually send (default is dry run)")
ap.add_argument("--users", type=int, default=0, help="only send the first N users (smoke test)")
args = ap.parse_args()

events = [json.loads(l) for l in gzip.open(SRC, "rt")]
if args.users:
    keep = sorted({e["user_id"] for e in events})[: args.users]
    events = [e for e in events if e["user_id"] in set(keep)]
if len(events) > C.EVENT_CAP:
    sys.exit(f"ABORT: {len(events):,} events exceeds cap {C.EVENT_CAP:,}")
for e in events:
    e.setdefault("platform", "simulated")  # visible in Amplitude as a second "simulated" marker

print(f"SIMULATED dataset {C.DATASET_LABEL}: {len(events):,} events, {len({e['user_id'] for e in events}):,} users")
if not args.send:
    print("Dry run. Sample payload event:\n" + json.dumps(events[0], indent=2))
    print("Add --send to upload. Key is read from AMPLITUDE_API_KEY.")
    sys.exit(0)

key = os.environ.get("AMPLITUDE_API_KEY")
if not key:
    sys.exit("Set AMPLITUDE_API_KEY in your environment first (Amplitude > Settings > Projects > default > General).")

start = 0
if not args.users and os.path.exists(CKPT):
    start = int(open(CKPT).read().strip() or 0)
    print(f"Resuming from event {start:,}")

def post(batch):
    body = json.dumps({"api_key": key, "events": batch}).encode()
    for attempt in range(8):
        req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json", "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503, 504):
                wait = min(60, 2 ** attempt)
                print(f"  HTTP {e.code}, retrying in {wait}s")
                time.sleep(wait)
                continue
            sys.exit(f"HTTP {e.code}: {msg}")  # 400s mean a payload problem: stop, don't burn quota
        except urllib.error.URLError as e:
            time.sleep(min(60, 2 ** attempt))
    sys.exit("Gave up after 8 retries; rerun to resume from the checkpoint.")

sent = start
t0 = time.time()
for i in range(start, len(events), BATCH):
    post(events[i : i + BATCH])
    sent = min(i + BATCH, len(events))
    if not args.users:
        open(CKPT, "w").write(str(sent))
    if (sent // BATCH) % 50 == 0 or sent == len(events):
        print(f"  {sent:,}/{len(events):,} sent  ({time.time() - t0:.0f}s)")
    time.sleep(0.1)
print(f"Done. {sent - start:,} events sent this run.")
