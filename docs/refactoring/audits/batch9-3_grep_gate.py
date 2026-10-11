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

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
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

for mod in ["modules/llm_clients.py", "modules/settings_service.py", "modules/chat_backend.py",
            "modules/chat_view_widget.py", "modules/quicktrans.py",
            "modules/unified_prompt_manager_qt.py", "modules/workers/proofread.py",
            "modules/translation_results_panel.py"]:
    c = (ROOT / mod).read_bytes().decode("utf-8")
    print(f"== {mod} ==")
    r = report(mod, c, False)
    print("\n".join(r) if r else "  CLEAN (0 hits)")
