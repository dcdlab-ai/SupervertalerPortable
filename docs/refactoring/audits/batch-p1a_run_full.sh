#!/bin/bash
# Full offscreen suite for BATCH P1-A (usage statistics / autostart / update
# check removal). Copy of batch-qc_run_full.sh: the 16 stages are identical,
# only probe paths change to the batch-p1a copies (byte-identical to the
# originals minus the 2-line usage_statistics opt-in-dialog stub, obsolete
# once the stats code is removed). seeds/regress_common unchanged.
cd /e/Dev/SupervertalerPortable
S=/e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-p1a/regress
P=/e/Dev/Work_temp/SupervertalerPortable/refactoring/b8-15/probes
A=/e/Dev/SupervertalerPortable/docs/refactoring/audits
PY=E:/Dev/python-embed/python.exe
TAG=${1:-p1a}
# Fresh stage: the harnesses create their own iso/ dirs, but all log redirects
# need $S, and the regress harness needs pre-seeded inputs/ (test.txt/md/docx)
# (same seeding as batch-qcfin; source = batch-g32e/stage-regress/inputs,
# hashes c9c80973/c079e760/39abb383 — the b8-15 originals were lost 2026-10-22).
mkdir -p "$S/stage-regress/inputs"
cp -p /e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-g32e/stage-regress/inputs/test.txt \
      /e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-g32e/stage-regress/inputs/test.md \
      /e/Dev/Work_temp/SupervertalerPortable/refactoring/batch-g32e/stage-regress/inputs/test.docx \
      "$S/stage-regress/inputs/" 2>/dev/null
kill_leftovers() {
  powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1a\kill_leftovers.ps1' >/dev/null 2>&1
  sleep 2
}
run() { timeout 480 "$@"; }
echo "=== fallback probe (9.4h) ==="
rm -rf $S/iso-$TAG-fb
run $PY -u $A/batch-p1a_batch9-4_probe_94h_fallback.py . $S/iso-$TAG-fb > $S/probe_${TAG}_fb.log 2>&1
kill_leftovers
echo "=== profiles probe (9.4f) ==="
rm -rf $S/iso-$TAG
run $PY -u $A/batch-p1a_batch9-4_probe_94f_profiles.py . $S/iso-$TAG > $S/probe_${TAG}_profiles.log 2>&1
kill_leftovers
echo "=== qtchat probe ==="
rm -rf $S/iso-$TAG-qt
run $PY -u $A/batch-p1a_batch9-4_probe_94d_qtchat.py . $S/iso-$TAG-qt > $S/probe_${TAG}_qtchat.log 2>&1
kill_leftovers
echo "=== statusbar prof ==="
rm -rf $S/iso-$TAG-prof
run $PY -u $A/batch-p1a_batch9-4_probe_94c_statusbar.py . $S/iso-$TAG-prof prof > $S/probe_${TAG}_statusbar_prof.log 2>&1
kill_leftovers
echo "=== e2e ==="
rm -rf $S/iso-$TAG-e2e
run $PY -u $A/batch-p1a_batch9-3_probe_llm_e2e.py . $S/iso-$TAG-e2e $TAG > $S/e2e_after_$TAG.log 2>&1
kill_leftovers
echo "=== S-clean ==="
run $PY -u $A/batch-p1a_batch8-15_probe_window.py "$P/iso-clean" ${TAG}_clean clean > $S/probe_after_${TAG}_clean.log 2>&1
kill_leftovers
echo "=== S-upgrade ==="
run $PY -u $A/batch-p1a_batch8-15_probe_window.py "$P/iso-upgrade" ${TAG}_upgr upgrade > $S/probe_after_${TAG}_upgrade.log 2>&1
kill_leftovers
echo "=== regress ==="
run $PY -u $A/batch8-15_regress_common.py . $S/stage-regress $TAG > $S/regress_after_$TAG.log 2>&1
kill_leftovers
echo "=== smoke ==="
run $PY -u $A/batch-p1a_batch8-13_code_tools_smoke.py . $S/stage-smoke $TAG > $S/smoke_after_$TAG.log 2>&1
kill_leftovers
echo "=== termbase ==="
run $PY -u $A/batch-p1a_batch8-15_regress_termbase.py . $S/stage-tb $TAG > $S/tb_after_$TAG.log 2>&1
kill_leftovers
echo "=== about ==="
rm -rf $S/iso-about-$TAG
run $PY -u $A/batch-p1a_batch8-15_probe_about.py . $S/iso-about-$TAG $TAG > $S/about_after_$TAG.log 2>&1
kill_leftovers
echo "=== save probe ==="
rm -rf $S/iso-$TAG-save
run $PY -u $A/batch9-4_seed_94a_save.py $S/iso-$TAG-save modern > $S/seed_${TAG}_save.log 2>&1
run $PY -u $A/batch-p1a_batch9-4_probe_94a_save.py . $S/iso-$TAG-save save > $S/probe_${TAG}_save.log 2>&1
kill_leftovers
echo "=== save probe legacy (pre-9.5 file) ==="
rm -rf $S/iso-$TAG-save-legacy
run $PY -u $A/batch9-4_seed_94a_save.py $S/iso-$TAG-save-legacy legacy > $S/seed_${TAG}_save_legacy.log 2>&1
run $PY -u $A/batch-p1a_batch9-4_probe_94a_save.py . $S/iso-$TAG-save-legacy legacy > $S/probe_${TAG}_save_legacy.log 2>&1
kill_leftovers
echo "=== r9 a ==="
rm -rf $S/iso-$TAG-a
run $PY -u $A/r9_seed_profiles.py $S/iso-$TAG-a a > $S/seed_${TAG}_r9_a.log 2>&1
run $PY -u $A/batch-p1a_r9_probe_profiles.py . $S/iso-$TAG-a a > $S/probe_${TAG}_r9_a.log 2>&1
kill_leftovers
echo "=== r9 ctrl ==="
rm -rf $S/iso-$TAG-ctrl
run $PY -u $A/r9_seed_profiles.py $S/iso-$TAG-ctrl ctrl > $S/seed_${TAG}_r9_ctrl.log 2>&1
run $PY -u $A/batch-p1a_r9_probe_profiles.py . $S/iso-$TAG-ctrl ctrl > $S/probe_${TAG}_r9_ctrl.log 2>&1
kill_leftovers
echo "=== r9 rm ==="
rm -rf $S/iso-$TAG-rm
run $PY -u $A/r9_seed_profiles.py $S/iso-$TAG-rm rm > $S/seed_${TAG}_r9_rm.log 2>&1
run $PY -u $A/batch-p1a_r9_probe_profiles.py . $S/iso-$TAG-rm rm > $S/probe_${TAG}_r9_rm.log 2>&1
kill_leftovers
echo "=== DONE ==="
