#!/bin/bash
# Full offscreen suite for BATCH Q-A (Q.1/Q.2/Q.6 — QuickTrans MT-profile
# fields, link-only gate, cooperative close).
# Copy of batch-m2_run_full.sh with S pointed at refactoring/batch-qa and
# TAG=qa; shared probe scripts/fixtures unchanged, logs compare 1:1 against
# the batch-m2 baselines.
cd /e/Dev/SupervertalerPortable
S=/d/Temp/SupervertalerPortable/refactoring/batch-qa
S94=/d/Temp/SupervertalerPortable/refactoring/batch9-4
P=/d/Temp/SupervertalerPortable/refactoring/b8-15/probes
PY=E:/Dev/python-embed/python.exe
TAG=${1:-qa}
kill_leftovers() {
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.ExecutablePath -like 'E:\Dev\python-embed\*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | Where-Object { \$_.CommandLine -like '*SupervertalerPortable*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
  sleep 2
}
run() { timeout 480 "$@"; }
echo "=== fallback probe (9.4h) ==="
rm -rf $S/iso-$TAG-fb
run $PY -u $S94/probe_94h_fallback.py . $S/iso-$TAG-fb > $S/probe_${TAG}_fb.log 2>&1
kill_leftovers
echo "=== profiles probe (9.4f) ==="
rm -rf $S/iso-$TAG
run $PY -u $S94/probe_94f_profiles.py . $S/iso-$TAG > $S/probe_${TAG}_profiles.log 2>&1
kill_leftovers
echo "=== qtchat probe ==="
rm -rf $S/iso-$TAG-qt
run $PY -u $S94/probe_94d_qtchat.py . $S/iso-$TAG-qt > $S/probe_${TAG}_qtchat.log 2>&1
kill_leftovers
echo "=== statusbar prof ==="
rm -rf $S/iso-$TAG-prof
run $PY -u $S94/probe_94c_statusbar.py . $S/iso-$TAG-prof prof > $S/probe_${TAG}_statusbar_prof.log 2>&1
kill_leftovers
echo "=== e2e ==="
rm -rf $S/iso-$TAG-e2e
run $PY -u docs/refactoring/audits/batch9-3_probe_llm_e2e.py . $S/iso-$TAG-e2e $TAG > $S/e2e_after_$TAG.log 2>&1
kill_leftovers
echo "=== S-clean ==="
run $PY -u docs/refactoring/audits/batch8-15_probe_window.py "$P/iso-clean" ${TAG}_clean clean > $S/probe_after_${TAG}_clean.log 2>&1
kill_leftovers
echo "=== S-upgrade ==="
run $PY -u docs/refactoring/audits/batch8-15_probe_window.py "$P/iso-upgrade" ${TAG}_upgr upgrade > $S/probe_after_${TAG}_upgrade.log 2>&1
kill_leftovers
echo "=== regress ==="
run $PY -u docs/refactoring/audits/batch8-15_regress_common.py . $S/stage-regress $TAG > $S/regress_after_$TAG.log 2>&1
kill_leftovers
echo "=== smoke ==="
run $PY -u docs/refactoring/audits/batch8-13_code_tools_smoke.py . $S/stage-smoke $TAG > $S/smoke_after_$TAG.log 2>&1
kill_leftovers
echo "=== termbase ==="
run $PY -u docs/refactoring/audits/batch8-15_regress_termbase.py . $S/stage-tb $TAG > $S/tb_after_$TAG.log 2>&1
kill_leftovers
echo "=== about ==="
rm -rf $S/iso-about-$TAG
run $PY -u docs/refactoring/audits/batch8-15_probe_about.py . $S/iso-about-$TAG $TAG > $S/about_after_$TAG.log 2>&1
kill_leftovers
echo "=== save probe ==="
rm -rf $S/iso-$TAG-save
run $PY -u $S94/seed_94a_save.py $S/iso-$TAG-save modern > $S/seed_${TAG}_save.log 2>&1
run $PY -u $S94/probe_94a_save.py . $S/iso-$TAG-save save > $S/probe_${TAG}_save.log 2>&1
kill_leftovers
echo "=== save probe legacy (pre-9.5 file) ==="
rm -rf $S/iso-$TAG-save-legacy
run $PY -u $S94/seed_94a_save.py $S/iso-$TAG-save-legacy legacy > $S/seed_${TAG}_save_legacy.log 2>&1
run $PY -u $S94/probe_94a_save.py . $S/iso-$TAG-save-legacy legacy > $S/probe_${TAG}_save_legacy.log 2>&1
kill_leftovers
echo "=== r9 a ==="
rm -rf $S/iso-$TAG-a
run $PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-$TAG-a a > $S/seed_${TAG}_r9_a.log 2>&1
run $PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-$TAG-a a > $S/probe_${TAG}_r9_a.log 2>&1
kill_leftovers
echo "=== r9 ctrl ==="
rm -rf $S/iso-$TAG-ctrl
run $PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-$TAG-ctrl ctrl > $S/seed_${TAG}_r9_ctrl.log 2>&1
run $PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-$TAG-ctrl ctrl > $S/probe_${TAG}_r9_ctrl.log 2>&1
kill_leftovers
echo "=== r9 rm ==="
rm -rf $S/iso-$TAG-rm
run $PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-$TAG-rm rm > $S/seed_${TAG}_r9_rm.log 2>&1
run $PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-$TAG-rm rm > $S/probe_${TAG}_r9_rm.log 2>&1
kill_leftovers
echo "=== DONE ==="
