"""Editable paper-desk parameters. Code reads these; it never writes them.
All values below are EXAMPLE DEFAULTS - tune them for your own paper testing."""
PAPER_MODE = True  # hard guard: execute/exit refuse to run if not True. No live mode exists; the desk never holds keys or signs.

STARTING_PAPER_BALANCE = 1000.0   # USD
RISK_PER_TRADE_PCT = 5.0          # % of current paper balance per entry
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

# APPROVAL (paper). After APPROVAL_START, VERIFY survivors become proposals
# in pending.json and only fill via `python3 approve.py <id> approve`.
APPROVAL_REQUIRED = True
APPROVAL_START = '2026-01-01T00:00:00-05:00'  # proposals required for any cycle after this time
PROPOSAL_TTL_MINUTES = 15         # example default
PAPER_SLIPPAGE_PCT = 0.0          # added on approved fills (buy price * (1 + pct/100)); 0 = unchanged behavior
PAPER_FEE_USD = 0.0               # flat USD fee per approved fill, deducted from size; 0 = unchanged behavior

# TICKETS (paper). Informational trade tickets only; the desk never holds keys or signs.
TICKET_MAX_SLIPPAGE_BPS = 100     # example default; max slippage written on trade tickets / used for Jupiter quotes

# MOMENTUM (falling-knife gate in VERIFY). Remove a line or set it to None to disable that check.
MOMENTUM_MIN_CHANGE_5M_PCT = -10      # skip if 5-minute price change < -10%
MOMENTUM_MIN_CHANGE_1H_PCT = -20      # skip if 1-hour price change < -20%
MOMENTUM_MAX_SELL_BUY_RATIO_5M = 1.5  # skip if 5-minute sells/buys > 1.5
