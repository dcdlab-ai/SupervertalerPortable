# -*- coding: utf-8 -*-
"""R9 Ч2: AST-инвентарь упоминаний провайдеров в Supervertaler.py и modules/*.

Каждое совпадение привязывается к владельцу (метод класса / функция модуля)
через ast.parse. Вывод: семья провайдера -> файл -> владельцы (lineno..end_lineno,
число попаданий). Полный JSON — в D:\\Temp\\SupervertalerPortable\\analysis\\r9\\.

Запуск (из корня репо): E:\\Dev\\python-embed\\python.exe docs/refactoring/audits/r9_provider_inventory.py
Только чтение; ничего не модифицирует.
"""
import ast, json, os, re, sys

ROOT = os.getcwd()
STAGE = r"E:\Dev\Work_temp\SupervertalerPortable\analysis\r9"

FAMILIES = {
    "openai":      r"openai",
    "claude":      r"claude|anthropic",
    "gemini":      r"gemini|generativelanguage|google\.generativeai|genai",
    "google_mt":   r"google_translate|translation\.googleapis|Google Translate|googletrans",
    "mistral":     r"mistral",
    "deepseek":    r"deepseek",
    "openrouter":  r"openrouter",
    "ollama":      r"ollama",
    "custom_openai": r"custom_openai",
    "custom_mt":   r"custom_mt",
    "mt_deepl":    r"\bdeepl\b",
    "mt_msft":     r"microsoft.*translat|azure.*translat",
    "mt_amazon":   r"amazon.*translat|boto3",
    "mt_modernmt": r"modernmt",
    "mt_mymemory": r"mymemory",
}


def owners_of_file(path):
    """[(name, lineno, end_lineno)] для методов классов и функций верхнего уровня."""
    with open(path, encoding="utf-8", errors="replace") as f:
        src = f.read()
    tree = ast.parse(src)
    lines = src.splitlines()
    out = []  # (owner, lineno, end_lineno, [lines_text])
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qual = None
            for n in ast.walk(tree):  # найти класс-владельца нельзя через ast.walk дёшево; делаем по диапазону ниже
                pass
            out.append((node.name, node.lineno, node.end_lineno))
    # аннотировать принадлежность классу
    def walk_class(node, prefix=""):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, ast.ClassDef):
                for item in ch.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        yield (f"{prefix}{ch.name}.{item.name}", item.lineno, item.end_lineno)
                walk_class(ch, prefix + ch.name + ".")
            elif isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield (prefix + ch.name, ch.lineno, ch.end_lineno)
    if hasattr(tree, "body"):
        out = list(walk_class(tree))
    out.sort(key=lambda t: t[1])
    return lines, out


def scan(path):
    lines, owners = owners_of_file(path)
    def owner_of(ln):
        for name, a, b in owners:
            if a <= ln <= b:
                return f"{name} ({a}-{b})"
        return "<module-level>"
    res = {}
    for fam, pat in FAMILIES.items():
        rx = re.compile(pat, re.IGNORECASE)
        hits = {}
        for i, text in enumerate(lines, 1):
            if rx.search(text):
                hits.setdefault(owner_of(i), []).append(i)
        if hits:
            res[fam] = {o: v for o, v in sorted(hits.items())}
    return res


def main():
    files = ["Supervertaler.py"]
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "modules")):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".py"):
                files.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    report = {}
    for rel in files:
        report[rel] = scan(os.path.join(ROOT, rel))
    os.makedirs(STAGE, exist_ok=True)
    with open(os.path.join(STAGE, "r9_provider_inventory.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    # сводка: семья -> файл -> число методов + суммарное число строк-попаданий
    print("family;file;owners;hit_lines")
    for fam in FAMILIES:
        for rel, fams in report.items():
            if fam in fams:
                owners = fams[fam]
                print(f"{fam};{rel};{len(owners)};{sum(len(v) for v in owners.values())}")
    print(f"\nfull JSON: {os.path.join(STAGE, 'r9_provider_inventory.json')}")


if __name__ == "__main__":
    main()
