"""Exit-only watcher: runs EXIT on open paper positions. No SCAN/VERIFY/EXECUTE/proposals.
Usage: python3 exit_watch.py [--dry-run]   (--dry-run: report what would happen, change nothing)
Skips the tick if the desk lock is held (full cycle / approve.py running)."""
import os, sys, fcntl, subprocess, config
from common import BASE, LOGS, load_state, now
assert config.PAPER_MODE is True
LOG = os.path.join(LOGS, "exit_watch.log"); MAX_LOG = 512 * 1024
TRADES = os.path.join(LOGS, "trades.csv")

def log(msg):
    if os.path.exists(LOG) and os.path.getsize(LOG) > MAX_LOG: os.replace(LOG, LOG + ".1")
    with open(LOG, "a") as f: f.write(f"{now()} {msg}\n")
    print(msg)

def trade_lines(): return sum(1 for _ in open(TRADES)) if os.path.exists(TRADES) else 0

def deploy():
    """Optional: set DESK_DEPLOY_CMD (e.g. a script that uploads site/ to your static host). Returns rc, or None if unset."""
    cmd = os.environ.get("DESK_DEPLOY_CMD")
    if not cmd: return None
    return subprocess.run(cmd, shell=True, cwd=BASE, capture_output=True, text=True, timeout=300).returncode

def main(dry=False):
    pos = load_state()["positions"]
    if not pos: log("no open positions; idle"); return
    if dry: log(f"dry-run: would run EXIT on {[p['symbol'] for p in pos]}"); return
    lf = open(os.path.join(BASE, ".desk.lock"), "w")
    try: fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: log("desk locked (cycle/approve running); skip tick"); return
    try:
        pos = load_state()["positions"]  # re-read under lock
        if not pos: log("no open positions; idle"); return
        import exit as exit_mod, export
        before = trade_lines(); exit_mod.run(); sells = trade_lines() - before
        s = load_state()
        if sells:
            export.build(); rc = deploy()
            log(f"EXIT wrote {sells} SELL row(s); balance {s['balance']}; open {[p['symbol'] for p in s['positions']]}; deploy rc={rc}")
        else:
            log(f"EXIT checked {[p['symbol'] for p in pos]}: hold; balance {s['balance']}")
    finally: fcntl.flock(lf, fcntl.LOCK_UN); lf.close()

if __name__ == "__main__": main("--dry-run" in sys.argv)
