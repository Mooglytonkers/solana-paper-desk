"""APPROVE (paper): act on PROPOSED entries in pending.json. No wallet, no keys, no signing.
Usage:  python3 approve.py --list
        python3 approve.py <id> approve|skip
        python3 approve.py --expire        (desk.py also runs this every cycle)"""
import sys, time, datetime, config, verify
from common import (get_json, log_task, log_trade, load_state, save_state, load_pending, save_pending,
                    desk_lock, TZ, add_block)

def _now(): return datetime.datetime.now(TZ)
def _latency(prop, at): return round((at - datetime.datetime.fromisoformat(prop["signal_ts"])).total_seconds(), 1)

def current_pair(mint):
    data = get_json("https://api.dexscreener.com/tokens/v1/solana/" + mint) or []
    data = [p for p in data if (p.get("baseToken") or {}).get("address") == mint and p.get("priceUsd")]
    return max(data, key=lambda x: (x.get("liquidity") or {}).get("usd") or 0) if data else None

def expire_stale(at=None):
    """Remove proposals past expires_at, logging EXPIRED with latency. Caller holds desk_lock."""
    at = at or _now(); keep, n = [], 0
    for p in load_pending():
        if at >= datetime.datetime.fromisoformat(p["expires_at"]):
            log_task("APPROVE", p["symbol"], p["mint"], "EXPIRED", [f"id {p['id']}", "not acted on within TTL"],
                     approval_latency_s=_latency(p, at), signal_price=p["signal_price"]); n += 1
            add_block(p["mint"], getattr(config, "PROPOSAL_COOLDOWN_MINUTES", 0), f"cooldown after {p['id']} lapsed", at)
        else: keep.append(p)
    save_pending(keep); return n

def decide(pid, action, at=None, pair_fn=current_pair):
    assert config.PAPER_MODE is True, "PAPER_MODE must be True"
    at = at or _now()
    expire_stale(at)
    pend = load_pending(); prop = next((p for p in pend if p["id"] == pid), None)
    if prop is None: return f"{pid}: not pending (unknown, already decided, or expired)"
    rest = [p for p in pend if p["id"] != pid]; lat = _latency(prop, at)
    tag = [f"id {pid}"]
    def close(decision, reasons, **kw):
        log_task("APPROVE", prop["symbol"], prop["mint"], decision, tag + reasons, approval_latency_s=lat, signal_price=prop["signal_price"], **kw)
        save_pending(rest); return f"{pid}: {decision} ({'; '.join(reasons)}) latency {lat}s"
    if action == "skip":
        add_block(prop["mint"], getattr(config, "SKIP_COOLDOWN_MINUTES", 0), f"cooldown after {pid} skipped", at)
        return close("SKIP", ["skipped by Daniel"])
    pair = pair_fn(prop["mint"])
    if pair is None: return close("REJECTED", ["current price unavailable - no fill"])
    price = float(pair["priceUsd"]); drift = round((price / prop["signal_price"] - 1) * 100, 4)
    fails = verify.verify({"mint": prop["mint"], "pair": pair})
    if fails:
        add_block(prop["mint"], 60 * getattr(config, "HARD_GATE_FAIL_BLOCK_HOURS", 0), f"hard-gate fail at fill ({pid})", at)
        return close("REJECTED", ["hard gates now failing: " + "; ".join(fails)], drift_pct=drift)
    up, dn = getattr(config, "MAX_FILL_DRIFT_UP_PCT", None), getattr(config, "MAX_FILL_DRIFT_DOWN_PCT", None)
    if up is not None and drift > up: return close("REJECTED", [f"price moved {drift:+.1f}% vs signal > +{up}%"], drift_pct=drift)
    if dn is not None and drift < -dn: return close("REJECTED", [f"price moved {drift:+.1f}% vs signal < -{dn}%"], drift_pct=drift)
    s = load_state()
    if len(s["positions"]) >= config.MAX_OPEN_POSITIONS: return close("REJECTED", ["max open positions"], drift_pct=drift)
    if any(x["mint"] == prop["mint"] for x in s["positions"]): return close("REJECTED", ["already holding"], drift_pct=drift)
    usd = min(prop["size_usd"], s["balance"])
    fill = price * (1 + config.PAPER_SLIPPAGE_PCT / 100)
    if usd <= config.PAPER_FEE_USD: return close("REJECTED", ["size not above fee"], drift_pct=drift)
    qty = (usd - config.PAPER_FEE_USD) / fill
    s["balance"] = round(s["balance"] - usd, 2)
    s["positions"].append(dict(symbol=prop["symbol"], mint=prop["mint"], entry=fill, qty=qty, cost=usd, cost_basis=usd,
                               peak=price, entry_liq=(pair.get("liquidity") or {}).get("usd") or 0, opened=time.time(), scaled=0))
    log_trade(side="BUY", symbol=prop["symbol"], mint=prop["mint"], price=fill, qty=qty, usd=usd, cost_basis_usd=usd, pnl_usd="", pnl_pct="",
              reason=f"approved {pid}", balance_after=s["balance"], approval_latency_s=lat, signal_price=prop["signal_price"], drift_pct=drift)
    save_state(s)
    import tickets; tickets.safe_write("BUY", prop["symbol"], prop["mint"], usd, qty, fill, f"approved proposal {pid}")
    return close("APPROVED", [f"filled ${usd} @ {fill} (mkt {price}, slip {config.PAPER_SLIPPAGE_PCT}%, fee ${config.PAPER_FEE_USD})"], drift_pct=drift)

def main(a):
    if a[:1] == ["--list"]:
        with desk_lock(): expire_stale(); pend = load_pending()
        if not pend: print("no pending proposals"); return
        for p in pend: print(f"{p['id']}  {p['symbol']}  {p['mint']}  ${p['size_usd']} @ {p['signal_price']}  signal {p['signal_ts']}  expires {p['expires_at']}")
        return
    if a[:1] == ["--expire"]:
        with desk_lock(): print("expired:", expire_stale()); return
    if len(a) != 2 or a[1] not in ("approve", "skip"): sys.exit(__doc__)
    with desk_lock(): print(decide(a[0], a[1]))
    import export; export.build()

if __name__ == "__main__": main(sys.argv[1:])
