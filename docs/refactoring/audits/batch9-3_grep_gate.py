# -*- coding: utf-8 -*-
"""Batch 9.3 grep-гейт: удалённые идентификаторы = 0 вне разрешённых остатков.

Разрешённые остатки (перечень для отчёта):
  UI-зависимые имена до 9.4: _update_llm_indicator (ветки провайдеров статус-бара),
    _show_model_menu/_on_model_selected в chat_view (списки моделей),
    чекбоксы/радио/комбо AI Settings (_save_ai_settings_from_ui, _create_ai_settings_tab),
    QuickTrans-таб LLM (mtql_*), keepwarm-кластер (_setup_ollama_keepwarm и хвосты,
    set_ollama_timeout в llm_clients), _apply_gemini_proxy, show_about.
  Мёртвые методы 8.18: _REMOVED_add_mt_and_llm_matches_progressive,
    _save_llm_settings_from_ui.
  G5 (не трогать): figure-блок translate_current_segment с provider == "gemini".
  pdf_rescue_Qt.py — вне 9.x. docs/ — не сканируется. Комментарии — не код.
"""
import ast, pathlib, re, sys

# P1.8 (Part C): optional root override so the gate can be pointed at a
# staged tree with an injected violation (self-test of the new QSettings rule).
ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(r"E:\Dev\SupervertalerPortable")
MONO = (ROOT / "Supervertaler.py").read_bytes().decode("utf-8")
mono_lines = MONO.split("\n")

# --- AST-границы мёртвых методов и разрешённых зон монолита ---
tree = ast.parse(MONO)
allowed_spans = []  # (start, end, reason)
def walk(node, cls=None, reason_hint=None):
    for ch in ast.iter_child_nodes(node):
        if isinstance(ch, ast.ClassDef):
            walk(ch, ch.name)
        elif isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = (cls + "." if cls else "") + ch.name
            if ch.name in ("_REMOVED_add_mt_and_llm_matches_progressive", "_save_llm_settings_from_ui"):
                allowed_spans.append((ch.lineno, ch.end_lineno, "dead 8.18: " + ch.name))
            elif ch.name in ("_update_llm_indicator", "_setup_ollama_keepwarm", "_apply_ollama_timeout_setting",
                             "_start_ollama_keepwarm_timer", "_stop_ollama_keepwarm_timer",
                             "_ping_ollama_keepwarm", "_apply_gemini_proxy", "show_about",
                             "_save_ai_settings_from_ui", "_create_ai_settings_tab",
                             "_save_api_keys_from_ui", "_create_mt_quick_lookup_settings_tab",
                             "_save_mt_quick_lookup_settings"):
                allowed_spans.append((ch.lineno, ch.end_lineno, "UI 9.4: " + ch.name))
            walk(ch, cls)
        else:
            walk(ch, cls)
walk(tree)

def in_allowed(lineno):
    for a, b, _ in allowed_spans:
        if a <= lineno <= b:
            return True
    return False

# G5 (не трогать): figure-блок translate_current_segment
_m = MONO.split("\n")
_g5a = next(i for i, l in enumerate(_m, 1) if "Check for figure references and prepare images" in l)
_g5b = next(i for i, l in enumerate(_m, 1) if "Could not load figures" in l)
allowed_spans.append((_g5a, _g5b, "G5 figure block"))

PATTERNS = [
    (r"provider\s*==\s*['\"]ollama['\"]", "provider == 'ollama'"),
    (r"provider\s*==\s*['\"]openai['\"]", "provider == 'openai'"),
    (r"provider\s*==\s*['\"]claude['\"]", "provider == 'claude'"),
    (r"provider\s*==\s*['\"]gemini['\"]", "provider == 'gemini'"),
    (r"provider\s*==\s*['\"]mistral['\"]", "provider == 'mistral'"),
    (r"provider\s*==\s*['\"]deepseek['\"]", "provider == 'deepseek'"),
    (r"provider\s*==\s*['\"]openrouter['\"]", "provider == 'openrouter'"),
    (r"provider_name\s*==\s*['\"]gemini['\"]", "provider_name == 'gemini'"),
    (r"import\s+anthropic|from\s+anthropic", "import anthropic"),
    (r"google\.generativeai", "google.generativeai"),
    (r"\bcall_ollama\b|\b_call_ollama\b", "_call_ollama"),
    (r"check_ollama_status", "check_ollama_status"),
    (r"get_ollama_model_info", "get_ollama_model_info"),
    (r"get_claude_model_info", "get_claude_model_info"),
    (r"get_openai_translation", "get_openai_translation"),
    (r"get_claude_translation", "get_claude_translation"),
    (r"get_google_translation", "get_google_translation"),
    (r"_call_claude_with_usage", "_call_claude_with_usage"),
    (r"_call_gemini_with_usage", "_call_gemini_with_usage"),
    (r"_call_gemini_rest", "_call_gemini_rest"),
    (r"DEEPSEEK_MODELS", "DEEPSEEK_MODELS"),
]

