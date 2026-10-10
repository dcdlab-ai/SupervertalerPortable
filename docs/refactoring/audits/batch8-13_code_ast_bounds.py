import ast, sys, pathlib

path = pathlib.Path(sys.argv[1])
src = path.read_text(encoding="utf-8")
tree = ast.parse(src)
targets = sys.argv[2:]

# Map: for every FunctionDef, record enclosing class chain
def walk(node, parents):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cls = next((p.name for p in reversed(parents) if isinstance(p, ast.ClassDef)), "<module>")
            qual = f"{cls}.{child.name}"
            if child.name in targets:
                print(f"{qual}: {child.lineno}-{child.end_lineno}")
            walk(child, parents + [child])
        elif isinstance(child, ast.ClassDef):
            if child.name in targets:
                print(f"class {child.name}: {child.lineno}-{child.end_lineno}")
            walk(child, parents + [child])
        else:
            walk(child, parents + [child])

walk(tree, [])
