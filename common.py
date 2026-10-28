import csv, json, os, datetime, zoneinfo, urllib.request
BASE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(BASE, "logs"); os.makedirs(LOGS, exist_ok=True)
STATE = os.path.join(BASE, "state.json")
TZ = zoneinfo.ZoneInfo("America/New_York")
UNREACHABLE = set()

def now(): return datetime.datetime.now(TZ).isoformat(timespec="seconds")

def get_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "paper-desk/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r: return json.load(r)
    except Exception as e:
        UNREACHABLE.add(f"{url.split('/')[2]} ({type(e).__name__})"); return None

APPROVAL_FIELDS = ["approval_latency_s", "signal_price", "drift_pct"]
TRADE_FIELDS = ["ts", "side", "symbol", "mint", "price", "qty", "usd", "cost_basis_usd", "pnl_usd", "pnl_pct", "reason", "balance_after"] + APPROVAL_FIELDS
TASK_FIELDS = ["ts", "role", "token", "mint", "decision", "reasons"] + APPROVAL_FIELDS
PENDING = os.path.join(BASE, "pending.json")

import contextlib, fcntl
@contextlib.contextmanager
def desk_lock():
    """Serializes desk.py cycles and approve.py so state/pending are never written concurrently."""
    with open(os.path.join(BASE, ".desk.lock"), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX); yield

def load_pending(): return json.load(open(PENDING)) if os.path.exists(PENDING) else []
def save_pending(p):
    tmp = PENDING + ".tmp"; json.dump(p, open(tmp, "w"), indent=2); os.replace(tmp, PENDING)

def _migrate(p, fields):
    """If an existing CSV has an older header, rewrite it with the new columns (blank for old rows)."""
    with open(p, newline="") as f: r = csv.DictReader(f); old = r.fieldnames or []; rows = list(r)
    if old == fields: return
    tmp = p + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields + [c for c in old if c not in fields]); w.writeheader(); w.writerows(rows)
    os.replace(tmp, p)

def _append(name, fields, row):
    p = os.path.join(LOGS, name); new = not os.path.exists(p)
    if not new: _migrate(p, fields)
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new: w.writeheader()
        w.writerow(row)

def log_task(role, token, mint, decision, reasons, **extra):
    _append("tasks.csv", TASK_FIELDS,
            dict(ts=now(), role=role, token=token, mint=mint, decision=decision, reasons="; ".join(reasons), **extra))

def log_trade(**row):
    _append("trades.csv", TRADE_FIELDS, dict(ts=now(), **row))

def load_state():
    import config
    if not os.path.exists(STATE): return {"balance": config.STARTING_PAPER_BALANCE, "positions": []}
    return json.load(open(STATE))

def save_state(s):
    tmp = STATE + ".tmp"; json.dump(s, open(tmp, "w"), indent=2); os.replace(tmp, STATE)
