"""EXIT: applies config EXIT rules to open paper positions."""
import time, config
from common import get_json, log_task, log_trade, load_state, save_state

def _sell(s, pos, frac, price, reason):
    # Realized P&L uses the proportional share of the REMAINING cost basis for the qty sold.
    qty = pos["qty"] * frac; usd = round(qty * price, 2)
    basis = pos.get("cost_basis", pos["cost"])
    sold_basis = basis if frac >= 1.0 else basis * qty / pos["qty"]
    pnl = usd - sold_basis
    pos["qty"] -= qty; pos["cost_basis"] = basis - sold_basis
    s["balance"] = round(s["balance"] + usd, 2)
    log_trade(side="SELL", symbol=pos["symbol"], mint=pos["mint"], price=price, qty=qty, usd=usd,
              cost_basis_usd=round(sold_basis, 6), pnl_usd=round(pnl, 6), pnl_pct=round(pnl / sold_basis * 100, 4) if sold_basis else "",
              reason=reason, balance_after=s["balance"])
    log_task("EXIT", pos["symbol"], pos["mint"], "PAPER_SELL", [reason])
    import tickets; tickets.safe_write("SELL", pos["symbol"], pos["mint"], usd, qty, price, f"EXIT {reason}")

def run():
    assert config.PAPER_MODE is True
    s = load_state(); keep = []
    for pos in s["positions"]:
        data = get_json("https://api.dexscreener.com/tokens/v1/solana/" + pos["mint"]) or []
        if not data: log_task("EXIT", pos["symbol"], pos["mint"], "HOLD", ["no price data"]); keep.append(pos); continue
        p = max(data, key=lambda x: (x.get("liquidity") or {}).get("usd", 0))
        price, liq = float(p["priceUsd"]), (p.get("liquidity") or {}).get("usd", 0)
        pos["peak"] = max(pos["peak"], price); gain = (price / pos["entry"] - 1) * 100
        full = None
        if liq < pos["entry_liq"] * (1 - config.EXIT_LIQUIDITY_DROP_PCT / 100): full = "liquidity drop"
        elif gain <= -config.STOP_LOSS_PCT: full = "stop loss"
        elif (time.time() - pos["opened"]) / 3600 >= config.TIME_STOP_HOURS: full = "time stop"
        elif pos["scaled"] and price <= pos["peak"] * (1 - config.TRAILING_STOP_PCT / 100): full = "trailing stop"
        if full: _sell(s, pos, 1.0, price, full); continue
        while pos["scaled"] < len(config.SCALE_OUT_LEVELS) and gain >= config.SCALE_OUT_LEVELS[pos["scaled"]][0]:
            lvl, frac = config.SCALE_OUT_LEVELS[pos["scaled"]]; _sell(s, pos, frac, price, f"scale-out +{lvl}%"); pos["scaled"] += 1
        if pos["qty"] > 1e-12: keep.append(pos); log_task("EXIT", pos["symbol"], pos["mint"], "HOLD", [f"pnl {gain:+.1f}%"])
    s["positions"] = keep; save_state(s)