def report(fname, content, is_mono):
    hits = {}
    lines = content.split("\n")
    for pat, label in PATTERNS:
        for i, line in enumerate(lines, 1):
            if re.search(pat, line):
                stripped = line.strip()
                is_comment = stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*")
                hits.setdefault(label, []).append((i, is_comment, stripped[:110]))
    out = []
    for label, rows in sorted(hits.items()):
        code_rows = [(i, t) for i, c, t in rows if not c or is_mono is False and False]
        if is_mono:
            bad = [(i, t) for i, c, t in rows if (not c) and not in_allowed(i)]
            allowed = [(i, t) for i, c, t in rows if c or in_allowed(i)]
        else:
            bad = [(i, t) for i, c, t in rows if not c]
            allowed = [(i, t) for i, c, t in rows if c]
        if bad:
            out.append(f"  FAIL {label}:")
            for i, t in bad[:10]:
                out.append(f"    {fname}:{i}: {t}")
        if allowed:
            out.append(f"  allowed {label}: {len(allowed)} (comment/разрешённые зоны)")
    return out

print("== Supervertaler.py (монолит) ==")
res = report("Supervertaler.py", MONO, True)
print("\n".join(res) if res else "  CLEAN (0 hits)")

# --- P1.8 Part C: QSettings constructor ban (M1 battery, P1.6 verdict) ---
# Qt 6 forces NativeFormat (HKCU) for the two-string-arg form
# QSettings("org", "app") REGARDLESS of setDefaultFormat(IniFormat), and any
# explicit NativeFormat is equally non-portable. Banned:
#   - >=2 positional args that are all plain string constants
#   - any argument expression mentioning NativeFormat
# Allowed: QSettings(fileName), QSettings(fileName, IniFormat),
# QSettings(fileName, IniFormat, parent), etc.
def qsettings_audit(fname, src):
    rows = []
    try:
        tree_q = ast.parse(src)
    except SyntaxError as e:
        return [f"  FAIL {fname}: SyntaxError {e}"]
    for node in ast.walk(tree_q):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else (
            f.attr if isinstance(f, ast.Attribute) else "")
        if name != "QSettings":
            continue
        where = f"{fname}:{node.lineno}"
        def is_str_const(a):
            return isinstance(a, ast.Constant) and isinstance(a.value, str)
        def mentions_native(a):
            return "NativeFormat" in ast.dump(a)
        strs = [a for a in node.args if is_str_const(a)]
        if len(node.args) >= 2 and len(strs) == len(node.args):
            rows.append(f"  FAIL {where}: two-arg string QSettings('org','app') "
                        f"-> forced NativeFormat (Qt6)")
        if any(mentions_native(a) for a in node.args) or \
           any(mentions_native(k.value) for k in node.keywords):
            rows.append(f"  FAIL {where}: explicit NativeFormat in QSettings")
    if rows:
        return rows
    return [f"  QSettings sites OK ({_qs_count(tree_q)})"]

def _qs_count(tree_q):
    n = 0
    for node in ast.walk(tree_q):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else (
                f.attr if isinstance(f, ast.Attribute) else "")
            if name == "QSettings":
                n += 1
    return n

print("== QSettings constructor gate (P1.8 Part C) ==")
qs_out = qsettings_audit("Supervertaler.py", MONO)
print("\n".join(qs_out))

GATE_MODULES = ["modules/llm_clients.py", "modules/settings_service.py", "modules/chat_backend.py",
                "modules/chat_view_widget.py", "modules/quicktrans.py",
                "modules/unified_prompt_manager_qt.py", "modules/workers/proofread.py",
                "modules/translation_results_panel.py"]
qs_fail = [r for r in qs_out if "FAIL" in r]
for mod in GATE_MODULES:
    c = (ROOT / mod).read_bytes().decode("utf-8")
    out_q = qsettings_audit(mod, c)
    print("\n".join(out_q))
    qs_fail += [r for r in out_q if "FAIL" in r]

for mod in GATE_MODULES:
    c = (ROOT / mod).read_bytes().decode("utf-8")
    print(f"== {mod} ==")
    r = report(mod, c, False)
    print("\n".join(r) if r else "  CLEAN (0 hits)")

if qs_fail:
    print("GATE-QS-FAIL")
    sys.exit(1)
