#!/bin/bash
# Full offscreen suite for BATCH P1-C (last_directory in build root,
# shortcuts.json via data_root, Okapi sidecar inside the build).
# Copy of batch-p1b_run_full.sh with:
#   - probe copies: the batch-p1b_* copies are REUSED unchanged -- the seam
#     contract (SUPERVERTALER_DATA_ROOT -> <iso>/Supervertaler) did not change
#     in P1-C and the copies contain nothing batch-specific (P1-C report §7);
#   - the four P1-C-specific probes run first: fdh (last_directory state
#     file), shortcuts (widget with CWD != build root), okapi unit (candidate
#     order + mocked download_install), negative (worktree, no seam);
#   - S pointed at batch-p1c, kill script staged under batch-p1c/.
cd /e/Dev/SupervertalerPortable
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p1c/regress
P=/e/Dev/Work_temp/SupervertalerPortable/refactoring/b8-15/probes
A=/e/Dev/SupervertalerPortable/docs/refactoring/audits
FIX=/e/Dev/SupervertalerPortable/docs/refactoring/audits/fixtures/regress_inputs
PY=E:/Dev/python-embed/python.exe
TAG=${1:-p1c}
STAGE=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p1c
# --- self-seeding stage (STEP 0): no manual prep required ---
mkdir -p "$S" "$S/stage-regress/inputs" "$S/stage-regress/iso" \
         "$S/stage-smoke" "$S/stage-tb" "$STAGE"
cp -p "$FIX/test.txt" "$FIX/test.md" "$FIX/test.docx" "$S/stage-regress/inputs/"
kill_leftovers() {
  powershell -NoProfile -ExecutionPolicy Bypass -File "$STAGE/kill_leftovers.ps1" >/dev/null 2>&1
  sleep 2
}
# kill_leftovers.ps1 lives in the repo; stage copy keeps the path contract
cp -p "$A/batch-p1b_kill_leftovers.ps1" "$STAGE/kill_leftovers.ps1"
run() { timeout 480 "$@"; }

echo "=== P1-C probe 1: fdh (last_directory.json in build root) ==="
rm -rf "$STAGE/iso-fdh"
run $PY -u $A/batch-p1c_probe_fdh.py "$STAGE/iso-fdh" > "$STAGE/probe_${TAG}_fdh.log" 2>&1
echo "fdh exit=$?"
kill_leftovers
echo "=== P1-C probe 2: shortcuts widget (CWD != build root) ==="
rm -rf "$STAGE/iso-sh"
run $PY -u $A/batch-p1c_probe_shortcuts.py "$STAGE/iso-sh" > "$STAGE/probe_${TAG}_sh.log" 2>&1
echo "sh exit=$?"
kill_leftovers
echo "=== P1-C probe 3: okapi unit (candidates + mocked download) ==="
rm -rf "$STAGE/iso-okapi"
run $PY -u $A/batch-p1c_unit_okapi.py "$STAGE/iso-okapi" > "$STAGE/unit_${TAG}_okapi.log" 2>&1
echo "okapi exit=$?"
kill_leftovers
echo "=== P1-C probe 4: negative (worktree, no seam, empty profile) ==="
if [ ! -d "$STAGE/negroot/SupervertalerPortable" ]; then
  git -C /e/Dev/SupervertalerPortable worktree add "$STAGE/negroot/SupervertalerPortable" HEAD >/dev/null 2>&1
fi
mkdir -p "$STAGE/negroot/iso/profile" "$STAGE/negroot/iso/tmp"
rm -rf "$STAGE/negroot/iso/profile" "$STAGE/negroot/iso/Supervertaler" "$STAGE/negroot/last_directory.json"
mkdir -p "$STAGE/negroot/iso/profile" "$STAGE/negroot/iso/tmp"
run $PY -u $A/batch-p1c_probe_negative.py \
    "E:\\Dev\\Work_temp\\SupervertalerPortable\\refactoring\\batch-p1c\\negroot\\SupervertalerPortable" \
    "E:\\Dev\\Work_temp\\SupervertalerPortable\\refactoring\\batch-p1c\\negroot\\iso" \
    > "$STAGE/probe_${TAG}_negative.log" 2>&1
echo "negative exit=$?"

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
