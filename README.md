# Solana Paper Desk

> ## ⚠️ Disclaimer
> **Paper trading / entertainment only. Not financial advice.** Memecoins are extremely risky; most go to zero and many are scams.
> This software simulates trades with fake money. It holds no keys, never signs, never connects a wallet and has no live mode.
> Provided "as is", with **no warranty** of any kind (see [LICENSE](LICENSE)). Use at your own risk.

A small four-role **paper** trading desk for Solana memecoins, built on public **DexScreener** and **RugCheck** data:

| Role | What it does |
|---|---|
| **SCAN** | Pulls the latest Solana token profiles from DexScreener and their deepest-liquidity pair. Never judges. |
| **VERIFY** | Hard gates (liquidity, pair age, vol/liq band, momentum, RugCheck: mint/freeze authority, LP lock, holder concentration, danger flags). **SKIP is the default**; a token passes only if every gate is proven. |
| **EXECUTE** | Sizes a paper entry from the paper balance. With approvals on, it creates a *proposal* in `pending.json` instead of filling. |
| **EXIT** | Applies the exit rules to open paper positions. |

It has a heavy skip bias and **logs every decision**: every task (including skips, with reasons) goes to `logs/tasks.csv`, and every fill to `logs/trades.csv`. `export.py` builds `data.json` for a static, single-file dashboard (`site/index.html`).

## Quickstart

Requirements: Python 3.9+ on Linux or macOS (uses `zoneinfo` and `fcntl`). No third-party packages (`requirements.txt` is empty on purpose).

```bash
git clone <your fork> && cd solana-paper-desk
python3 desk.py                    # one cycle: expire proposals -> EXIT -> SCAN -> VERIFY -> EXECUTE -> export
python3 approve.py --list          # show pending proposals
python3 approve.py <id> approve    # paper-fill at the current price (gates are re-checked first)
python3 approve.py <id> skip
python3 export.py                  # rebuild data.json + site/data.json
python3 -m http.server -d site 8000   # open http://localhost:8000
```

Run `desk.py` on a schedule (cron, systemd timer, etc.), e.g. every 15 minutes. All state is repo-local: `state.json`, `pending.json`, `logs/`, `tickets/`, `data.json` (all git-ignored).

### Optional: fast exit watcher
`exit_watch_loop.sh` runs `exit_watch.py` every 2 minutes, applying only the EXIT rules to open positions (no scanning or new entries). It skips a tick if a cycle/approval holds the desk lock.

```bash
nohup ./exit_watch_loop.sh >/dev/null 2>&1 &
```

If `DESK_DEPLOY_CMD` is set, it runs that shell command after any paper sell (e.g. your own script that uploads `site/`).

## Approval flow
With `APPROVAL_REQUIRED = True` and the current time after `APPROVAL_START`, VERIFY survivors become proposals with an id like `P1a2b3c`, the signal price and an expiry (`PROPOSAL_TTL_MINUTES`). Nothing fills until `approve.py <id> approve`, which re-fetches the price, re-runs VERIFY, applies slippage/fee and logs approval latency and price drift. Unacted proposals are logged as `EXPIRED`.

Each paper fill also writes an informational ticket in `tickets/` with a read-only public Jupiter quote. No transaction is ever built.

## Dashboard / deploy
`site/index.html` reads `data.json` from the same folder. `export.py` writes it to both the repo root and `site/`. To publish, upload the `site/` folder to any static host using **your own** account, e.g. Cloudflare Pages:

```bash
npx wrangler pages deploy site --project-name <your-project> --branch main
```

(Netlify, GitHub Pages, S3, etc. work the same way.) Note the dashboard shows your balance and trades publicly if you publish it.

## Config knobs (`config.py`, example defaults)
Code reads `config.py`; it never writes it.

| Knob | Default | Meaning |
|---|---|---|
| `PAPER_MODE` | `True` | Hard guard. EXECUTE/EXIT/approve assert it is `True`. There is no live mode. |
| `STARTING_PAPER_BALANCE` | 1000 | Starting fake USD. |
| `RISK_PER_TRADE_PCT` | 5 | % of current balance per entry. |
| `MAX_OPEN_POSITIONS` | 3 | Max concurrent positions. |
| `MIN_LIQUIDITY_USD` | 50,000 | Min pair liquidity. |
| `MIN_PAIR_AGE_HOURS` | 2 | Min pair age. |
| `REQUIRE_LP_LOCKED_OR_BURNED` / `MIN_LP_LOCKED_PCT` | True / 90 | RugCheck LP lock requirement. |
| `MAX_TOP_HOLDER_PCT` / `MAX_DEV_HOLDER_PCT` | 30 / 10 | Holder-concentration limits (enforced via RugCheck flags). |
| `REQUIRE_MINT_FREEZE_REVOKED` | True | Fail if mint or freeze authority is live. |
| `MAX_RUGCHECK_SCORE_NORM` | 50 | Max RugCheck normalised score (higher = riskier). |
| `MIN_VOL_LIQ_RATIO` / `MAX_VOL_LIQ_RATIO` | 0.1 / 20 | 24h volume ÷ liquidity sanity band. |
| `SOCIAL_CHECK_ENABLED` | False | Stub hook for a narrative/social check. |
| `EXIT_LIQUIDITY_DROP_PCT` | 40 | Exit if liquidity drops this much vs entry. |
| `STOP_LOSS_PCT` | 25 | Stop loss. |
| `SCALE_OUT_LEVELS` | `[(50,0.5),(100,0.5)]` | (gain %, fraction of remaining to sell). |
| `TRAILING_STOP_PCT` | 20 | Trailing stop from peak, active after the first scale-out. |
| `TIME_STOP_HOURS` | 24 | Max holding time. |
| `MAX_CANDIDATES` | 30 | Tokens scanned per cycle. |
| `WHALE_WATCH_ENABLED` | False | Stub second scan source. |
| `APPROVAL_REQUIRED` / `APPROVAL_START` | True / ISO time | Proposal mode and when it starts. |
| `PROPOSAL_TTL_MINUTES` | 15 | Proposal lifetime. |
| `PAPER_SLIPPAGE_PCT` / `PAPER_FEE_USD` | 0 / 0 | Simulated slippage and flat fee on approved fills. |
| `TICKET_MAX_SLIPPAGE_BPS` | 100 | Slippage used for the informational Jupiter quote. |
| `MOMENTUM_*` | see below | Momentum gate. |

### Momentum gate (falling-knife filter)
Skip if any of: 5-minute price change < `MOMENTUM_MIN_CHANGE_5M_PCT` (−10%), 1-hour change < `MOMENTUM_MIN_CHANGE_1H_PCT` (−20%), or 5-minute sells/buys > `MOMENTUM_MAX_SELL_BUY_RATIO_5M` (1.5). Set a knob to `None` (or delete it) to disable that check.

### Exit rules
Full exit on any of: liquidity −40% vs entry, −25% stop loss, 24h time stop, or (after the first scale-out) price 20% below the peak. Scale out half the remaining position at +50% and half again at +100%.

## License
MIT. See [LICENSE](LICENSE).
