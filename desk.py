"""Runs one paper cycle: EXIT open positions, SCAN, VERIFY, EXECUTE."""
import collections, config, scan, verify, execute, exit as exit_mod
import approve
from common import UNREACHABLE, load_state, desk_lock
assert config.PAPER_MODE is True
import fcntl, os, sys, time
_g = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cycle.lock"), "a+")
try: fcntl.flock(_g, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError: print("double-run guard: another desk.py cycle is running; exiting"); sys.exit(0)
_g.seek(0); _last = float((_g.read().strip() or "0"))
if time.time() - _last < getattr(config, "MIN_CYCLE_INTERVAL_SECONDS", 0):
    print(f"double-run guard: last cycle started {time.time()-_last:.0f}s ago; exiting"); sys.exit(0)
_g.seek(0); _g.truncate(); _g.write(str(time.time())); _g.flush()
_lock = desk_lock(); _lock.__enter__()  # held for the whole cycle; approve.py waits
print("expired proposals:", approve.expire_stale())
exit_mod.run()
cands = scan.scan(); passed = verify.run(cands); entries = execute.run(passed)
print(f"scanned={len(cands)} passed={len(passed)} skipped={len(cands)-len(passed)}")
for c in cands:
    if c.get("reasons"): print("SKIP", (c['pair'] or {}).get('baseToken', {}).get('symbol', '?'), c['mint'], "|", "; ".join(c['reasons']))
cnt = collections.Counter(r.split(' ')[0]+' '+r.split(' ')[1] if ' ' in r else r for c in cands for r in c.get("reasons", []))
print("top reasons:", cnt.most_common(5))
for e in entries: print("ENTRY", e["symbol"], e["mint"], e["entry"], e["entry_liq"], e["cost"])
print("approval active:", execute.approval_active(), "pending:", len(__import__("common").load_pending()))
print("balance:", load_state()["balance"], "unreachable:", sorted(UNREACHABLE) or "none")
import export; export.build(); print("data.json updated")
