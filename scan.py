"""SCAN: gathers fresh Solana pairs. Never judges."""
import config
from common import get_json, log_task

def whale_watch():  # stub, disabled by default
    return [] if not config.WHALE_WATCH_ENABLED else []

def scan():
    profiles = get_json("https://api.dexscreener.com/token-profiles/latest/v1") or []
    mints = list(dict.fromkeys(p["tokenAddress"] for p in profiles if p.get("chainId") == "solana"))[:config.MAX_CANDIDATES]
    src = {m: "DexScreener profiles" for m in mints}
    mints += [m for m in whale_watch() if m not in mints]
    out = []
    for i in range(0, len(mints), 30):
        data = get_json("https://api.dexscreener.com/tokens/v1/solana/" + ",".join(mints[i:i+30])) or []
        best = {}
        for p in data:  # keep deepest-liquidity pair per mint
            m = p["baseToken"]["address"]
            if m in mints and (p.get("liquidity") or {}).get("usd", 0) >= (best.get(m, {}).get("liquidity") or {}).get("usd", -1):
                best[m] = p
        for m in mints[i:i+30]:
            out.append({"mint": m, "pair": best.get(m)})
    for c in out:
        bt = (c["pair"] or {}).get("baseToken") or {}
        sym = bt.get("symbol") if bt.get("address") == c["mint"] and bt.get("symbol") else c["mint"][:6]
        log_task("SCAN", sym, c["mint"], "CANDIDATE", ["found via " + src.get(c["mint"], "whale watch")])
    return out
