#!/bin/bash
# Batch 9.4b offscreen protection suite (repo tree = E:\Dev\SupervertalerPortable)
cd /e/Dev/SupervertalerPortable
P=/e/Dev/Work_temp/SupervertalerPortable/refactoring/b8-15/probes
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch9-4
PY=E:/Dev/python-embed/python.exe
# Kill ONLY processes launched from the bundled runtime (E:\Dev\python-embed) and
# Okapi java from this project. NEVER kill by image name: unrelated pythons
# (e.g. i:\AI\StrataPortable\python\python.exe) must stay untouched.
kill_leftovers() {
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.ExecutablePath -like 'E:\\Dev\\python-embed\\*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | Where-Object { \$_.CommandLine -like '*SupervertalerPortable*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
  sleep 2
}

echo "=== headless ==="
$PY -u docs/refactoring/audits/batch8-15_headless_imports.py > $S/headless_after_94b.txt 2>&1
kill_leftovers

echo "=== S-clean ==="
$PY -u docs/refactoring/audits/batch8-15_probe_window.py "$P/iso-clean" b94b_clean clean > $S/probe_after_94b_clean.log 2>&1
kill_leftovers

echo "=== S-upgrade ==="
$PY -u docs/refactoring/audits/batch8-15_probe_window.py "$P/iso-upgrade" b94b_upgr upgrade > $S/probe_after_94b_upgrade.log 2>&1
kill_leftovers

echo "=== regress ==="
$PY -u docs/refactoring/audits/batch8-15_regress_common.py . $S/stage-regress b94b > $S/regress_after_94b.log 2>&1
kill_leftovers

echo "=== smoke ==="
$PY -u docs/refactoring/audits/batch8-15_tools_smoke.py . $S/stage-smoke b94b > $S/smoke_after_94b.log 2>&1
kill_leftovers

echo "=== termbase ==="
$PY -u docs/refactoring/audits/batch8-15_regress_termbase.py . $S/stage-tb b94b > $S/tb_after_94b.log 2>&1
kill_leftovers

echo "=== about ==="
$PY -u docs/refactoring/audits/batch8-15_probe_about.py . $S/iso-about b94b > $S/about_after_94b.log 2>&1
kill_leftovers

echo "=== save probe ==="
rm -rf $S/iso-94b-save
$PY -u $S/seed_94a_save.py $S/iso-94b-save > $S/seed_94b_save.log 2>&1
$PY -u $S/probe_94a_save.py . $S/iso-94b-save save > $S/probe_94b_save.log 2>&1
kill_leftovers

echo "=== r9 a ==="
rm -rf $S/iso-94b-a
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94b-a a > $S/probe_94b_r9_a.log 2>&1
kill_leftovers

echo "=== r9 ctrl ==="
rm -rf $S/iso-94b-ctrl
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94b-ctrl ctrl > $S/probe_94b_r9_ctrl.log 2>&1
kill_leftovers

echo "=== r9 rm ==="
rm -rf $S/iso-94b-rm
$PY -u docs/refactoring/audits/r9_probe_profiles.py . $S/iso-94b-rm rm > $S/probe_94b_r9_rm.log 2>&1
kill_leftovers

echo "=== DONE ==="
