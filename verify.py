"""VERIFY: hard skips first. SKIP is the default; PASS only if every gate is proven."""
import time, config
from common import get_json, log_task

def social_check(c):  # optional stub for survivors only
    return []

def momentum(p):
    """Falling-knife gate. Thresholds come from config; a missing name (or None) disables that check.
    Missing pair data passes (noted only if every enabled check lacked data)."""
    r, missing = [], []
    pc, tx5 = p.get("priceChange") or {}, (p.get("txns") or {}).get("m5") or {}
    for key, name in (("m5", "MOMENTUM_MIN_CHANGE_5M_PCT"), ("h1", "MOMENTUM_MIN_CHANGE_1H_PCT")):
        lim = getattr(config, name, None)
        if lim is None: continue
        v = pc.get(key)
        if v is None: missing.append(key); continue
        if float(v) < lim: r.append(f"momentum: {key} {float(v):+.1f}% < {lim}%")
    lim = getattr(config, "MOMENTUM_MAX_SELL_BUY_RATIO_5M", None)
    if lim is not None:
        b, s = tx5.get("buys"), tx5.get("sells")
        if b is None or s is None: missing.append("m5 txns")
        elif (s / b if b else (float("inf") if s else 0)) > lim:
            r.append(f"momentum: m5 sells/buys {s}/{b} > {lim}")
    return r, missing

def verify(c):
    if getattr(config, "BINANCE_US_ONLY", False):  # gate #1: canonical Binance.US mint, else skip immediately
        import binance_us
        sym = ((c.get("pair") or {}).get("baseToken") or {}).get("symbol")
        g = binance_us.gate(c["mint"], sym)
        if g: return g
    p, r = c["pair"], []
    if not p: return ["no Solana pair data"]
    liq = (p.get("liquidity") or {}).get("usd") or 0
    vol = (p.get("volume") or {}).get("h24") or 0
    age_h = (time.time()*1000 - (p.get("pairCreatedAt") or time.time()*1000)) / 3.6e6
    if liq < config.MIN_LIQUIDITY_USD: r.append(f"liquidity ${liq:,.0f} < ${config.MIN_LIQUIDITY_USD:,}")
    if age_h < config.MIN_PAIR_AGE_HOURS: r.append(f"pair age {age_h:.1f}h < {config.MIN_PAIR_AGE_HOURS}h")
    ratio = vol / liq if liq else 0
    if liq and not (config.MIN_VOL_LIQ_RATIO <= ratio <= config.MAX_VOL_LIQ_RATIO): r.append(f"vol/liq {ratio:.2f} outside sanity band")
    r += momentum(p)[0]
    if r: return r  # cheap fails: skip before hitting RugCheck
    rc = get_json(f"https://api.rugcheck.xyz/v1/tokens/{c['mint']}/report/summary")
    if rc is None: return ["RugCheck unreachable - cannot prove safety"]
    names = " | ".join(x.get("name", "") for x in rc.get("risks", [])).lower()
    if config.REQUIRE_MINT_FREEZE_REVOKED and ("mint authority" in names or "freeze authority" in names):
        r.append("mint/freeze authority not revoked")
    if config.REQUIRE_LP_LOCKED_OR_BURNED and (rc.get("lpLockedPct") or 0) < config.MIN_LP_LOCKED_PCT:
        r.append(f"LP locked {rc.get('lpLockedPct') or 0:.0f}% < {config.MIN_LP_LOCKED_PCT}%")
    if "top 10" in names or "high ownership" in names or "single holder" in names:
        r.append(f"holder concentration flag (>{config.MAX_TOP_HOLDER_PCT}% top / dev)")
    if (rc.get("score_normalised") or 0) > config.MAX_RUGCHECK_SCORE_NORM: r.append(f"RugCheck score {rc.get('score_normalised')} high")
    for x in rc.get("risks", []):
        if x.get("level") == "danger" or "honeypot" in x.get("name", "").lower(): r.append(f"danger flag: {x.get('name')}")
    if not r and config.SOCIAL_CHECK_ENABLED: r += social_check(c)
    return sorted(set(r))

def run(cands):
    passed = []
    for c in cands:
        sym = (c["pair"] or {}).get("baseToken", {}).get("symbol", "?")
        reasons = verify(c)
        if not reasons:
            p = c["pair"] or {}; pc, tx = p.get("priceChange") or {}, (p.get("txns") or {}).get("m5") or {}
            b, s = tx.get("buys"), tx.get("sells")
            sb = (f"{s/b:.2f}" if b else "n/a") if b is not None and s is not None else "n/a"
            log_reasons = ["all gates passed", f"momentum m5 {pc.get('m5')}% h1 {pc.get('h1')}% m5 sells/buys {s}/{b} ({sb})"]
        log_task("VERIFY", sym, c["mint"], "SKIP" if reasons else "PASS", reasons or log_reasons)
        if not reasons: passed.append(c)
        else: c["reasons"] = reasons
    return passed
