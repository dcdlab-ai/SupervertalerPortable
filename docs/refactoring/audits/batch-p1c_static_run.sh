#!/bin/bash
# BATCH P1-C static protection suite (chain, pyflakes, py_compile, headless,
# grep-gate). Copy of batch-p1a_static_run.sh with S pointed at batch-p1c.
cd /e/Dev/SupervertalerPortable
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p1c/static
PY=E:/Dev/python-embed/python.exe
TAG=${1:-p1c}
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
