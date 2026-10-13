#!/bin/bash
# Batch 9.4c offscreen protection suite
cd /e/Dev/SupervertalerPortable
P=/d/Temp/SupervertalerPortable/refactoring/b8-15/probes
S=/d/Temp/SupervertalerPortable/refactoring/batch9-4
PY=E:/Dev/python-embed/python.exe
# Kill ONLY bundled-runtime pythons and project java; NEVER by image name
# (i:\AI\StrataPortable\python\python.exe must stay untouched).
kill_leftovers() {
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.ExecutablePath -like 'E:\\Dev\\python-embed\\*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | Where-Object { \$_.CommandLine -like '*SupervertalerPortable*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
  sleep 2
}

echo "=== statusbar prof ==="
rm -rf $S/iso-94c-prof
$PY -u $S/probe_94c_statusbar.py . $S/iso-94c-prof prof > $S/probe_94c_statusbar_prof.log 2>&1
kill_leftovers
echo "=== statusbar none ==="
rm -rf $S/iso-94c-none
$PY -u $S/probe_94c_statusbar.py . $S/iso-94c-none none > $S/probe_94c_statusbar_none.log 2>&1
kill_leftovers
echo "=== statusbar legacy ==="
rm -rf $S/iso-94c-legacy
$PY -u $S/probe_94c_statusbar.py . $S/iso-94c-legacy legacy > $S/probe_94c_statusbar_legacy.log 2>&1
kill_leftovers

echo "=== S-clean ==="
$PY -u docs/refactoring/audits/batch8-15_probe_window.py "$P/iso-clean" b94c_clean clean > $S/probe_after_94c_clean.log 2>&1
kill_leftovers

echo "=== S-upgrade ==="
$PY -u docs/refactoring/audits/batch8-15_probe_window.py "$P/iso-upgrade" b94c_upgr upgrade > $S/probe_after_94c_upgrade.log 2>&1
kill_leftovers

echo "=== regress ==="
$PY -u docs/refactoring/audits/batch8-15_regress_common.py . $S/stage-regress b94c > $S/regress_after_94c.log 2>&1
kill_leftovers

echo "=== smoke ==="
$PY -u docs/refactoring/audits/batch8-15_tools_smoke.py . $S/stage-smoke b94c > $S/smoke_after_94c.log 2>&1
kill_leftovers

echo "=== termbase ==="
$PY -u docs/refactoring/audits/batch8-15_regress_termbase.py . $S/stage-tb b94c > $S/tb_after_94c.log 2>&1
kill_leftovers

echo "=== about ==="
$PY -u docs/refactoring/audits/batch8-15_probe_about.py . $S/iso-about b94c > $S/about_after_94c.log 2>&1
kill_leftovers

echo "=== save probe ==="
rm -rf $S/iso-94c-save
$PY -u $S/seed_94a_save.py $S/iso-94c-save > $S/seed_94c_save.log 2>&1
$PY -u $S/probe_94a_save.py . $S/iso-94c-save save > $S/probe_94c_save.log 2>&1
kill_leftovers

echo "=== r9 a ==="
rm -rf $S/iso-94c-a
$PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-94c-a a > $S/seed_94c_r9_a.log 2>&1
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94c-a a > $S/probe_94c_r9_a.log 2>&1
kill_leftovers

echo "=== r9 ctrl ==="
rm -rf $S/iso-94c-ctrl
$PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-94c-ctrl ctrl > $S/seed_94c_r9_ctrl.log 2>&1
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94c-ctrl ctrl > $S/probe_94c_r9_ctrl.log 2>&1
kill_leftovers

echo "=== r9 rm ==="
rm -rf $S/iso-94c-rm
$PY -u docs/refactoring/audits/r9_seed_profiles.py $S/iso-94c-rm rm > $S/seed_94c_r9_rm.log 2>&1
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94c-rm rm > $S/probe_94c_r9_rm.log 2>&1
kill_leftovers

echo "=== DONE ==="
