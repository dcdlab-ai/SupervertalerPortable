# -*- coding: utf-8 -*-
"""Top-level class boundaries via AST — never trust documented line numbers.
Usage: python ast_classes.py <file.py> [ClassName1,ClassName2 | all]"""
import ast, sys

src = open(sys.argv[1], encoding="utf-8").read()
tree = ast.parse(src)
wanted = None if len(sys.argv) < 3 or sys.argv[2] == "all" else set(sys.argv[2].split(","))

for node in tree.body:
    if not isinstance(node, ast.ClassDef):
        continue
    if wanted and node.name not in wanted:
        continue
    methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
    bases = [ast.unparse(b) for b in node.bases]
    print(f"{node.name}: lines {node.lineno}-{node.end_lineno} (bases: {bases}, methods: {methods})")
