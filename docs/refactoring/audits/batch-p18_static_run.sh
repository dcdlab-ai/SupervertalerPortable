#!/bin/bash
# BATCH P1.8 static protection suite (chain, pyflakes, py_compile, headless,
# grep-gate incl. the new QSettings two-arg ban). Copy of batch-p17_static_run.sh
# with S pointed at batch-p18. Run as: bash batch-p18_static_run.sh <tag>
cd /e/Dev/SupervertalerPortable
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p18/static
PY=E:/Dev/python-embed/python.exe
TAG=${1:-p18}
mkdir -p "$S"

echo "=== chain $TAG ==="
$PY -u docs/refactoring/audits/batch8-15_startup_chain_resolve.py Supervertaler.py $TAG 2>&1 | tail -3

echo "=== pyflakes $TAG ==="
$PY -u docs/refactoring/audits/batch8-15_run_pyflakes.py $TAG 2>&1 | tail -8

echo "=== py_compile ==="
$PY -u docs/refactoring/audits/batch8-15_pycompile_all.py 2>&1 | tail -4

echo "=== headless ==="
$PY -u docs/refactoring/audits/batch8-15_headless_imports.py 2>&1 | tail -4

echo "=== grep gate ==="
$PY -u docs/refactoring/audits/batch9-3_grep_gate.py 2>&1

echo "=== DONE static ==="
