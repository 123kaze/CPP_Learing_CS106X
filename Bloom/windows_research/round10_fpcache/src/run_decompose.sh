#!/usr/bin/env bash
# decompose.py over every round-6 main-table setting, 4 jobs at a time.
cd "$(dirname "$0")/.."
export PY=../../.condaenv/bin/python
mkdir -p results/logs
job() {
  $PY -u src/decompose.py --dataset "$1" ${2:+--budgets "$2"} > "results/logs/decompose_$1${2:+-$2}.log" 2>&1
  echo "done $1 $2 exit $?"
}
export -f job
printf '%s\n' "caida 128,256" "caida 1024,2048" "shalla 256,1024" "shalla 2048,4096" "cod" "url" \
  "caida_flow" "mawi2020_flow" "mawi2021_flow" "mawi2022_flow" |
  xargs -P 4 -L 1 bash -c 'job "$0" "$1"'
