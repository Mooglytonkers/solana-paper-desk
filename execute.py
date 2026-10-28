"""EXECUTE: paper fills only. No keys, no signing, no network writes.
Before config.APPROVAL_START (or if APPROVAL_REQUIRED is False): fills VERIFY survivors immediately, as before.
After it: VERIFY survivors become PROPOSED entries in pending.json; no fill until approve.py."""
import datetime, hashlib, config
from common import log_task, log_trade, load_state, save_state, load_pending, save_pending, now, TZ

def approval_active(at=None):
    at = at or datetime.datetime.now(TZ)
    return bool(getattr(config, "APPROVAL_REQUIRED", False)) and at >= datetime.datetime.fromisoformat(config.APPROVAL_START)

def run(passed):
    assert config.PAPER_MODE is True, "PAPER_MODE must be True; live trading not supported"
    s, entries = load_state(), []
    pending = load_pending() if approval_active() else None
    for c in passed:
        p, sym = c["pair"], c["pair"]["baseToken"]["symbol"]
        if len(s["positions"]) >= config.MAX_OPEN_POSITIONS:
            log_task("EXECUTE", sym, c["mint"], "SKIP", ["max open positions"]); continue
        if any(x["mint"] == c["mint"] for x in s["positions"]):
            log_task("EXECUTE", sym, c["mint"], "SKIP", ["already holding"]); continue
        usd = round(s["balance"] * config.RISK_PER_TRADE_PCT / 100, 2)
        price = float(p["priceUsd"])
        if pending is not None:
            if any(x["mint"] == c["mint"] for x in pending):
                log_task("EXECUTE", sym, c["mint"], "SKIP", ["proposal already pending"]); continue
            ts = now(); exp = (datetime.datetime.fromisoformat(ts) + datetime.timedelta(minutes=config.PROPOSAL_TTL_MINUTES)).isoformat(timespec="seconds")
            pid = "P" + hashlib.sha1((c["mint"] + ts).encode()).hexdigest()[:6]
            prop = dict(id=pid, symbol=sym, mint=c["mint"], signal_price=price, signal_ts=ts, size_usd=usd,
                        signal_liq=(p.get("liquidity") or {}).get("usd"), reasons=["all VERIFY gates passed"], expires_at=exp)
            pending.append(prop)
            log_task("EXECUTE", sym, c["mint"], "PROPOSE", [f"id {pid}", f"${usd} @ signal {price}", f"expires {exp}"], signal_price=price)
            continue
        qty = usd / price
        s["balance"] = round(s["balance"] - usd, 2)
        pos = dict(symbol=sym, mint=c["mint"], entry=price, qty=qty, cost=usd, cost_basis=usd, peak=price,
                   entry_liq=p["liquidity"]["usd"], opened=__import__("time").time(), scaled=0)
        s["positions"].append(pos); entries.append(pos)
        log_trade(side="BUY", symbol=sym, mint=c["mint"], price=price, qty=qty, usd=usd, cost_basis_usd=usd, pnl_usd="", pnl_pct="", reason="VERIFY pass", balance_after=s["balance"])
        log_task("EXECUTE", sym, c["mint"], "PAPER_BUY", [f"${usd} @ {price}"])
        import tickets; tickets.safe_write("BUY", sym, c["mint"], usd, qty, price, "EXECUTE paper fill")
    if pending is not None: save_pending(pending)
    save_state(s); return entries
