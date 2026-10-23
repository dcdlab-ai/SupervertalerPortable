#!/bin/bash
# Batch 9.4h offscreen protection suite
cd /e/Dev/SupervertalerPortable
P=/e/Dev/Work_temp/SupervertalerPortable/refactoring/b8-15/probes
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch9-4
PY=E:/Dev/python-embed/python.exe
# Kill ONLY bundled-runtime pythons and project java; NEVER by image name
# (i:\AI\StrataPortable\python\python.exe must stay untouched).
kill_leftovers() {
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.ExecutablePath -like 'E:\\Dev\\python-embed\\*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | Where-Object { \$_.CommandLine -like '*SupervertalerPortable*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
  sleep 2
}

echo "=== fallback probe (9.4h) ==="
rm -rf $S/iso-94h-fb
$PY -u $S/probe_94h_fallback.py . $S/iso-94h-fb > $S/probe_94h_fb.log 2>&1
kill_leftovers

echo "=== profiles probe ==="
rm -rf $S/iso-94h
$PY -u $S/probe_94f_profiles.py . $S/iso-94h > $S/probe_94h_profiles.log 2>&1
kill_leftovers

echo "=== qtchat probe ==="
rm -rf $S/iso-94h-qt
$PY -u $S/probe_94d_qtchat.py . $S/iso-94h-qt > $S/probe_94h_qtchat.log 2>&1
kill_leftovers

echo "=== statusbar prof ==="
rm -rf $S/iso-94h-prof
$PY -u $S/probe_94c_statusbar.py . $S/iso-94h-prof prof > $S/probe_94h_statusbar_prof.log 2>&1
kill_leftovers

echo "=== e2e ==="
rm -rf $S/iso-94h-e2e
$PY -u docs/refactoring/audits/batch9-3_probe_llm_e2e.py . $S/iso-94h-e2e b94h > $S/e2e_after_94h.log 2>&1
kill_leftovers

echo "=== S-clean ==="
$PY -u docs/refactoring/audits/batch8-15_probe_window.py "$P/iso-clean" b94h_clean clean > $S/probe_after_94h_clean.log 2>&1
kill_leftovers

echo "=== S-upgrade ==="
$PY -u docs/refactoring/audits/batch8-15_probe_window.py "$P/iso-upgrade" b94h_upgr upgrade > $S/probe_after_94h_upgrade.log 2>&1
kill_leftovers

echo "=== regress ==="
$PY -u docs/refactoring/audits/batch8-15_regress_common.py . $S/stage-regress b94h > $S/regress_after_94h.log 2>&1
kill_leftovers

echo "=== smoke ==="
$PY -u docs/refactoring/audits/batch8-15_tools_smoke.py . $S/stage-smoke b94h > $S/smoke_after_94h.log 2>&1
kill_leftovers

echo "=== termbase ==="
$PY -u docs/refactoring/audits/batch8-15_regress_termbase.py . $S/stage-tb b94h > $S/tb_after_94h.log 2>&1
kill_leftovers

echo "=== about ==="
$PY -u docs/refactoring/audits/batch8-15_probe_about.py . $S/iso-about b94h > $S/about_after_94h.log 2>&1
kill_leftovers

echo "=== save probe ==="
rm -rf $S/iso-94h-save
$PY -u $S/seed_94a_save.py $S/iso-94h-save > $S/seed_94h_save.log 2>&1
$PY -u $S/probe_94a_save.py . $S/iso-94h-save save > $S/probe_94h_save.log 2>&1
kill_leftovers

echo "=== r9 a ==="
rm -rf $S/iso-94h-a
$PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-94h-a a > $S/seed_94h_r9_a.log 2>&1
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94h-a a > $S/probe_94h_r9_a.log 2>&1
kill_leftovers

echo "=== r9 ctrl ==="
rm -rf $S/iso-94h-ctrl
$PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-94h-ctrl ctrl > $S/seed_94h_r9_ctrl.log 2>&1
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94h-ctrl ctrl > $S/probe_94h_r9_ctrl.log 2>&1
kill_leftovers

echo "=== r9 rm ==="
rm -rf $S/iso-94h-rm
$PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-94h-rm rm > $S/seed_94h_r9_rm.log 2>&1
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94h-rm rm > $S/probe_94h_r9_rm.log 2>&1
kill_leftovers

echo "=== DONE ==="
