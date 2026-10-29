"""Editable paper-desk parameters. Code reads these; it never writes them."""
PAPER_MODE = True  # hard guard: execute/exit refuse to run if not True. Live mode = Daniel signs every tx himself.

STARTING_PAPER_BALANCE = 1000.0   # USD
RISK_PER_TRADE_PCT = 10.0         # % of current paper balance per entry (raised 5 -> 10 by Daniel 2026-10-29)
MAX_OPEN_POSITIONS = 3

# VERIFY hard gates (any failure = SKIP; SKIP is default)
MIN_LIQUIDITY_USD = 50_000
MIN_PAIR_AGE_HOURS = 2
REQUIRE_LP_LOCKED_OR_BURNED = True
MIN_LP_LOCKED_PCT = 90
MAX_TOP_HOLDER_PCT = 30           # top-10 concentration; RugCheck "high ownership" flags fail this
MAX_DEV_HOLDER_PCT = 10
REQUIRE_MINT_FREEZE_REVOKED = True
MAX_RUGCHECK_SCORE_NORM = 50      # RugCheck score_normalised (higher = riskier)
MIN_VOL_LIQ_RATIO = 0.1           # 24h volume / liquidity sanity band
MAX_VOL_LIQ_RATIO = 20
SOCIAL_CHECK_ENABLED = False      # optional narrative stub for survivors

# EXIT rules
EXIT_LIQUIDITY_DROP_PCT = 40      # vs liquidity at entry
STOP_LOSS_PCT = 25
SCALE_OUT_LEVELS = [(50, 0.5), (100, 0.5)]  # (gain %, fraction of remaining to sell)
TRAILING_STOP_PCT = 20            # from peak, active after first scale-out
TIME_STOP_HOURS = 24

# SCAN
MAX_CANDIDATES = 30
WHALE_WATCH_ENABLED = False

# APPROVAL (paper). Added 2026-10-21 per Daniel. After APPROVAL_START, VERIFY survivors become proposals
# in pending.json and only fill via `python3 approve.py <id> approve`.
APPROVAL_REQUIRED = True
APPROVAL_START = '2026-10-21T12:00:00-04:00'
PROPOSAL_TTL_MINUTES = 20         # set by Daniel 2026-10-29 review (was placeholder 15)
PAPER_SLIPPAGE_PCT = 0.0          # PLACEHOLDER - added on approved fills (buy price * (1 + pct/100)); 0 = unchanged behavior
PAPER_FEE_USD = 0.0               # PLACEHOLDER - flat USD fee per approved fill, deducted from size; 0 = unchanged behavior

# BINANCE.US UNIVERSE (paper). Added 2026-10-21 per Daniel (trades only on Binance.US).
BINANCE_US_ONLY = False           # set False by Daniel 2026-10-21 07:13 ET (gate fully bypassed); VERIFY gate #1: mint must be the canonical Solana mint of a TRADING Binance.US base asset
BINANCE_US_REFRESH_HOURS = 24     # PLACEHOLDER - Daniel to confirm; allowlist refetch interval

# SELF-CUSTODY / TICKETS (paper). Daniel signs in his own wallet (Phantom); the desk never holds keys or signs.
WALLET_PUBLIC_ADDRESS = None      # public address only; needed (with PAPER_MODE False + Daniel's go-live OK) before any unsigned tx is built
TICKET_MAX_SLIPPAGE_BPS = 100     # PLACEHOLDER - Daniel to confirm; max slippage written on trade tickets / used for Jupiter quotes

# MOMENTUM (falling-knife gate in VERIFY). Remove a line or set it to None to disable that check.
MOMENTUM_MIN_CHANGE_5M_PCT = -10      # skip if 5-minute price change < -10%
MOMENTUM_MIN_CHANGE_1H_PCT = -20      # skip if 1-hour price change < -20%
MOMENTUM_MAX_SELL_BUY_RATIO_5M = 1.5  # skip if 5-minute sells/buys > 1.5

# --- 2026-10-29 rules review (approved by Daniel) ---
PROPOSAL_COOLDOWN_MINUTES = 60      # per mint: no new proposal for this long after one lapses (EXPIRED)
SKIP_COOLDOWN_MINUTES = 60          # per mint: no new proposal for this long after Daniel skips one (added 2026-10-29)
HARD_GATE_FAIL_BLOCK_HOURS = 24     # per mint: no new proposal after a fill-time hard-gate rejection
MAX_FILL_DRIFT_UP_PCT = 10          # approve.py rejects if price is > +10% vs signal at fill
MAX_FILL_DRIFT_DOWN_PCT = 25        # approve.py rejects if price is < -25% vs signal at fill
MIN_CYCLE_INTERVAL_SECONDS = 60     # desk.py double-run guard: skip if last cycle started < this many seconds ago

