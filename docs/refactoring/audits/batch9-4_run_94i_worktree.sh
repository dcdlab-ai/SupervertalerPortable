#!/bin/bash
# Batch 9.4i offscreen suite against a worktree (per-commit validation of 9.4i-1)
# usage: run_94i_worktree.sh <worktree-path> <tag>
cd /e/Dev/SupervertalerPortable
P=/e/Dev/Work_temp/SupervertalerPortable/refactoring/b8-15/probes
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch9-4
PY=E:/Dev/python-embed/python.exe
T=$1
TAG=$2
kill_leftovers() {
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.ExecutablePath -like 'E:\\Dev\\python-embed\\*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | Where-Object { \$_.CommandLine -like '*SupervertalerPortable*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
  sleep 2
}

echo "=== fallback probe (9.4h) ==="
rm -rf $S/iso-$TAG-fb
$PY -u $S/probe_94h_fallback.py "$T" $S/iso-$TAG-fb > $S/probe_${TAG}_fb.log 2>&1
kill_leftovers

echo "=== profiles probe (9.4f) ==="
rm -rf $S/iso-$TAG
$PY -u $S/probe_94f_profiles.py "$T" $S/iso-$TAG > $S/probe_${TAG}_profiles.log 2>&1
kill_leftovers

echo "=== qtchat probe ==="
rm -rf $S/iso-$TAG-qt
$PY -u $S/probe_94d_qtchat.py "$T" $S/iso-$TAG-qt > $S/probe_${TAG}_qtchat.log 2>&1
kill_leftovers

echo "=== statusbar prof ==="
rm -rf $S/iso-$TAG-prof
$PY -u $S/probe_94c_statusbar.py "$T" $S/iso-$TAG-prof prof > $S/probe_${TAG}_statusbar_prof.log 2>&1
kill_leftovers

echo "=== e2e ==="
rm -rf $S/iso-$TAG-e2e
$PY -u "$T/docs/refactoring/audits/batch9-3_probe_llm_e2e.py" "$T" $S/iso-$TAG-e2e $TAG > $S/e2e_after_$TAG.log 2>&1
kill_leftovers

echo "=== S-clean ==="
$PY -u "$T/docs/refactoring/audits/batch8-15_probe_window.py" "$P/iso-clean" ${TAG}_clean clean > $S/probe_after_${TAG}_clean.log 2>&1
kill_leftovers

echo "=== S-upgrade ==="
$PY -u "$T/docs/refactoring/audits/batch8-15_probe_window.py" "$P/iso-upgrade" ${TAG}_upgr upgrade > $S/probe_after_${TAG}_upgrade.log 2>&1
kill_leftovers

echo "=== regress ==="
$PY -u "$T/docs/refactoring/audits/batch8-15_regress_common.py" "$T" $S/stage-regress-$TAG $TAG > $S/regress_after_$TAG.log 2>&1
kill_leftovers

echo "=== smoke ==="
$PY -u "$T/docs/refactoring/audits/batch8-15_tools_smoke.py" "$T" $S/stage-smoke-$TAG $TAG > $S/smoke_after_$TAG.log 2>&1
kill_leftovers

echo "=== termbase ==="
$PY -u "$T/docs/refactoring/audits/batch8-15_regress_termbase.py" "$T" $S/stage-tb-$TAG $TAG > $S/tb_after_$TAG.log 2>&1
kill_leftovers

echo "=== about ==="
$PY -u "$T/docs/refactoring/audits/batch8-15_probe_about.py" "$T" $S/iso-about-$TAG $TAG > $S/about_after_$TAG.log 2>&1
kill_leftovers

echo "=== save probe ==="
rm -rf $S/iso-$TAG-save
$PY -u $S/seed_94a_save.py $S/iso-$TAG-save > $S/seed_${TAG}_save.log 2>&1
$PY -u $S/probe_94a_save.py "$T" $S/iso-$TAG-save save > $S/probe_${TAG}_save.log 2>&1
kill_leftovers

echo "=== r9 a ==="
rm -rf $S/iso-$TAG-a
$PY -u "$T/docs/refactoring/audits/r9_seed_profiles.py" $S/iso-$TAG-a a > $S/seed_${TAG}_r9_a.log 2>&1
$PY -u "$T/docs/refactoring/audits/r9_probe_profiles.py" "$T" $S/iso-$TAG-a a > $S/probe_${TAG}_r9_a.log 2>&1
kill_leftovers

echo "=== r9 ctrl ==="
rm -rf $S/iso-$TAG-ctrl
$PY -u "$T/docs/refactoring/audits/r9_seed_profiles.py" $S/iso-$TAG-ctrl ctrl > $S/seed_${TAG}_r9_ctrl.log 2>&1
$PY -u "$T/docs/refactoring/audits/r9_probe_profiles.py" "$T" $S/iso-$TAG-ctrl ctrl > $S/probe_${TAG}_r9_ctrl.log 2>&1
kill_leftovers

echo "=== r9 rm ==="
rm -rf $S/iso-$TAG-rm
$PY -u "$T/docs/refactoring/audits/r9_seed_profiles.py" $S/iso-$TAG-rm rm > $S/seed_${TAG}_r9_rm.log 2>&1
$PY -u "$T/docs/refactoring/audits/r9_probe_profiles.py" "$T" $S/iso-$TAG-rm rm > $S/probe_${TAG}_r9_rm.log 2>&1
kill_leftovers

echo "=== DONE ==="
