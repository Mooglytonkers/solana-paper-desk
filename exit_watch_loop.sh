#!/bin/bash
# Supervised loop: runs exit_watch.py every 120s from the repo directory. PID written to .exit_watch.pid
cd "$(dirname "$0")" || exit 1
mkdir -p logs
echo $$ > .exit_watch.pid
while true; do timeout 280 python3 exit_watch.py >/dev/null 2>>logs/exit_watch.err; sleep 120; done
