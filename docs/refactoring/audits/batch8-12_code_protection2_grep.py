# -*- coding: utf-8 -*-
"""Batch #8.12 защита 2: grep по Supervertaler.py, modules/**, tools/**, tests/**
для КАЖДОГО удалённого идентификатора (имена 17 модулей, их публичные классы/
функции, match_memoq_status, compose_memoq_status, StatusDefinition,
4 HelpTopics-константы, voice-методы termbase_manager).

Формы: \bident\b в любом месте строки (покрывает import/from, строки, getattr,
connect, ключи). Вывод: идентификатор -> список file:line (кроме удалённых
файлов, которых уже нет). Ожидаемый результат: 0 hits, кроме допустимых
остатков (закомментированный Ribbon-блок монолита 9013-9024, одноимённые
символы живых модулей, docstring-самоупоминания).
"""
import pathlib
import re

REPO = pathlib.Path(r"E:\Dev\SupervertalerPortable")

MODULES = ["extract_tm", "feature_manager", "find_replace", "glossary_manager",
           "identifier_conventions", "pdf_rescue_tkinter", "project_home_panel",
           "project_tm", "prompt_assistant", "prompt_library", "quick_access_sidebar",
           "ribbon_widget", "style_guide_manager", "superdocs", "superdocs_viewer_qt",
           "tracked_changes", "translation_services"]

PUBLIC = ["ExtractTM", "get_extract_path", "extract_exists", "FeatureModule",
          "FeatureManager", "lazy_import_whisper", "lazy_import_chromadb",
          "lazy_import_sentence_transformers", "lazy_import_deepl", "lazy_import_boto3",
          "lazy_import_hunspell", "lazy_import_webengine", "lazy_import_fitz",
          "get_feature_manager", "check_feature", "FindReplaceDialog", "TermbaseInfo",
          "TermbaseEntry", "TermbaseManager", "tm_search_key", "tm_registry_id",
          "termbase_search_key", "tm_search_keys", "looks_like_registry_id",
          "PDFRescue", "ProjectHomeItem", "ProjectHomePanel", "ProjectTM",
          "PromptAssistant", "PromptLibrary", "QuickActionButton", "SidebarSection",
          "QuickAccessSidebar", "RibbonButton", "RibbonGroup", "RibbonTab",
          "ColoredTabBar", "RibbonWidget", "RibbonBuilder", "StyleGuideLibrary",
          "TrackedChangesAgent", "TrackedChangesBrowser", "format_tracked_changes_context",
          "TranslationRequest", "TranslationResult", "TranslationServices",
          "create_translation_service"]

EXTRA = ["match_memoq_status", "compose_memoq_status", "StatusDefinition",
         "SIDEKICK", "TRADOS_AWARE_CHAT", "CLIPBOARD",
         "get_termbase_voice_enabled", "set_termbase_voice_enabled",
         "get_voice_enabled_termbase_ids"]

# имена, которые НЕ проверяем как идентификаторы (одноимённые символы живого кода:
# TermbaseManager/get_user_data_path — свои классы в termbase_manager/config_manager;
# VOICE — подстрока TOOL_VOICE-комментария; PromptLibrary — см. ниже)
IDENTS = MODULES + PUBLIC + EXTRA

targets = [REPO / "Supervertaler.py"]
for sub in ("modules", "tools", "tests"):
    d = REPO / sub
    if d.exists():
        targets.extend(p for p in d.rglob("*.py") if "__pycache__" not in str(p))

hits = {n: [] for n in IDENTS}
for p in targets:
    text = p.read_text(encoding="utf-8", errors="replace")
    rel = p.relative_to(REPO).as_posix()
    for i, line in enumerate(text.splitlines(), 1):
        for n in IDENTS:
            if re.search(rf"\b{n}\b", line):
                hits[n].append(f"{rel}:{i}: {line.strip()[:130]}")

total = 0
for n in IDENTS:
    if hits[n]:
        total += len(hits[n])
        print(f"--- {n} ({len(hits[n])} hits)")
        for h in hits[n]:
            print(f"    {h}")
print(f"\nTOTAL hits: {total}")
zero = [n for n in IDENTS if not hits[n]]
print(f"zero-hit identifiers: {len(zero)}/{len(IDENTS)}")
