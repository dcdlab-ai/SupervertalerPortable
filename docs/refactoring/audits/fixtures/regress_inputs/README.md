# Regression inputs (regress harness fixtures)

Input files for `batch8-15_regress_common.py` (stages: `regress`) and its
per-batch copies. The 16-stage suite runners copy these three files into
`<stage>/stage-regress/inputs/` before the run — the stage dir no longer
depends on leftover artifacts from earlier batches.

Provenance: `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-g32e\stage-regress\inputs\`
(the b8-15 originals were lost 2026-10-22; the g32e copies are the canonical
ones since batch g32e — see `batch-p1a_run_full.sh` header comment).

sha256 (full):

| file      | sha256                                                            |
|-----------|-------------------------------------------------------------------|
| test.txt  | `c9c80973de2716f52884ab265561e11d2a081c63ea840a53caa46a14590acea5` |
| test.md   | `c079e760406e796c6ce45eb58e9ff82c1d9967b3f6438284c0c1543c3b3b38b1` |
| test.docx | `39abb383e13bdc2bc988646a151fc97b62887b18d62f88bad4287d274097c11a` |

Regression acceptance hashes (outputs of the harness, unchanged by P1-B):
`5a12501f934a589c` (export_simple_txt), `44828d90090f046d` (export_docx),
`c413d56372e69dd9` (export_tmx).

Do not edit these files: changing a byte changes the import segment counts
and breaks the regress hash comparison against all previous batches.
