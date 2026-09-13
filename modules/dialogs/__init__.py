# modules.dialogs — диалоги, извлечённые из Supervertaler.py (Batch #3b, Step 3 EXTRACTION_PLAN.md).
# Каждый файл содержит ровно один класс, перенесённый вербатим.

from .theme_editor import ThemeEditorDialog
from .detached_log import DetachedLogWindow
from .advanced_filters import AdvancedFiltersDialog
from .scratchpad import ScratchpadDialog
from .live_progress import LiveProgressDialog
from .import_progress import _ImportProgressDialog

__all__ = [
    "ThemeEditorDialog",
    "DetachedLogWindow",
    "AdvancedFiltersDialog",
    "ScratchpadDialog",
    "LiveProgressDialog",
    "_ImportProgressDialog",
]
