# -*- coding: utf-8 -*-
"""Спец-проба E-02: отложенный on_err доходит до show_offline_error БЕЗ NameError
и несёт текст ошибки.

Путь check_for_updates в текущей сборке закрыт ранним return (временное
упрощение), поэтому проба берёт РЕАЛЬНЫЙ исходник метода с диска (AST-границы),
нейтрализует ранний return и финальный start_request("api") -> принудительный
start_python_fallback("probe"), подменяет _fetch_latest_release_info_from_github
на raiser и QProgressBox/QMessageBox на заглушки.

Запуск: python batch8-15_probe_e02.py <tree-root> <iso-dir> <tag>
Ожидание после фикса: captured question text содержит 'probe-net-down-42'.
На baseline (до фикса): NameError внутри on_err (процесс может погибнуть через
qFatal — это и есть доказательство бага; exit code != 0 / пустой capture).
"""
import ast, faulthandler, os, pathlib, re, sys, time

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
cfg_dir = iso / "AppData" / "Roaming" / "Supervertaler"
cfg_dir.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
(cfg_dir / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8"
)

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected

win = Supervertaler.SupervertalerQt()
print(f"[{tag}] window built", flush=True)

# 1. извлечь исходник check_for_updates с диска
src = (tree / "Supervertaler.py").read_text(encoding="utf-8")
t = ast.parse(src)
fn = None
for node in ast.walk(t):
    if isinstance(node, ast.ClassDef) and node.name == "SupervertalerQt":
        for sub in node.body:
            if isinstance(sub, ast.FunctionDef) and sub.name == "check_for_updates":
                fn = sub
assert fn, "check_for_updates not found"
seg = ast.get_source_segment(src, fn)
lines = seg.splitlines()
# 2. нейтрализовать ранний return: от '        try:' до '        return' включительно
i_try = next(i for i, l in enumerate(lines) if l == "        try:")
i_ret = next(i for i, l in enumerate(lines) if l == "        return")
assert i_ret < 12, f"early return not near top? {i_ret}"
lines = lines[:i_try] + lines[i_ret + 1:]
# 3. принудительный fallback вместо start_request("api")
j = next(i for i, l in enumerate(lines) if l.strip() == 'start_request("api")')
lines[j] = lines[j].replace('start_request("api")', 'start_python_fallback("probe: forced")')
# 3b. убрать thread-hop: worker() синхронно в главном потоке (иначе QTimer.singleShot(0, ...),
# созданный в потоке без event loop, не доходит до главного loop'а — пре-существующее свойство
# механизма, вне объёма E-02; здесь проверяется только NameError-фикс)
k = next(i for i, l in enumerate(lines) if "threading.Thread(target=worker" in l)
lines[k] = lines[k].replace("threading.Thread(target=worker, daemon=True).start()", "worker()")
body = "\n".join(lines)

# 4. заглушки
captured = {"question": []}

class _NC:
    def connect(self, *a): pass

class _QProgressDialogStub:
    def __init__(self, *a, **k):
        self.canceled = _NC()
        self.destroyed = _NC()
    def setWindowTitle(self, *a): pass
    def setWindowModality(self, *a): pass
    def setMinimumDuration(self, *a): pass
    def setAutoClose(self, *a): pass
    def setAutoReset(self, *a): pass
    def show(self): pass
    def setLabelText(self, *a): pass
    def close(self): pass

class _QMessageBoxStub:
    StandardButton = type("SB", (), {"Yes": 1, "No": 2})
    StandardButton.Yes = 1
    StandardButton.No = 2
    @staticmethod
    def question(parent, title, text, *a, **k):
        captured["question"].append((title, text))
        return 2  # No
    @staticmethod
    def information(parent, title, text, *a, **k):
        captured.setdefault("information", []).append((title, text))
    @staticmethod
    def warning(parent, title, text, *a, **k):
        captured.setdefault("warning", []).append((title, text))

class _NS:
    Qt = Supervertaler.Qt
    QUrl = Supervertaler.QUrl
    QProgressDialog = _QProgressDialogStub
    QMessageBox = _QMessageBoxStub
    QNetworkAccessManager = Supervertaler.QNetworkAccessManager
    QTimer = Supervertaler.QTimer
    threading = __import__("threading")

ns = dict(_NS.__dict__)
exec(compile(body, "<check_for_updates-stripped>", "exec"), ns)

# 5. подмена fetch на raiser + запуск
win._fetch_latest_release_info_from_github = lambda timeout_seconds=6: (_ for _ in ()).throw(
    RuntimeError("probe-net-down-42"))
win._update_check_progress = None
try:
    ns["check_for_updates"](win)
except BaseException as e:
    print(f"[{tag}] EXC-SYNC on check_for_updates: {type(e).__name__}: {e}", flush=True)

# 6. прокрутить event loop, чтобы отработал QTimer.singleShot(0, on_err)
t0 = time.time()
while time.time() - t0 < 5 and not captured["question"]:
    app.processEvents()
    time.sleep(0.05)

if captured["question"]:
    title, text = captured["question"][0]
    hit = "probe-net-down-42" in text
    print(f"[{tag}] CAPTURED question: title={title!r} contains-error-text={hit}", flush=True)
    print(f"[{tag}] text[:300]={text[:300]!r}", flush=True)
    print(f"[{tag}] RESULT {'OK' if hit else 'PARTIAL'}", flush=True)
    os._exit(0 if hit else 2)
else:
    print(f"[{tag}] RESULT FAIL (no question captured in 5s)", flush=True)
    os._exit(1)
