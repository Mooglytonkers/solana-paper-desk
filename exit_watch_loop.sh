#!/bin/bash
# Supervised loop: runs exit_watch.py every 120s. PID in /workspace/desk/.exit_watch.pid
cd /workspace/desk || exit 1
echo $$ > .exit_watch.pid
while true; do timeout 280 python3 exit_watch.py >/dev/null 2>>logs/exit_watch.err; sleep 120; done
