"""Builds data.json for the dashboard from state.json, logs/tasks.csv, logs/trades.csv. Read-only on inputs.
Only network use: DexScreener GET for marking open positions (unrealized P&L); null if unavailable."""
import csv, json, os, re, collections, datetime
BASE = os.path.dirname(os.path.abspath(__file__))
def rows(name):
    p = os.path.join(BASE, "logs", name)
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []
def reason_key(r):
    r = r.strip()
    if r.startswith("liquidity"): return "low liquidity"
    if r.startswith("pair age"): return "pair too young"
    if r.startswith("vol/liq"): return "vol/liq out of band"
    return re.sub(r"[\d$.,%]+", "", r).strip() or r
def num(x):
    try: return float(x) if x not in (None, "") else None
    except ValueError: return None
def dex_price(mint):
    from common import get_json
    data = get_json("https://api.dexscreener.com/tokens/v1/solana/" + mint) or []
    data = [p for p in data if (p.get("baseToken") or {}).get("address") == mint and p.get("priceUsd")]
    if not data: return None
    return num(max(data, key=lambda x: (x.get("liquidity") or {}).get("usd") or 0)["priceUsd"])
def build(price_fn=dex_price):
    import config
    sp = os.path.join(BASE, "state.json")
    state = json.load(open(sp)) if os.path.exists(sp) else {"balance": None, "positions": []}
    tasks, trades = rows("tasks.csv"), rows("trades.csv")
    v = [t for t in tasks if t["role"] == "VERIFY"]
    skips = [t for t in v if t["decision"] == "SKIP"]
    br = collections.Counter(reason_key(r) for t in skips for r in t["reasons"].split(";") if r.strip())
    sells = []
    for t in trades:
        if t.get("side") != "SELL": continue
        pu, pp = num(t.get("pnl_usd")), num(t.get("pnl_pct"))
        sells.append(dict(t, pnl_usd=pu, pnl_pct=pp, cost_basis_usd=num(t.get("cost_basis_usd")),
                          token=t.get("symbol"), time=t.get("ts"), pnl=round(pu, 2) if pu is not None else None))
    known = [s["pnl_usd"] for s in sells if s["pnl_usd"] is not None]
    realized = round(sum(known), 2)
    opens = []
    for p in state.get("positions", []):
        basis = p.get("cost_basis", p.get("cost"))
        price = price_fn(p["mint"])
        mv = p["qty"] * price if price is not None else None
        u = mv - basis if mv is not None else None
        opens.append(dict(p, cost_basis_usd=basis, mark_price=price, market_value_usd=round(mv, 2) if mv is not None else None,
                          unrealized_pnl_usd=round(u, 2) if u is not None else None,
                          unrealized_pnl_pct=round(u / basis * 100, 2) if u is not None and basis else None))
    ux = [o["unrealized_pnl_usd"] for o in opens]
    unreal = round(sum(ux), 2) if opens and all(x is not None for x in ux) else (0.0 if not opens else None)
    # Approval workflow (paper)
    import statistics
    pp = os.path.join(BASE, "pending.json")
    pending = json.load(open(pp)) if os.path.exists(pp) else []
    ap = [t for t in tasks if t["role"] == "APPROVE"]
    cnt = collections.Counter(t["decision"] for t in ap)
    lats = [x for x in (num(t.get("approval_latency_s")) for t in ap) if x is not None]
    drifts = [x for x in (num(t.get("drift_pct")) for t in ap if t["decision"] == "APPROVED") if x is not None]
    astats = {"approved": cnt.get("APPROVED", 0), "skipped": cnt.get("SKIP", 0), "expired": cnt.get("EXPIRED", 0),
              "rejected": cnt.get("REJECTED", 0), "proposed": sum(1 for t in tasks if t["decision"] == "PROPOSE"),
              "median_latency_s": round(statistics.median(lats), 1) if lats else None,
              "avg_drift_pct": round(sum(drifts) / len(drifts), 4) if drifts else None}
    import execute, glob
    tix = []
    for f in sorted(glob.glob(os.path.join(BASE, "tickets", "*.json")), key=os.path.getmtime, reverse=True)[:10]:
        t = json.load(open(f)); q = t.get("jupiter_quote") or {}
        tix.append(dict(id=t["id"], side=t["side"], symbol=t["symbol"], mint=t["mint"], size_usd=t["size_usd"], created_at=t["created_at"],
                        jupiter_link=t["jupiter_link"], quote_ok=bool(q.get("reachable")), out_amount=q.get("outAmount"),
                        price_impact=q.get("priceImpactPct"), md="tickets/" + t["id"] + ".md"))
    now = datetime.datetime.now().astimezone()
    skip_rate = round(len(skips)/len(v), 4) if v else None
    data = {
        "generated_at": now.isoformat(timespec="seconds"), "paper_mode": True,
        "balance": state.get("balance"), "open_positions": opens,
        "total_tasks": len(tasks), "verify_decisions": len(v), "skips": len(skips), "skip_rate": skip_rate,
        "skip_reasons": dict(br.most_common()), "recent_tasks": tasks[-30:],
        "realized_pnl_usd": realized, "unrealized_pnl_usd": unreal,
        "trades": sells, "all_fills": trades,
        "approval_required": bool(getattr(config, "APPROVAL_REQUIRED", False)), "approval_start": getattr(config, "APPROVAL_START", None),
        "mode": "PAPER" if config.PAPER_MODE else "LIVE",
        "self_custody_note": "You sign in your wallet; desk never holds keys.", "latest_tickets": tix,
        "approval_active": execute.approval_active(), "pending_proposals": pending, "approval_stats": astats,
        # camelCase keys read by the dashboard (site/index.html)
        "startBalance": config.STARTING_PAPER_BALANCE, "maxOpen": config.MAX_OPEN_POSITIONS,
        "positions": [dict(token=o.get("symbol"), size=round(o["cost_basis_usd"], 2), pnl=o["unrealized_pnl_usd"],
                           pnlPct=o["unrealized_pnl_pct"], markPrice=o["mark_price"], entryPrice=o.get("entry"), rules="paper EXIT rules") for o in opens],
        "totalTasks": len(tasks), "skipCount": len(skips), "skipRate": round(100*skip_rate) if skip_rate is not None else 0,
        "sessionPnl": realized, "realizedPnl": realized, "unrealizedPnl": unreal,
        "wins": sum(1 for x in known if x > 0), "losses": sum(1 for x in known if x < 0),
        "skipReasons": dict(br.most_common()), "tasks": tasks[-30:],
        "updated": now.strftime("%Y-%m-%d %H:%M ET"),
        "modeLabel": "PAPER" if config.PAPER_MODE else "LIVE",
        "selfCustodyNote": "You sign in your wallet; desk never holds keys.",
        "latestTickets": [dict(id=t["id"], side=t["side"], token=t["symbol"], size=t["size_usd"], link=t["jupiter_link"],
                               quoteOk=t["quote_ok"], outAmount=t["out_amount"], priceImpact=t["price_impact"], created=t["created_at"]) for t in tix],
        "approvalActive": execute.approval_active(), "approvalStart": getattr(config, "APPROVAL_START", None),
        "pendingProposals": [dict(id=p["id"], token=p["symbol"], mint=p["mint"], size=p["size_usd"], signalPrice=p["signal_price"],
                                  signalTs=p["signal_ts"], expiresAt=p["expires_at"]) for p in pending],
        "approvalStats": {"approved": astats["approved"], "skipped": astats["skipped"], "expired": astats["expired"],
                          "rejected": astats["rejected"], "proposed": astats["proposed"],
                          "medianLatencyS": astats["median_latency_s"], "avgDriftPct": astats["avg_drift_pct"]},
    }
    out = json.dumps(data, indent=2)
    for p in (os.path.join(BASE, "data.json"), os.path.join(BASE, "site", "data.json")):  # site/ copy so the dashboard can be served as-is
        if os.path.isdir(os.path.dirname(p)): open(p, "w").write(out)
    return data
if __name__ == "__main__": build()
