#!/bin/bash
# Q-C regression: re-run the Q-A/Q-B probes unmodified against the Q-C tree.
cd /e/Dev/SupervertalerPortable
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-qc/regress/qab
PY=E:/Dev/python-embed/python.exe
mkdir -p $S
run() { timeout 480 "$@"; }
for p in batch-qa_q1_probe batch-qa_q2_probe batch-qa_q6_probe batch-qb_q3_probe batch-qb_q4_probe batch-qb_qa_panel_adapted_probe; do
  echo "=== $p ==="
  run $PY -u docs/refactoring/audits/$p.py . $S/${p}_qc.json > $S/${p}_qc.log 2>&1
  echo "exit=$?"
done
echo "=== DONE qab ==="
