"""Защита 1 (§4.1) Batch #8.10: резолв вызовов стартовой цепочки через AST.

Цепочка (постановка 8.10, Этап 0 п.5а): main, SupervertalerQt.__init__, init_ui,
create_menus, create_main_layout, setup_global_shortcuts, _setup_progress_indicators,
_warm_up_top_tabs, create_settings_tab + все методы страниц Settings,
SuperlookupTab.__init__/init_ui/perform_lookup/search_with_query/
on_results_tab_changed/register_global_hotkey, SupervertalerQt.closeEvent.

Запуск: python startup_chain_resolve.py [path-to-Supervertaler.py] [tag]
"""
import ast, json, pathlib, re, sys

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
MONOLITH = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "Supervertaler.py"

STATIC_CHAIN = [
    "main",
    "SupervertalerQt.__init__",
    "SupervertalerQt.init_ui",
    "SupervertalerQt.create_menus",
    "SupervertalerQt.create_main_layout",
    "SupervertalerQt.setup_global_shortcuts",
    "SupervertalerQt._setup_progress_indicators",
    "SupervertalerQt._setup_tray_icon",
    "SupervertalerQt._on_main_tab_changed",
    "SupervertalerQt._warm_up_top_tabs",
    "SupervertalerQt.create_grid_view_widget_for_home",
    "SupervertalerQt.create_assistance_panel",
    "SupervertalerQt.create_settings_tab",
    "SupervertalerQt.closeEvent",
    "SuperlookupTab.__init__",
    "SuperlookupTab.init_ui",
    "SuperlookupTab.perform_lookup",
    "SuperlookupTab.search_with_query",
    "SuperlookupTab.on_results_tab_changed",
    "SuperlookupTab.register_global_hotkey",
]


def build_chain(tree):
    chain = list(STATIC_CHAIN)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "SupervertalerQt":
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and (
                    re.match(r"_create_.*_settings_tab$", sub.name)
                    or sub.name in ("create_termbases_tab", "create_assistance_panel",
                                    "create_grid_view_widget_for_home")
                ):
                    chain.append(f"SupervertalerQt.{sub.name}")
    return chain


def main():
    tree = ast.parse(MONOLITH.read_text(encoding="utf-8"))

    top_funcs = set()
    classes = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            top_funcs.add(node.name)
        elif isinstance(node, ast.ClassDef):
            methods = {}
            assigned = set()
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods[sub.name] = sub
                elif isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                            assigned.add(t.attr)
                elif isinstance(sub, ast.AnnAssign):
                    if isinstance(sub.target, ast.Attribute) and isinstance(sub.target.value, ast.Name) and sub.target.value.id == "self":
                        assigned.add(sub.target.attr)
            classes[node.name] = {"methods": methods, "assigned_attrs": assigned}

    results = []
    unresolved = 0

    try:
        from PyQt6.QtWidgets import QMainWindow, QWidget
        from PyQt6.QtCore import QObject
        qt_api = set(dir(QMainWindow)) | set(dir(QWidget)) | set(dir(QObject))
    except Exception:
        qt_api = set()

    def walk_calls(func_node, cls_name):
        nonlocal unresolved
        cls = classes.get(cls_name) if cls_name else None
        for node in ast.walk(func_node):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self":
                attr = f.attr
                if cls is not None:
                    if attr in cls["methods"]:
                        results.append({"call": f"self.{attr}()", "resolved": f"{cls_name}.{attr}", "ok": True})
                        continue
                    if attr in cls["assigned_attrs"]:
                        results.append({"call": f"self.{attr}()", "resolved": f"assigned attr self.{attr}", "ok": True})
                        continue
                    if attr in qt_api:
                        results.append({"call": f"self.{attr}()", "resolved": "Qt base-class API", "ok": True})
                        continue
                    results.append({"call": f"self.{attr}()", "resolved": None, "ok": False})
                    unresolved += 1
                elif cls_name is None:
                    results.append({"call": f"self.{attr}() in main()", "resolved": None, "ok": False})
                    unresolved += 1

    for entry in build_chain(tree):
        if entry == "main":
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
            walk_calls(fn, None)
        else:
            cls_name, meth = entry.split(".")
            fn = classes[cls_name]["methods"].get(meth)
            if fn is None:
                print(f"MISSING METHOD: {entry}", file=sys.stderr)
                unresolved += 1
                continue
            walk_calls(fn, cls_name)

    out_path = pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b8-10")
    tag = sys.argv[2] if len(sys.argv) > 2 else "after"
    (out_path / f"startup_chain_{tag}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    bad = [r for r in results if not r["ok"]]
    print(f"total calls: {len(results)}, unresolved: {unresolved}")
    for r in bad:
        print("UNRESOLVED:", r["call"])
    sys.exit(1 if unresolved else 0)


if __name__ == "__main__":
    main()
