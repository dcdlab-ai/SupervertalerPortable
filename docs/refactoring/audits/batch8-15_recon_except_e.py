"""Recon E-02: все места, где имя из `except ... as X` используется внутри
вложенной функции/lambda. Печатает охватывающий метод и КАК вызывается вложенная
функция (отложенно = реальный NameError; синхронно = безопасно)."""
import ast, pathlib

src = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py").read_text(encoding="utf-8")
lines = src.splitlines()
tree = ast.parse(src)


def enclosing_chain(node):
    """Возвращает список (kind, name, lineno) от top-level до родителя node."""
    parents = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parents[c] = p
    chain = []
    cur = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chain.append(("def", cur.name, cur.lineno))
        elif isinstance(cur, ast.ClassDef):
            chain.append(("class", cur.name, cur.lineno))
    return list(reversed(chain))


# соберём все FunctionDef/Lambda узлы с их except-областью видимости
hits = []

for handler_node in ast.walk(tree):
    if not isinstance(handler_node, ast.ExceptHandler) or handler_node.name is None:
        continue
    ename = handler_node.name

    # все вложенные функции/лямбды внутри handler
    for sub in ast.walk(handler_node):
        if sub is handler_node:
            continue
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            # имя except используется внутри sub (но не в более глубокой вложенной функции,
            # где оно уже не видно — Python: NameError в момент вызова)
            for n in ast.walk(sub):
                if isinstance(n, ast.Name) and n.id == ename and isinstance(n.ctx, ast.Load):
                    hits.append((handler_node, sub, n))
                    break

print(f"total handler-name-in-nested-function hits: {len(hits)}")
for h, sub, n in hits:
    chain = enclosing_chain(h)
    meth = " > ".join(f"{k}:{nm}@{ln}" for k, nm, ln in chain[-3:])
    # как вызывается sub: ищем в родителе sub ссылки на имя функции
    parents = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parents[c] = p
    name_of_sub = getattr(sub, "name", "<lambda>")
    call_ctx = []
    p = parents.get(sub)
    if isinstance(p, ast.Call):
        call_ctx.append("called-directly-in-except (sync)")
    else:
        # ищем все использования имени в обработчике
        for nn in ast.walk(handler_node):
            if isinstance(nn, ast.Name) and nn.id == name_of_sub and isinstance(nn.ctx, ast.Load):
                pp = parents.get(nn)
                desc = type(pp).__name__
                if isinstance(pp, ast.Call) and pp.func is nn:
                    desc += " CALL(sync?)"
                elif isinstance(pp, ast.Attribute):
                    desc += f" attr.{pp.attr}"
                elif isinstance(pp, ast.BinOp):
                    desc += " binop(Timer arg?)"
                call_ctx.append(f"line {nn.lineno}: {desc}")
    print(f"\nexcept as '{h.name}' @ {h.lineno} | nested {type(sub).__name__} '{name_of_sub}' @ {getattr(sub, 'lineno', '?')} | use @ {n.lineno}")
    print(f"  enclosing: {meth}")
    print(f"  uses of nested name: {call_ctx}")
    print(f"  code {n.lineno}: {lines[n.lineno-1].strip()[:130]}")
