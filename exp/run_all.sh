#!/bin/bash
# Full experiment grid. Each run writes _results/runs/<tag>.json and skips if present.
cd "D:/paper publish"
PY=./.venv310/Scripts/python.exe
LOG=/tmp/runs.log
: > $LOG

r () {  # arch policy stream seed epochs [extra]
  echo "=== $1 $2 $3 s$4 ($5 ep) $(date +%H:%M:%S) ===" >> $LOG
  PYTHONIOENCODING=utf-8 $PY exp/05_train.py --arch "$1" --policy "$2" --stream "$3" \
      --seed "$4" --epochs "$5" $6 >> $LOG 2>&1
}

# 1. HEADLINE: historical architecture under the rigorous protocol
for s in 0 1 2; do r densenet201 grouped full $s 12; done
# 2. LEAKAGE COMPARISON: same model, same everything, only the split policy differs
for s in 0 1 2; do r densenet201 random  full $s 12; done
# 3. SHORTCUT PROBES: what content is the label predictable from?
for s in 0 1 2; do r resnet18 grouped full     $s 15; done
for s in 0 1 2; do r resnet18 grouped brain    $s 15; done
for s in 0 1 2; do r resnet18 grouped nonbrain $s 15; done
for s in 0 1 2; do r resnet18 grouped exterior $s 15; done
# 4. NEGATIVE CONTROL: permuted labels must collapse to chance
r resnet18 grouped full 0 15 --permute_labels
# 5. ARCHITECTURE BASELINE
for s in 0 1 2; do r resnet50 grouped full $s 12; done
# 6. leakage comparison for the probe architecture too
for s in 0 1 2; do r resnet18 random full $s 15; done

echo "ALL_RUNS_DONE $(date +%H:%M:%S)" >> $LOG
