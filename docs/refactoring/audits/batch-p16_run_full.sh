#!/bin/bash
# Full offscreen suite for BATCH P1.6 (quicktrans.ini, QSettings insurance,
# AA_DontUseNativeDialogs). Copy of batch-p1c_run_full.sh with:
#   - probe copies: the batch-p1b_* copies REUSED unchanged (the seam contract
#     did not change in P1.6);
#   - the four P1.6-specific probes run first: popup geometry (quicktrans.ini),
#     QSettings insurance unit, dialogs smoke, winreg tripwire (M3);
#   - M4 bracket: reg query (READ-ONLY observation) of HKCU\Software\Supervertaler
#     and HKCU\...\Run taken before the full cycle and after it, diff must be
#     empty;
#   - after the suite: the qsettings/ directory must exist in NO isolated
#     profile (a bare app start creates no QSettings files).
#   - S pointed at batch-p16, kill script staged under batch-p16/.
cd /e/Dev/SupervertalerPortable
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p16/regress
P=/e/Dev/Work_temp/SupervertalerPortable/refactoring/b8-15/probes
A=/e/Dev/SupervertalerPortable/docs/refactoring/audits
FIX=/e/Dev/SupervertalerPortable/docs/refactoring/audits/fixtures/regress_inputs
PY=E:/Dev/python-embed/python.exe
TAG=${1:-p16}
STAGE=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p16
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

# --- M4 BEFORE: registry observation (READ, method M4; never a write) ---
{ echo "=== M4 reg BEFORE ==="
  reg query "HKCU\\Software\\Supervertaler" /s
  reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v Supervertaler
} > "$STAGE/m4_before.txt" 2>&1

echo "=== P1.6 probe 1: popup geometry -> quicktrans.ini ==="
rm -rf "$STAGE/iso-popup"
run $PY -u $A/batch-p16_probe_popup.py "E:\\Dev\\Work_temp\\SupervertalerPortable\\refactoring\\batch-p16\\iso-popup" > "$STAGE/probe_${TAG}_popup.log" 2>&1
echo "popup exit=$?"
kill_leftovers
echo "=== P1.6 probe 2: QSettings insurance unit ==="
rm -rf "$STAGE/iso-qs"
run $PY -u $A/batch-p16_unit_qsettings.py "E:\\Dev\\Work_temp\\SupervertalerPortable\\refactoring\\batch-p16\\iso-qs" > "$STAGE/probe_${TAG}_qs.log" 2>&1
echo "qs exit=$?"
kill_leftovers
echo "=== P1.6 probe 3: dialogs smoke (AA_DontUseNativeDialogs) ==="
rm -rf "$STAGE/iso-fd"
run $PY -u $A/batch-p16_probe_dialogs.py "E:\\Dev\\Work_temp\\SupervertalerPortable\\refactoring\\batch-p16\\iso-fd" > "$STAGE/probe_${TAG}_fd.log" 2>&1
echo "fd exit=$?"
kill_leftovers
echo "=== P1.6 probe 4: winreg tripwire M3 (full app + popup) ==="
rm -rf "$STAGE/iso-wr"
run $PY -u $A/batch-p16_probe_winreg.py . "$STAGE/iso-wr" ${TAG}_wr > "$STAGE/probe_${TAG}_winreg.log" 2>&1
echo "winreg exit=$?"
kill_leftovers

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

# --- M4 AFTER: registry observation + diff (must be empty) ---
{ echo "=== M4 reg AFTER ==="
  reg query "HKCU\\Software\\Supervertaler" /s
  reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v Supervertaler
} > "$STAGE/m4_after.txt" 2>&1
echo "=== M4 diff (empty = registry untouched by the full cycle) ==="
diff "$STAGE/m4_before.txt" "$STAGE/m4_after.txt" > "$STAGE/m4_diff.txt"
echo "m4 diff exit=$? (1 = differences, see m4_diff.txt)"

# --- qsettings negative: a bare app start creates no QSettings files ---
echo "=== qsettings negative (no qsettings/ dir in any isolated profile) ==="
find "$S" "$STAGE" -maxdepth 4 -type d -name qsettings \
     -not -path "*/iso-qs/*" -not -path "*/iso-qs" 2>/dev/null

echo "=== DONE ==="
