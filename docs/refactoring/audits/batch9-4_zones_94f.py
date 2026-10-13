import ast, pathlib
src = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py").read_text(encoding="utf-8")
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in (
        "_create_mt_quick_lookup_settings_tab", "_save_mt_quick_lookup_settings",
        "create_llm_client", "_get_active_custom_profile", "_custom_llm_ready"):
        print(f"{node.name}: {node.lineno}-{node.end_lineno}")
src2 = pathlib.Path(r"E:\Dev\SupervertalerPortable\modules\quicktrans.py").read_text(encoding="utf-8")
tree2 = ast.parse(src2)
for node in ast.walk(tree2):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in (
        "_add_llm_providers", "_call_llm_translation", "_collect_providers"):
        print(f"quicktrans.py {node.name}: {node.lineno}-{node.end_lineno}")
