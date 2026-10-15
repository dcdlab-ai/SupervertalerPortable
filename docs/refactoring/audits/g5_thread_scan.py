# G5 audit (READ-ONLY): scan QTimer.singleShot / direct widget access / modal
# dialogs in code executed from worker threads (QThread.run + transitive
# self-methods, threading.Thread/Timer targets, ThreadPoolExecutor submits).
# Reads product code, modifies nothing, no network.
import ast, os, sys
from collections import defaultdict

ROOT = os.getcwd()
FILES = ["Supervertaler.py"]
for dirpath, dirs, files in os.walk(os.path.join(ROOT, "modules")):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py"):
            FILES.append(os.path.relpath(os.path.join(dirpath, f), ROOT))

WIDGET_METHODS = {
    "setText","setPlainText","setHtml","append","appendHtml","addItem","addItems",
    "setCurrentRow","setCurrentIndex","setCurrentText","setChecked","setEnabled",
    "setVisible","setStyleSheet","setWindowTitle","setToolTip","setPlaceholderText",
    "setValue","setRange","setMaximum","setMinimum","update","repaint","show","hide",
    "close","setFocus","setReadOnly","insert","insertPlainText","moveCursor",
    "setSortingEnabled","setRowCount","setColumnCount","clear","setItem","setItemWidget",
    "setSortingEnabled","setSortingEnabled","setSortingEnabled","setSortingEnabled",
    "setSortingEnabled","setSortingEnabled","setSortingEnabled","setSortingEnabled",
}
MODAL_FUNCS = {
    ("QMessageBox","information"),("QMessageBox","warning"),("QMessageBox","critical"),
    ("QMessageBox","question"),("QMessageBox","about"),
    ("QFileDialog","getOpenFileName"),("QFileDialog","getSaveFileName"),
    ("QFileDialog","getExistingDirectory"),("QFileDialog","getOpenFileNames"),
    ("QColorDialog","getColor"),("QInputDialog","getText"),("QInputDialog","getInteger"),
    ("QInputDialog","getMultiLineText"),
}

def dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))

def collect(path):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src, filename=path)
    lines = src.splitlines()
    # ---- worker set ----
    worker_methods = set()   # (class, method)
    worker_funcs = set()     # function names (threading.Thread/Timer/executor targets)
    qthread_classes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = {b.id if isinstance(b, ast.Name) else dotted(b) for b in node.bases}
            if any("QThread" in b for b in bases):
                qthread_classes.add(node.name)
    # transitive closure from run()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in qthread_classes:
            methods = {m.name: m for m in node.body if isinstance(m, ast.FunctionDef)}
            if "run" not in methods:
                continue
            visited = {"run"}
            queue = ["run"]
            while queue:
                m = methods.get(queue.pop())
                if m is None:
                    continue
                for c in ast.walk(m):
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) \
                       and isinstance(c.func.value, ast.Name) and c.func.value.id == "self":
                        if c.func.attr in methods and c.func.attr not in visited:
                            visited.add(c.func.attr); queue.append(c.func.attr)
            for v in visited:
                worker_methods.add((node.name, v))
    # threading.Thread(target=NAME) / threading.Timer(_, NAME) / executor.submit(NAME)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            fname = dotted(fn) if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
            target = None
            if fname.endswith("Thread"):
                for kw in node.keywords:
                    if kw.arg == "target":
                        target = kw.value
            elif fname.endswith("Timer") and len(node.args) >= 2:
                target = node.args[1]
            elif fname.endswith(("submit","map")):
                target = node.args[0] if node.args else None
            if isinstance(target, ast.Name):
                worker_funcs.add(target.id)
            elif isinstance(target, ast.Lambda):
                worker_funcs.add("<lambda@%s:%d>" % (path, target.lineno))
    # ---- scan dangerous calls with enclosing context ----
    findings = []
    def walk(node, stack):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, stack + [(child.name, None)])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, stack + [(None, child.name)])
            elif isinstance(child, ast.Lambda):
                walk(child, stack + [(None, "<lambda@%d>" % child.lineno)])
            else:
                walk(child, stack)
        # dangerous calls at this node
        if isinstance(node, ast.Call):
            enc_cls = next((c for c, f in reversed(stack) if c), None)
            enc_fn = next((f for c, f in reversed(stack) if f), None)
            in_worker = (enc_cls, enc_fn) in worker_methods or enc_fn in worker_funcs
            fname = dotted(node.func) if isinstance(node.func, ast.Attribute) else (node.func.id if isinstance(node.func, ast.Name) else "")
            kind = None
            if fname.endswith("QTimer.singleShot") or fname.endswith(".singleShot"):
                kind = "QTimer.singleShot"
            elif fname.endswith("QMetaObject.invokeMethod") or fname.endswith(".invokeMethod"):
                kind = "invokeMethod"
            elif isinstance(node.func, ast.Attribute) and node.func.attr in WIDGET_METHODS:
                base = dotted(node.func.value) if isinstance(node.func.value, ast.Attribute) else (node.func.value.id if isinstance(node.func.value, ast.Name) else "")
                if any(t in base for t in ("parent_app","self.app","parent","win","app")):
                    kind = "widget-direct(%s.%s)" % (base, node.func.attr)
                elif enc_cls and enc_fn and (enc_cls, enc_fn) in worker_methods:
                    kind = "widget-self(%s)" % node.func.attr
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                 and (node.func.value.id, node.func.attr) in MODAL_FUNCS:
                kind = "modal-dialog(%s.%s)" % (node.func.value.id, node.func.attr)
            if kind:
                findings.append((path, node.lineno, kind, enc_cls, enc_fn, in_worker,
                                 lines[node.lineno-1].strip()[:90]))
    for top in ast.iter_child_nodes(tree):
        walk(top, [])
    return findings, worker_methods, worker_funcs, qthread_classes

all_findings = []
worker_summary = []
for f in FILES:
    try:
        fs, wm, wf, qc = collect(os.path.join(ROOT, f))
    except SyntaxError as e:
        print("SYNTAX", f, e); continue
    all_findings += fs
    if wm or wf:
        worker_summary.append((f, sorted(qc), sorted(wm), sorted(wf)))

print("=== WORKER SETS ===")
for f, qc, wm, wf in worker_summary:
    print(f"  {f}: QThread={qc} methods={wm} funcs={wf}")

print()
print("=== DANGEROUS CALLS (worker=True means inside worker-thread code) ===")
for path, ln, kind, cls, fn, inw, src in sorted(all_findings):
    if inw:
        print(f"  WORKER  {path}:{ln}  [{kind}]  in {cls}.{fn}  :: {src}")
print()
print("=== ALL singleShot/invokeMethod/modal (worker flag) ===")
for path, ln, kind, cls, fn, inw, src in sorted(all_findings):
    if kind.startswith(("QTimer","invokeMethod","modal")):
        print(f"  {'W' if inw else '.'}  {path}:{ln}  [{kind}]  in {cls}.{fn}  :: {src}")
