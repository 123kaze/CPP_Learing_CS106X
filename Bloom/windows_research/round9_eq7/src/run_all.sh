#!/usr/bin/env bash
# Runs every job of $SCRIPT (default eq7_offline.py), 4 at a time (Caida-sized processes use ~2.5 GB each).
cd "$(dirname "$0")/.."
PY=../../.condaenv/bin/python
SCRIPT=${1:-eq7_offline.py}; TAG=; [ "$SCRIPT" = eq7_offline.py ] || TAG=${SCRIPT%.py}_
job() {
  if [ "$1" = holdout ]; then
    $PY -u ../round6_bucket/src/holdout6.py run src/$SCRIPT holdout > results/logs/${TAG}holdout.log 2>&1
  else
    $PY -u src/$SCRIPT seeds "$1" "$2" > "results/logs/${TAG}$1_$2.log" 2>&1
  fi
  echo "done $1 $2 exit $?"
}
export -f job; export PY SCRIPT TAG
mkdir -p results/logs
printf '%s\n' "caida 128" "caida 256" "caida 1024" "caida 2048" "cod 256" "cod 1024" "cod 4096" \
  "shalla 256" "shalla 1024" "shalla 2048" "shalla 4096" "url 64" "url 128" "url 256" "holdout x" |
  xargs -P 4 -L 1 bash -c 'job "$0" "$1"'
