"""Runs one paper cycle: EXIT open positions, SCAN, VERIFY, EXECUTE."""
import collections, config, scan, verify, execute, exit as exit_mod
import approve
from common import UNREACHABLE, load_state, desk_lock
assert config.PAPER_MODE is True
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
