#!/bin/bash
# Full offscreen suite for BATCH P1-B (data root = build root, pointer removal).
# Copy of batch-p1a_run_full.sh with:
#   - probes point at the batch-p1b copies (made by batch-p1b_make_probe_copies.py:
#     seam SUPERVERTALER_DATA_ROOT=<iso>, config.json pointer seeding removed);
#   - regress runs batch-p1b_regress_common.py (same two edits);
#   - SELF-SEEDING stage: mkdir -p for every stage dir the harnesses use,
#     fixtures seeded from the repository (docs/refactoring/audits/fixtures/
#     regress_inputs/, sha256 in the README next to them), stage-regress/iso/
#     created when absent. A clean stage dir runs without manual seeding.
cd /e/Dev/SupervertalerPortable
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p1b/regress
P=/e/Dev/Work_temp/SupervertalerPortable/refactoring/b8-15/probes
A=/e/Dev/SupervertalerPortable/docs/refactoring/audits
FIX=/e/Dev/SupervertalerPortable/docs/refactoring/audits/fixtures/regress_inputs
PY=E:/Dev/python-embed/python.exe
TAG=${1:-p1b}
# --- self-seeding stage (STEP 0): no manual prep required ---
mkdir -p "$S" "$S/stage-regress/inputs" "$S/stage-regress/iso" \
         "$S/stage-smoke" "$S/stage-tb" \
         /e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p1b
cp -p "$FIX/test.txt" "$FIX/test.md" "$FIX/test.docx" "$S/stage-regress/inputs/"
kill_leftovers() {
  powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1b\kill_leftovers.ps1' >/dev/null 2>&1
  sleep 2
}
# kill_leftovers.ps1 lives in the repo; stage copy keeps the historical path contract
cp -p "$A/batch-p1b_kill_leftovers.ps1" \
   /e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p1b/kill_leftovers.ps1
run() { timeout 480 "$@"; }
echo "=== fallback probe (9.4h) ==="
rm -rf $S/iso-$TAG-fb
run $PY -u $A/batch-p1b_batch9-4_probe_94h_fallback.py . $S/iso-$TAG-fb > $S/probe_${TAG}_fb.log 2>&1
kill_leftovers
echo "=== profiles probe (9.4f) ==="
rm -rf $S/iso-$TAG
run $PY -u $A/batch-p1b_batch9-4_probe_94f_profiles.py . $S/iso-$TAG > $S/probe_${TAG}_profiles.log 2>&1
kill_leftovers
echo "=== qtchat probe ==="
rm -rf $S/iso-$TAG-qt
run $PY -u $A/batch-p1b_batch9-4_probe_94d_qtchat.py . $S/iso-$TAG-qt > $S/probe_${TAG}_qtchat.log 2>&1
kill_leftovers
echo "=== statusbar prof ==="
rm -rf $S/iso-$TAG-prof
run $PY -u $A/batch-p1b_batch9-4_probe_94c_statusbar.py . $S/iso-$TAG-prof prof > $S/probe_${TAG}_statusbar_prof.log 2>&1
kill_leftovers
echo "=== e2e ==="
rm -rf $S/iso-$TAG-e2e
run $PY -u $A/batch-p1b_batch9-3_probe_llm_e2e.py . $S/iso-$TAG-e2e $TAG > $S/e2e_after_$TAG.log 2>&1
kill_leftovers
echo "=== S-clean ==="
run $PY -u $A/batch-p1b_batch8-15_probe_window.py "$P/iso-clean" ${TAG}_clean clean > $S/probe_after_${TAG}_clean.log 2>&1
kill_leftovers
echo "=== S-upgrade ==="
run $PY -u $A/batch-p1b_batch8-15_probe_window.py "$P/iso-upgrade" ${TAG}_upgr upgrade > $S/probe_after_${TAG}_upgrade.log 2>&1
kill_leftovers
echo "=== regress ==="
run $PY -u $A/batch-p1b_batch8-15_regress_common.py . $S/stage-regress $TAG > $S/regress_after_$TAG.log 2>&1
kill_leftovers
echo "=== smoke ==="
run $PY -u $A/batch-p1b_batch8-13_code_tools_smoke.py . $S/stage-smoke $TAG > $S/smoke_after_$TAG.log 2>&1
kill_leftovers
echo "=== termbase ==="
run $PY -u $A/batch-p1b_batch8-15_regress_termbase.py . $S/stage-tb $TAG > $S/tb_after_$TAG.log 2>&1
kill_leftovers
echo "=== about ==="
rm -rf $S/iso-about-$TAG
run $PY -u $A/batch-p1b_batch8-15_probe_about.py . $S/iso-about-$TAG $TAG > $S/about_after_$TAG.log 2>&1
kill_leftovers
echo "=== save probe ==="
rm -rf $S/iso-$TAG-save
run $PY -u $A/batch9-4_seed_94a_save.py $S/iso-$TAG-save modern > $S/seed_${TAG}_save.log 2>&1
run $PY -u $A/batch-p1b_batch9-4_probe_94a_save.py . $S/iso-$TAG-save save > $S/probe_${TAG}_save.log 2>&1
kill_leftovers
echo "=== save probe legacy (pre-9.5 file) ==="
rm -rf $S/iso-$TAG-save-legacy
run $PY -u $A/batch9-4_seed_94a_save.py $S/iso-$TAG-save-legacy legacy > $S/seed_${TAG}_save_legacy.log 2>&1
run $PY -u $A/batch-p1b_batch9-4_probe_94a_save.py . $S/iso-$TAG-save-legacy legacy > $S/probe_${TAG}_save_legacy.log 2>&1
kill_leftovers
echo "=== r9 a ==="
rm -rf $S/iso-$TAG-a
run $PY -u $A/r9_seed_profiles.py $S/iso-$TAG-a a > $S/seed_${TAG}_r9_a.log 2>&1
run $PY -u $A/batch-p1b_r9_probe_profiles.py . $S/iso-$TAG-a a > $S/probe_${TAG}_r9_a.log 2>&1
kill_leftovers
echo "=== r9 ctrl ==="
rm -rf $S/iso-$TAG-ctrl
run $PY -u $A/r9_seed_profiles.py $S/iso-$TAG-ctrl ctrl > $S/seed_${TAG}_r9_ctrl.log 2>&1
run $PY -u $A/batch-p1b_r9_probe_profiles.py . $S/iso-$TAG-ctrl ctrl > $S/probe_${TAG}_r9_ctrl.log 2>&1
kill_leftovers
echo "=== r9 rm ==="
rm -rf $S/iso-$TAG-rm
run $PY -u $A/r9_seed_profiles.py $S/iso-$TAG-rm rm > $S/seed_${TAG}_r9_rm.log 2>&1
run $PY -u $A/batch-p1b_r9_probe_profiles.py . $S/iso-$TAG-rm rm > $S/probe_${TAG}_r9_rm.log 2>&1
kill_leftovers
echo "=== DONE ==="
