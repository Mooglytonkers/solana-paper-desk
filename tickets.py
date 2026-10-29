"""Trade tickets (paper). For every paper fill, writes tickets/<id>.json + tickets/<id>.md with a read-only public
Jupiter quote and a jup.ag link. Daniel signs in his own wallet; this desk never holds keys, signs, or connects a wallet."""
import json, os, datetime, urllib.request, config
from common import BASE, TZ
DIR = os.path.join(BASE, "tickets")
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
QUOTE_URLS = ["https://lite-api.jup.ag/swap/v1/quote", "https://quote-api.jup.ag/v6/quote"]
BANNER = "PAPER — do not sign. Simulated fill only; the desk never holds keys or signs. You sign in your own wallet only after an explicit go-live."

def _get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "paper-desk/1.0", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r: return r.status, json.load(r)

def decimals(mint):
    """Token decimals from public Solana RPC (read-only). None if unavailable."""
    try:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTokenSupply", "params": [mint]}).encode()
        return int(_get("https://api.mainnet-beta.solana.com", body)[1]["result"]["value"]["decimals"])
    except Exception: return None

def jupiter_quote(input_mint, output_mint, amount_raw, slippage_bps):
    errors = []
    for base in QUOTE_URLS:
        url = f"{base}?inputMint={input_mint}&outputMint={output_mint}&amount={int(amount_raw)}&slippageBps={slippage_bps}"
        try:
            st, q = _get(url)
            if "outAmount" not in q: errors.append(f"{base}: HTTP {st} no outAmount ({str(q)[:120]})"); continue
            return dict(reachable=True, endpoint=base, request=url, inAmount=q.get("inAmount"), outAmount=q.get("outAmount"),
                        otherAmountThreshold=q.get("otherAmountThreshold"), priceImpactPct=q.get("priceImpactPct"),
                        route=[(r.get("swapInfo") or {}).get("label") for r in q.get("routePlan", [])],
                        fetched_at=datetime.datetime.now(TZ).isoformat(timespec="seconds"))
        except Exception as e: errors.append(f"{base}: {type(e).__name__}: {str(e)[:120]}")
    return dict(reachable=False, errors=errors)

def exit_plan():
    lv = "; ".join(f"sell {int(f*100)}% of remaining at +{g}%" for g, f in config.SCALE_OUT_LEVELS)
    return (f"Full exit on: liquidity -{config.EXIT_LIQUIDITY_DROP_PCT}% vs entry, stop loss -{config.STOP_LOSS_PCT}%, "
            f"time stop {config.TIME_STOP_HOURS}h, trailing stop {config.TRAILING_STOP_PCT}% from peak after first scale-out. Scale-outs: {lv}.")

def write(side, symbol, mint, usd, qty, price, ref, note=""):
    os.makedirs(DIR, exist_ok=True)
    ts = datetime.datetime.now(TZ)
    tid = f"T{ts.strftime('%Y%m%d-%H%M%S')}-{side}-{symbol.strip().replace('/', '_')[:10]}-{mint[:4]}"
    bps = config.TICKET_MAX_SLIPPAGE_BPS
    if side == "BUY":
        q = jupiter_quote(USDC, mint, round(usd * 1e6), bps); link = f"https://jup.ag/swap/USDC-{mint}"
    else:
        d = decimals(mint)
        q = jupiter_quote(mint, USDC, qty * 10 ** d, bps) if d is not None else dict(reachable=False, errors=["token decimals unavailable from public RPC; no quote"])
        link = f"https://jup.ag/swap/{mint}-USDC"
    t = dict(id=tid, banner=BANNER, mode="PAPER", created_at=ts.isoformat(timespec="seconds"), side=side, symbol=symbol, mint=mint,
             size_usd=usd, qty=qty, paper_fill_price=price, max_slippage_bps=bps, quote_pair=("USDC->" + symbol) if side == "BUY" else (symbol + "->USDC"),
             jupiter_quote=q, jupiter_link=link, exit_plan=exit_plan(), ref=ref, note=note,
             unsigned_tx=None, self_custody="You sign in your own wallet; the desk never holds keys.")
    json.dump(t, open(os.path.join(DIR, tid + ".json"), "w"), indent=2)
    qs = (f"- Endpoint: {q['endpoint']}\n- Route: {' → '.join(x or '?' for x in q['route'])}\n- outAmount (raw units): {q['outAmount']}\n"
          f"- Min out at {bps} bps: {q['otherAmountThreshold']}\n- Price impact: {q['priceImpactPct']}\n- Quoted at: {q['fetched_at']}") if q.get("reachable") \
         else "- Jupiter quote UNAVAILABLE: " + " | ".join(q.get("errors", []))
    md = f"""# {BANNER}

**Ticket {tid}** ({t['created_at']})

- Side: {side}
- Symbol: {symbol}
- Mint: `{mint}`
- Size: ${usd}  (paper qty {qty}, paper fill price {price})
- Max slippage: {bps} bps
- Jupiter swap link: {link}

## Jupiter quote (read-only, {t['quote_pair']})
{qs}

## Exit plan
{exit_plan()}

Ref: {ref}. {note}
No unsigned transaction was built. That needs your public wallet address and an explicit go-live.
"""
    open(os.path.join(DIR, tid + ".md"), "w").write(md)
    return tid

def build_unsigned_tx(*a, **k):
    """Stub. Never signs. Will only ever build an UNSIGNED tx for Daniel to sign in his own wallet, after go-live."""
    if config.PAPER_MODE is not False or not getattr(config, "WALLET_PUBLIC_ADDRESS", None):
        raise RuntimeError("build_unsigned_tx disabled: requires PAPER_MODE = False AND WALLET_PUBLIC_ADDRESS set, with Daniel's explicit go-live approval")
    raise NotImplementedError("unsigned tx building not implemented yet")

def safe_write(*a, **k):
    """Ticket writing must never break a fill/cycle."""
    try: return write(*a, **k)
    except Exception as e:
        from common import log_task
        log_task("TICKET", a[1] if len(a) > 1 else "-", a[2] if len(a) > 2 else "-", "TICKET_FAILED", [f"{type(e).__name__}: {e}"[:200]]); return None
