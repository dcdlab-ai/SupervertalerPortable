"""Recon E-03 (условие 1 Дмитрия): AST-проход vision-блока translate_current_segment
(50018-50047) — каждое имя/атрибут: существует ли? Поиск ТРЕТЬЕГО скрытого дефекта
того же сорта (NameError/AttributeError, глотаемого except @50046).

Проверяемые цели:
  self.figure_context.<m>   -> методы FigureContextManager (modules/figure_context_manager.py)
  LLMClient.<m>             -> класс modules/llm_clients.py (после фикса E-03a)
  pil_image_to_base64_png   -> модульная функция (после фикса E-03b)
  прочие Name/Attribute     -> locals функции / builtins / self.*
"""
import ast, pathlib, builtins

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
mono_src = (ROOT / "Supervertaler.py").read_text(encoding="utf-8")
tree = ast.parse(mono_src)

BLOCK_LO, BLOCK_HI = 50018, 50047  # включительно: комментарий .. except-тело

# --- 1. собрать целевые факты из modules ---
fc_src = (ROOT / "modules" / "figure_context_manager.py").read_text(encoding="utf-8")
fc_tree = ast.parse(fc_src)
fc_methods = set()
fc_module_funcs = set()
for node in fc_tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "FigureContextManager":
        for sub in node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fc_methods.add(sub.name)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        fc_module_funcs.add(node.name)

llm_src = (ROOT / "modules" / "llm_clients.py").read_text(encoding="utf-8")
llm_tree = ast.parse(llm_src)
llm_class_members = set()
for node in llm_tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "LLMClient":
        for sub in node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                llm_class_members.add(sub.name)
            elif isinstance(sub, ast.Assign):
                for t in sub.targets:
                    if isinstance(t, ast.Name):
                        llm_class_members.add(t.id)

# --- 2. найти translate_current_segment и locals до блока ---
def collect_locals(fn, upto_lineno):
    names = set()
    for node in ast.walk(fn):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not fn:
            continue
        if getattr(node, "lineno", 0) > upto_lineno:
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.comprehension):
            for t in ast.walk(node.target):
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names

tcs = None
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "SupervertalerQt":
        for sub in node.body:
            if isinstance(sub, ast.FunctionDef) and sub.name == "translate_current_segment":
                tcs = sub
if tcs is None:
    raise SystemExit("translate_current_segment not found")

locals_before = collect_locals(tcs, BLOCK_LO)
self_attrs = {n.attr for n in ast.walk(tcs) if isinstance(n, ast.Attribute)
              and isinstance(n.value, ast.Name) and n.value.id == "self"}

# --- 3. пройти блок и проверить каждое имя/атрибут ---
print(f"vision block: {BLOCK_LO}-{BLOCK_HI}; locals before: {len(locals_before)}; "
      f"FC methods: {sorted(fc_methods)}; module funcs: {sorted(fc_module_funcs)}")

problems = []
def check_block(block):
    for node in ast.walk(block):
        if not (BLOCK_LO <= getattr(node, "lineno", 0) <= BLOCK_HI):
            continue
        if isinstance(node, ast.Attribute):
            val = node.value
            if isinstance(val, ast.Name) and val.id == "self" and node.attr == "figure_context":
                continue  # сам атрибут figure_context — проверен (init @6312)
            if isinstance(val, ast.Name) and val.id == "figure_context" and any(
                isinstance(p := x, ast.Attribute) for x in []):
                pass
            # x.figure_context.<m>
            if isinstance(val, ast.Attribute) and val.attr == "figure_context":
                m = node.attr
                status = "OK" if m in fc_methods else "MISSING-IN-FC"
                print(f"  line {node.lineno}: self.figure_context.{m} -> {status}")
                if m not in fc_methods:
                    problems.append((node.lineno, f"self.figure_context.{m}", status))
            # LLMClient.<m>
            elif isinstance(val, ast.Name) and val.id == "LLMClient":
                m = node.attr
                status = "OK(classmember)" if m in llm_class_members else "MISSING-IN-LLMCLIENT"
                print(f"  line {node.lineno}: LLMClient.{m} -> {status}")
                if m not in llm_class_members:
                    problems.append((node.lineno, f"LLMClient.{m}", status))
            # module function pil_image_to_base64_png (после фикса будет Name, сейчас Attribute на figure_context)
            elif isinstance(val, ast.Name) and val.id in fc_module_funcs:
                print(f"  line {node.lineno}: {val.id}.{node.attr} (attr on module func?)")

for node in ast.walk(tcs):
    if isinstance(node, ast.If) and node.lineno == 50020:
        check_block(node)
        break

# Name-loads в блоке
if_node = next(n for n in ast.walk(tcs) if isinstance(n, ast.If) and n.lineno == 50020)
bi = builtins.__dict__
for n in ast.walk(if_node):
    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and BLOCK_LO <= n.lineno <= BLOCK_HI:
        if n.id in ("self", "figure_context"):
            continue
        if n.id in locals_before:
            continue
        if n.id in bi:
            continue
        if n.id in fc_module_funcs:
            print(f"  line {n.lineno}: Name '{n.id}' -> module function (OK после E-03b)")
            continue
        print(f"  line {n.lineno}: Name '{n.id}' -> ??? NOT local/builtin/modulefunc")

print("\nPROBLEMS (2 known expected):")
for p in problems:
    print("  ", p)
