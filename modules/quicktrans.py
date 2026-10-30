"""
QuickTrans - Instant translation popup (GT4T-style)

A popup window that shows translations from all enabled MT engines and LLMs.
Part of the Supervertaler tool suite. Triggered by Ctrl+M (in-app) or Ctrl+Alt+Q (global).

Features:
- Shows source text at the top
- Displays numbered list of translations from MT engines and LLMs
- Press number key (1-9) or click to insert translation
- Escape to dismiss
- Translations fetched in parallel for speed
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget, QPushButton, QApplication, QSizePolicy, QComboBox,
    QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt6.QtGui import QKeySequence, QShortcut, QCursor, QFont
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.portable_paths import state_root


# Provider chip colours, keyed by internal provider code. Shared by the popup
# rows (MTSuggestionItem) and the docked panel (QuickTransPanel) so the colour
# coding stays consistent everywhere.
PROVIDER_COLORS = {
    "CMT": "#00897B",   # Custom MT teal
    "CUS": "#9C27B0",   # Custom purple
}

# Fixed width (px) reserved for the provider pill column in QuickTrans rows, so
# the translation text starts at the same x-position in every row regardless of
# how wide each provider's pill is. Wide enough for the longest provider names
# ("Google Translate", "Microsoft (free)", …).
PROVIDER_CHIP_COLUMN_WIDTH = 116

# Shared style for the small icon-only header buttons in the docked panel.
_PANEL_ICON_BTN_STYLE = """
    QPushButton { border: none; background: transparent; font-size: 13px; }
    QPushButton:hover { background-color: #e0e0e0; border-radius: 4px; }
    QPushButton:focus { outline: none; }
"""


# Provider codes that are AI/LLM rather than machine-translation engines, used
# to group QuickTrans results. Everything not listed here (GT, DL, MS, AT, MMT,
# MM, and CMT custom-MT) is treated as a machine-translation engine.
_AI_PROVIDER_CODES = {"CUS"}


def _is_ai_code(code: str) -> bool:
    return code in _AI_PROVIDER_CODES


# Q.2: marker shown in a QuickTrans row when the segment is link-only (one or
# more Markdown image links with no other letters/digits — same detector as
# the batch translator, modules.bilingual_markdown_handler.is_image_links_only).
# The network request is skipped; the row carries the source verbatim plus
# this note, and inserting it puts the untouched source into the target (draft,
# M1 behaviour). Mixed segments (a link plus words/digits) are fetched normally.
LINK_ONLY_MARKER = "⤳ link-only — не отправлено"


def _is_link_only_text(text: str) -> bool:
    """True for link-only segments (Q.2). Lazy import mirrors _canonical_lang_name."""
    if not text:
        return False
    try:
        from modules.bilingual_markdown_handler import is_image_links_only
    except Exception:
        return False
    try:
        return bool(is_image_links_only(text))
    except Exception:
        return False


def _is_panel_error_text(translation: str) -> bool:
    """True for the app's bracketed notice strings ('[Error: …]', '[MT proxy
    …]', '[Custom MT …]', '[No translation returned]', …) that the fetch
    layer returns instead of raising. The worker's is_error flag only covers
    texts containing 'error', so the panel normalises here (Q.4): every
    bracketed notice becomes an error ROW of the panel — no Paste button,
    Ctrl+N skips it — while the popup keeps its own unchanged handling."""
    t = (translation or '').strip()
    return t.startswith('[') and t.endswith(']')


# Canonical list of translation languages, shared by the QuickTrans popup's
# language-pair selector and Settings → Language Pair (Supervertaler.py imports
# this so the two stay in sync). Full display names – the same strings the
# project stores and the MT/LLM call functions expect.
AVAILABLE_LANGUAGES = [
    "Afrikaans", "Albanian", "Arabic", "Armenian", "Basque", "Bengali",
    "Bulgarian", "Catalan", "Chinese (Simplified)", "Chinese (Traditional)",
    "Croatian", "Czech", "Danish", "Dutch", "English", "Estonian",
    "Finnish", "French", "Galician", "Georgian", "German", "Greek",
    "Hebrew", "Hindi", "Hungarian", "Icelandic", "Indonesian", "Irish",
    "Italian", "Japanese", "Korean", "Latvian", "Lithuanian", "Macedonian",
    "Malay", "Norwegian", "Persian", "Polish", "Portuguese", "Romanian",
    "Russian", "Serbian", "Slovak", "Slovenian", "Spanish", "Swahili",
    "Swedish", "Thai", "Turkish", "Ukrainian", "Urdu", "Vietnamese", "Welsh",
]


def _canonical_lang_name(value):
    """Return the canonical display name from AVAILABLE_LANGUAGES for a language
    given as either a name or a code (e.g. 'nl' / 'Nederlands' → 'Dutch').

    The combos hold full names, so a value the project stores as a *code*
    ('en'/'nl') must be mapped — otherwise setCurrentText() silently no-ops and
    the combo falls back to its first item ('Afrikaans'). Returns the input
    unchanged when it can't be mapped (so unknown values still pass through to
    the MT/LLM providers, which accept names or codes)."""
    if not value:
        return value
    if value in AVAILABLE_LANGUAGES:
        return value
    try:
        from modules.lang_detect import lang_code
    except Exception:
        return value
    code = lang_code(value)
    if not code:
        return value
    for name in AVAILABLE_LANGUAGES:
        if lang_code(name) == code:
            return name
    return value


@dataclass
class MTSuggestion:
    """A single MT suggestion from a provider"""
    provider_name: str  # Full name: "Google Translate", "DeepL", etc.
    provider_code: str  # Short code: "CMT", "CUS", …
    translation: str
    is_error: bool = False
    # Q.2: link-only row — request skipped, translation holds the source
    # verbatim; the row shows LINK_ONLY_MARKER and stays clickable.
    link_only: bool = False


class MTFetchWorker(QThread):
    """Background worker to fetch MT translations in parallel"""

    result_ready = pyqtSignal(str, str, str, bool, bool)  # provider_name, provider_code, translation, is_error, link_only
    all_complete = pyqtSignal()

    def __init__(self, source_text: str, source_lang: str, target_lang: str,
                 providers: List[Tuple[str, str, callable]], parent=None):
        super().__init__(parent)
        self.source_text = source_text
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.providers = providers  # List of (name, code, call_function)

    def run(self):
        """Fetch translations from all providers in parallel"""
        def fetch_single(provider_info):
            name, code, call_func = provider_info
            # Q.2: the lowest common gate of every QuickTrans entry (popup and
            # docked panel, MT auto-fetch and LLM Fetch buttons) — a link-only
            # segment never reaches the network: the row carries the source
            # verbatim. Covers MT and LLM call functions alike.
            if _is_link_only_text(self.source_text):
                return (name, code, self.source_text, False, True)
            try:
                result = call_func(self.source_text, self.source_lang, self.target_lang)
                is_error = result.startswith('[') and 'error' in result.lower()
                return (name, code, result, is_error, False)
            except Exception as e:
                return (name, code, f"[Error: {str(e)}]", True, False)

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fetch_single, p): p for p in self.providers}
            for future in as_completed(futures):
                try:
                    name, code, translation, is_error, link_only = future.result()
                    self.result_ready.emit(name, code, translation, is_error, link_only)
                except Exception as e:
                    provider = futures[future]
                    self.result_ready.emit(provider[0], provider[1], f"[Error: {str(e)}]", True, False)

        self.all_complete.emit()


# Q.6: workers cooperatively detached from a closing popup/panel. The window
# releases them (no parent, no handlers touching its widgets); this registry
# keeps each QThread object alive until run() returns — the network request is
# NOT aborted and lives until the server answers or times out; all_complete
# then removes the worker so it is garbage-collected with a finished thread
# (never destroyed while running).
_DETACHED_WORKERS: List[MTFetchWorker] = []


def _detach_worker_for_close(worker: MTFetchWorker) -> None:
    """Detach a still-running worker from a closing QuickTrans window (Q.6):
    drop its signal connections (a queued emission already in flight is also
    stopped by the window's ``_closed`` guard), unparent it, and park it in the
    module-level registry until the in-flight request completes."""
    try:
        worker.result_ready.disconnect()
    except TypeError:
        pass
    try:
        worker.all_complete.disconnect()
    except TypeError:
        pass
    if worker.parent() is not None:
        worker.setParent(None)
    _DETACHED_WORKERS.append(worker)

    def _remove_from_detached(_w=worker):
        try:
            _DETACHED_WORKERS.remove(_w)
        except ValueError:
            pass

    worker.all_complete.connect(_remove_from_detached)


class MTSuggestionItem(QFrame):
    """A single MT suggestion row in the popup"""

    clicked = pyqtSignal(str)  # Emits the translation text when clicked

    def __init__(self, number: int, suggestion: MTSuggestion, parent=None):
        super().__init__(parent)
        self.suggestion = suggestion
        self.number = number
        self.is_selected = False

        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        # Number badge (stored so the pick-number can be updated when results
        # are regrouped into MT / AI sections after all fetches complete).
        # Kept small and light so it visually matches the compact provider pill
        # rather than dominating the row.
        num_label = QLabel(str(number))
        self.num_label = num_label
        num_label.setFixedSize(18, 18)
        num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_label.setStyleSheet("""
            QLabel {
                background-color: #ff9800;
                color: white;
                font-weight: bold;
                font-size: 10px;
                border-radius: 4px;
            }
        """)
        # Align to the top so the badge stays a small fixed pill instead of
        # stretching down the full height of a multi-line (long) translation.
        layout.addWidget(num_label, 0, Qt.AlignmentFlag.AlignTop)

        # Provider name badge – a compact pill, top-aligned and content-sized.
        provider_label = QLabel(suggestion.provider_name)
        provider_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Keep the chip its natural (text) height regardless of row height.
        provider_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        # Color-code by provider code (internal key, not displayed)
        bg_color = PROVIDER_COLORS.get(suggestion.provider_code, "#666")
        provider_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                font-weight: 600;
                font-size: 9px;
                border-radius: 9px;
                padding: 1px 8px;
            }}
        """)
        # Place the pill in a fixed-width column so the translation text starts at
        # the same x-position in every row (the pills themselves vary in width).
        chip_cell = QWidget()
        chip_cell.setFixedWidth(PROVIDER_CHIP_COLUMN_WIDTH)
        chip_cell_layout = QHBoxLayout(chip_cell)
        chip_cell_layout.setContentsMargins(0, 0, 0, 0)
        chip_cell_layout.setSpacing(0)
        chip_cell_layout.addWidget(
            provider_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        chip_cell_layout.addStretch()
        layout.addWidget(chip_cell, 0, Qt.AlignmentFlag.AlignTop)

        # Translation text
        text_label = QLabel(suggestion.translation)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        if suggestion.is_error:
            text_label.setStyleSheet("color: #ff6b6b; font-size: 11px;")
        else:
            text_label.setStyleSheet("color: #333; font-size: 11px;")

        layout.addWidget(text_label, 1, Qt.AlignmentFlag.AlignTop)

        # Q.2: link-only rows show the skip note next to the (verbatim) source.
        if suggestion.link_only:
            marker_label = QLabel(LINK_ONLY_MARKER)
            marker_label.setStyleSheet("color: #999; font-size: 9px; border: none;")
            layout.addWidget(marker_label, 0, Qt.AlignmentFlag.AlignTop)

        self._update_style()

    def _update_style(self):
        """Update visual style based on selection state"""
        if self.is_selected:
            self.setStyleSheet("""
                MTSuggestionItem {
                    background-color: #e3f2fd;
                    border: 1px solid #2196F3;
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                MTSuggestionItem {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                }
                MTSuggestionItem:hover {
                    background-color: #f5f5f5;
                    border: 1px solid #bdbdbd;
                }
            """)

    def select(self):
        """Select this item"""
        self.is_selected = True
        self._update_style()

    def deselect(self):
        """Deselect this item"""
        self.is_selected = False
        self._update_style()

    def set_number(self, number: int):
        """Update the displayed pick-number (used when results are regrouped)."""
        self.number = number
        if getattr(self, 'num_label', None) is not None:
            self.num_label.setText(str(number))

    def mousePressEvent(self, event):
        """Handle click to select this translation"""
        if event.button() == Qt.MouseButton.LeftButton and not self.suggestion.is_error:
            self.clicked.emit(self.suggestion.translation)
        super().mousePressEvent(event)


class PanelResultRow(QFrame):
    """A single result row in the docked QuickTrans panel (Q.4).

    Unlike the popup's MTSuggestionItem (click inserts the translation), a
    panel row never inserts on click — a click only places the cursor in the
    editable field. Insertion goes through the row's Paste button or the
    panel's Ctrl+1..9 shortcuts, both of which read the field's CURRENT text
    (user edits included), not the original provider answer. Error rows
    carry the error text for visibility but get no Paste button, and Ctrl+N
    skips them, so an error message can never reach the target cell.
    Link-only rows (Q.2) hold the source verbatim; Paste inserts it
    unchanged (draft, M1 behaviour)."""

    paste_requested = pyqtSignal(str)  # text to insert into the target cell

    _FIELD_MIN_H = 26  # single-line height floor for the result field

    def __init__(self, number: int, suggestion: MTSuggestion, parent=None):
        super().__init__(parent)
        self.suggestion = suggestion
        self.number = number

        # Static card look: the row is no longer click-to-insert (Q.4), so
        # there is no pointing-hand cursor, hover highlight or selection state.
        self.setStyleSheet("""
            PanelResultRow {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        # Number badge — same compact pill as the popup rows.
        self.num_label = QLabel(str(number))
        self.num_label.setFixedSize(18, 18)
        self.num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.num_label.setStyleSheet("""
            QLabel {
                background-color: #ff9800;
                color: white;
                font-weight: bold;
                font-size: 10px;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.num_label, 0, Qt.AlignmentFlag.AlignTop)

        # Provider chip in the fixed-width column — same as the popup rows,
        # so the result text starts at the same x-position in every row.
        provider_label = QLabel(suggestion.provider_name)
        provider_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        provider_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        bg_color = PROVIDER_COLORS.get(suggestion.provider_code, "#666")
        provider_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                font-weight: 600;
                font-size: 9px;
                border-radius: 9px;
                padding: 1px 8px;
            }}
        """)
        chip_cell = QWidget()
        chip_cell.setFixedWidth(PROVIDER_CHIP_COLUMN_WIDTH)
        chip_cell_layout = QHBoxLayout(chip_cell)
        chip_cell_layout.setContentsMargins(0, 0, 0, 0)
        chip_cell_layout.setSpacing(0)
        chip_cell_layout.addWidget(
            provider_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        chip_cell_layout.addStretch()
        layout.addWidget(chip_cell, 0, Qt.AlignmentFlag.AlignTop)

        # Q.4: editable result field — text is selectable, copyable and
        # editable; the row height follows the text. QTextEdit (rich text
        # off) rather than QPlainTextEdit: its document layout reports the
        # laid-out height in PIXELS and re-reports on wrap/width changes,
        # which the auto-height below needs (QPlainTextEdit reports line
        # counts instead).
        # NB: set via setPlainText, not the QTextEdit(text) constructor — the
        # constructor's insertion path collapses "\n" into a space (verified
        # offscreen), setPlainText keeps paragraph breaks.
        self.field = QTextEdit()
        self.field.setPlainText(suggestion.translation or "")
        self.field.setAcceptRichText(False)
        self.field.setTabChangesFocus(True)
        if suggestion.is_error:
            self.field.setStyleSheet(
                "QPlainTextEdit { color: #ff6b6b; font-size: 11px; "
                "border: 1px solid #f3d6d6; border-radius: 3px; background: white; }")
        else:
            self.field.setStyleSheet(
                "QPlainTextEdit { color: #333; font-size: 11px; "
                "border: 1px solid #e0e0e0; border-radius: 3px; background: white; }")
        layout.addWidget(self.field, 1)

        # Q.2: link-only rows show the skip note next to the (verbatim) source.
        if suggestion.link_only:
            marker_label = QLabel(LINK_ONLY_MARKER)
            marker_label.setStyleSheet("color: #999; font-size: 9px; border: none;")
            layout.addWidget(marker_label, 0, Qt.AlignmentFlag.AlignTop)

        # Q.4: Paste inserts the field's current text (selection first) into
        # the target cell through the panel's existing insert path. Not shown
        # for error rows — an error message must not reach the target.
        if not suggestion.is_error:
            paste_btn = QPushButton("Paste")
            paste_btn.setFixedHeight(22)
            paste_btn.setToolTip(
                "Insert into the target cell: the selected fragment of this "
                "field, or the whole field text if nothing is selected")
            paste_btn.clicked.connect(self._on_paste)
            layout.addWidget(paste_btn, 0, Qt.AlignmentFlag.AlignTop)

        # Auto-height: follow the document's laid-out height (line count after
        # wrapping at the current field width). documentSizeChanged fires on
        # text edits, width changes and font resolution, keeping the row snug.
        self.field.document().documentLayout().documentSizeChanged.connect(self._adjust_height)
        self._adjust_height()

    def _adjust_height(self):
        doc = self.field.document()
        h = int(round(doc.documentLayout().documentSize().height()))
        m = self.field.contentsMargins()
        h += m.top() + m.bottom() + 2 * self.field.frameWidth() + 2  # rounding slack
        self.field.setFixedHeight(max(self._FIELD_MIN_H, h))

    def _on_paste(self):
        """Emit the text Paste should insert: the field's selection if there
        is one, else the whole current field text (user edits included).
        QTextCursor.selectedText() uses U+2029 for paragraph breaks."""
        cursor = self.field.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText().replace('\u2029', '\n')
        else:
            text = self.field.toPlainText()
        if text:
            self.paste_requested.emit(text)

    def current_text(self) -> str:
        """The field's current text (user edits included) — what Ctrl+1..9
        and Paste insert for this row."""
        return self.field.toPlainText()

    def set_number(self, number: int):
        """Update the displayed pick-number (rows are renumbered in visual
        order as results arrive)."""
        self.number = number
        if getattr(self, 'num_label', None) is not None:
            self.num_label.setText(str(number))


class QuickTransProviderMixin:
    """Shared provider enumeration + LLM calling logic.

    Used by both the QuickTrans popup (``MTQuickPopup``) and the docked
    under-grid panel (``QuickTransPanel``). Both set ``self.parent_app`` to the
    Workbench main window, which supplies the API keys, enabled-provider
    states, MT call methods, and LLM client wiring.
    """

    def _load_mt_quick_settings(self) -> Dict[str, Any]:
        """Load MT Quick Lookup specific settings"""
        if hasattr(self.parent_app, 'load_general_settings'):
            settings = self.parent_app.load_general_settings()
            return settings.get('mt_quick_lookup', {})
        return {}

    def _get_enabled_providers(self, include_mt: bool = True,
                               include_llms: bool = True) -> List[Tuple[str, str, callable]]:
        """Get enabled providers with their call functions.

        ``include_mt`` / ``include_llms`` let callers fetch only the cheap MT
        engines or only the (paid) LLMs – the docked panel uses this to
        auto-fetch MT while keeping LLMs on-demand.
        """
        providers = []

        if not self.parent_app:
            return providers

        api_keys = {}
        enabled_providers = {}

        if hasattr(self.parent_app, 'load_api_keys'):
            api_keys = self.parent_app.load_api_keys()
        if hasattr(self.parent_app, 'load_provider_enabled_states'):
            enabled_providers = self.parent_app.load_provider_enabled_states()

        # Load MT Quick Lookup specific settings
        mt_quick_settings = self._load_mt_quick_settings()

        if include_mt:

            # Custom MT endpoint(s): when the master 'mtql_custom_mt' toggle is on,
            # each configured profile (with an endpoint) becomes its own MT chip.
            # Independent of the AI custom endpoint, so MT and AI can point at
            # different OpenAI-compatible services at the same time.
            if (mt_quick_settings.get('mtql_custom_mt', False)
                    and hasattr(self.parent_app, 'call_custom_mt')):
                llm_settings = (self.parent_app.load_llm_settings()
                                if hasattr(self.parent_app, 'load_llm_settings') else {})
                for profile in (llm_settings.get('custom_mt_profiles') or []):
                    if not profile.get('enabled', True):
                        continue  # profile hidden from QuickTrans by the user
                    if not (profile.get('endpoint') or '').strip():
                        continue
                    p_name = profile.get('name') or 'Custom MT'

                    def make_custom_mt_caller(prof):
                        return lambda text, src, tgt: self.parent_app.call_custom_mt(text, src, tgt, prof)

                    providers.append((p_name, "CMT", make_custom_mt_caller(profile)))

        # Add LLM providers if enabled
        if include_llms:
            self._add_llm_providers(providers, api_keys, mt_quick_settings)

        return providers

    def _add_llm_providers(self, providers: List, api_keys: Dict, mt_quick_settings: Dict):
        """Add LLM providers to the providers list.

        Batch #9.3/#9.4: облачные LLM (Claude/OpenAI/Gemini/Mistral/
        DeepSeek/OpenRouter) и Ollama удалены из движка и UI — остаётся
        только Custom (активный профиль custom_openai, чип CUS).

        Batch #9.4i (решение Дмитрия 2026-10-14): мастер-чекбокс
        mtql_custom_openai убран — чипы есть всегда; mtql_llm_profiles выбирает
        профили; при пустом списке работает глобальный активный профиль."""

        llm_settings = {}
        if hasattr(self, 'parent_app') and self.parent_app and hasattr(self.parent_app, 'load_llm_settings'):
            try:
                llm_settings = self.parent_app.load_llm_settings() or {}
            except Exception:
                llm_settings = {}
        profiles = llm_settings.get('custom_openai_profiles') or []
        enabled = mt_quick_settings.get('mtql_llm_profiles')
        _added = 0

        def make_llm_caller(provider_model, profile_name):
            def call_llm(text, src_lang, tgt_lang):
                return self._call_llm_translation('custom_openai', text, src_lang, tgt_lang,
                                                 provider_model, profile_name)
            return call_llm

        for prof in profiles:
            pname = prof.get('name')
            if not pname:
                continue
            if not (prof.get('endpoint') or '').strip():
                continue
            if enabled is not None and pname not in enabled:
                continue
            providers.append((pname, "CUS",
                              make_llm_caller((prof.get('model') or '').strip(), pname)))
            _added += 1

        if _added == 0:
            # Batch #9.4h/#9.4i (решение Дмитрия 2026-10-13/14): когда в QuickTrans
            # сняты/удалены ВСЕ профили (или список устарел, или профилей нет вовсе),
            # попап работает с глобальным активным профилем из AI Settings как с
            # единственно оставшимся чипом. _get_active_custom_profile разрешает
            # активный по имени -> первый профиль -> легаси-плоский endpoint.
            active = None
            if hasattr(self, 'parent_app') and self.parent_app and hasattr(self.parent_app, '_get_active_custom_profile'):
                try:
                    active = self.parent_app._get_active_custom_profile(llm_settings)
                except Exception:
                    active = None
            if active and (active.get('endpoint') or '').strip():
                label = (active.get('name') if active.get('name') else 'Custom')
                providers.append((label, "CUS", make_llm_caller(None, None)))
            # Batch #9.4i: профиль не настроен вовсе — чипов нет, ошибок нет.

    def _call_llm_translation(self, provider: str, text: str, source_lang: str, target_lang: str, model: str = None, profile_name: str = None) -> str:
        """Call LLM for translation"""
        try:
            from modules.llm_clients import LLMClient, load_api_keys

            if hasattr(self, 'parent_app') and self.parent_app and hasattr(self.parent_app, 'load_api_keys'):
                api_keys = self.parent_app.load_api_keys()
            else:
                api_keys = load_api_keys()

            api_key = api_keys.get(provider)

            # Batch #9.3: custom_openai не требует ключа в api_keys.txt
            if not api_key and provider != 'custom_openai':
                return f"[Error: No API key for {provider}]"

            # Reuse main app client wiring when available (supports custom profiles/base_url)
            if hasattr(self, 'parent_app') and self.parent_app and hasattr(self.parent_app, 'create_llm_client'):
                llm_settings = self.parent_app.load_llm_settings() if hasattr(self.parent_app, 'load_llm_settings') else None
                # «Не настроено» (Batch #9.3): без активного профиля Custom с
                # endpoint — вежливая строка чипа вместо сетевой ошибки.
                if hasattr(self.parent_app, '_custom_llm_ready') and                         not self.parent_app._custom_llm_ready(llm_settings):
                    return "[Custom LLM profile is not configured — Settings → AI Settings]"
                resolved_model = model
                if not resolved_model and llm_settings:
                    resolved_model = llm_settings.get(f"{provider}_model")
                client = self.parent_app.create_llm_client(provider, resolved_model, api_keys,
                                                 settings=llm_settings, profile_name=profile_name)
            else:
                base_url = None
                if provider == 'custom_openai':
                    api_key = api_key or 'not-needed'
                client = LLMClient(
                    api_key=api_key,
                    provider=provider,
                    model=model,
                    base_url=base_url
                )

            # Use a strict prompt that forces translation-only output
            prompt = (
                f"Translate the following text from {source_lang} to {target_lang}.\n"
                f"Output ONLY the translation, nothing else. "
                f"No explanations, no alternatives, no notes, no quotation marks.\n\n"
                f"{text}"
            )
            system_prompt = (
                "You are a translation engine. Output only the translated text. "
                "Never add explanations, alternatives, notes, or commentary. "
                "Never wrap the output in quotes. "
                "If the text is already in the target language, output it unchanged."
            )

            result = client.translate(
                text="",
                source_lang=source_lang,
                target_lang=target_lang,
                custom_prompt=prompt,
                system_prompt=system_prompt,
            )

            # Clean up result - remove quotes if present
            if result:
                result = result.strip()
                if (result.startswith('"') and result.endswith('"')) or (result.startswith("'") and result.endswith("'")):
                    result = result[1:-1]
                # Remove any "Translation:" or similar prefixes
                for prefix in ['Translation:', 'translation:', 'Result:', 'Output:']:
                    if result.startswith(prefix):
                        result = result[len(prefix):].strip()

            return result or "[No translation returned]"

        except Exception as e:
            return f"[Error: {str(e)}]"


class _SourceTextEdit(QTextEdit):
    """Editable source box for the QuickTrans popup.

    Two integration points with the popup: while it's focused the popup's
    number/Enter insert-shortcuts must yield (so typing '1' enters a digit, not
    a translation); and Ctrl+Enter re-translates the edited text. Opens without
    grabbing focus (ClickFocus) so 1-9 still work the instant the popup appears.
    """

    def __init__(self, text, on_focus_changed, on_retranslate, parent=None):
        super().__init__(parent)
        self.setPlainText(text or "")
        self._on_focus_changed = on_focus_changed
        self._on_retranslate = on_retranslate
        self.setAcceptRichText(False)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setFixedHeight(56)
        self.setStyleSheet(
            "font-size: 11px; color: #333; border: 1px solid #ddd; border-radius: 4px;"
        )
        self.setToolTip("Edit the source, then press Ctrl+Enter to re-translate")

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._on_focus_changed(True)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._on_focus_changed(False)

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)):
            self._on_retranslate()
            return
        super().keyPressEvent(event)


class MTQuickPopup(QuickTransProviderMixin, QDialog):
    """
    GT4T-style popup showing MT suggestions from all enabled providers

    Usage:
        popup = MTQuickPopup(parent_app, source_text, source_lang, target_lang)
        popup.translation_selected.connect(on_translation_selected)
        popup.show()
    """

    translation_selected = pyqtSignal(str)  # Emitted when user selects a translation

    def __init__(self, parent_app, source_text: str, source_lang: str = None,
                 target_lang: str = None, parent=None, external_mode: bool = False):
        super().__init__(parent)
        self.parent_app = parent_app
        self.source_text = source_text
        self.source_lang = source_lang or getattr(parent_app, 'source_language', 'en')
        self.target_lang = target_lang or getattr(parent_app, 'target_language', 'nl')
        # The project may store codes ('en'/'nl') while the language combos hold
        # full names; normalise so the selector shows the real pair instead of
        # falling back to the first item ('Afrikaans'). Providers take either.
        self.source_lang = _canonical_lang_name(self.source_lang)
        self.target_lang = _canonical_lang_name(self.target_lang)
        self._external_mode = external_mode  # True when invoked from global hotkey

        self.suggestions: List[MTSuggestion] = []
        self.suggestion_items: List[MTSuggestionItem] = []
        self.selected_index = -1
        self.worker = None
        # Q.6: set by closeEvent — every result/complete handler returns early
        # so a response arriving after close never touches the dead UI.
        self._closed = False
        # Guards the language-pair selector's change handler so the initial
        # setCurrentText() during build doesn't trigger a spurious re-fetch.
        self._lang_bar_ready = False

        self.setup_ui()
        self.setup_shortcuts()
        self.start_fetching()

    def setup_ui(self):
        """Setup the popup UI"""
        self.setWindowTitle("⚡ Supervertaler QuickTrans")
        if self._external_mode:
            # External mode (global hotkey): use Tool window type so the
            # Supervertaler taskbar icon doesn't flash when the popup appears.
            # Tool windows don't get their own taskbar entry and don't activate
            # the parent application.
            self.setWindowFlags(
                Qt.WindowType.Tool |
                Qt.WindowType.WindowCloseButtonHint |
                Qt.WindowType.WindowStaysOnTopHint
            )
        else:
            # In-app mode: standard dialog with title bar for resize/move support
            self.setWindowFlags(
                Qt.WindowType.Dialog |
                Qt.WindowType.WindowCloseButtonHint |
                Qt.WindowType.WindowStaysOnTopHint
            )

        # Set size - allow resizing
        self.setMinimumWidth(450)
        self.setMinimumHeight(200)

        # Restore saved size and position or use defaults.
        # P1.6a: geometry lives in <state_root()>/quicktrans.ini (build root),
        # never in the Windows registry. The old HKCU\Software\Supervertaler\
        # MTQuickPopup values are not read and not migrated — the geometry
        # returns to defaults once after the move (coordinator's decision).
        settings = QSettings(str(state_root() / "quicktrans.ini"),
                             QSettings.Format.IniFormat)
        saved_width = settings.value("width", 650, type=int)
        saved_height = settings.value("height", 400, type=int)
        self.resize(saved_width, saved_height)

        # Check if we have a saved position
        self._has_saved_position = settings.contains("x") and settings.contains("y")
        if self._has_saved_position:
            saved_x = settings.value("x", 0, type=int)
            saved_y = settings.value("y", 0, type=int)
            self.move(saved_x, saved_y)

        # Soft light-blue backdrop for the dialog itself, so the 8px frame
        # around the rounded container reads as one calm panel instead of
        # the drab default grey. Scoped to the class name so it styles only
        # this window, never its children (which keep their own styles).
        self.setStyleSheet("MTQuickPopup { background-color: #DCEAF8; }")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # Container with styling. Light-blue fill (matching the dialog) with
        # a soft blue border; the white result cards inside pop against it.
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #DCEAF8;
                border: 1px solid #B9D4F0;
                border-radius: 4px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)

        # The window title bar already shows "Supervertaler QuickTrans", so the
        # action buttons (Run in SuperLookup, settings) sit on the Source row
        # below rather than in a separate header that repeats the title.

        # Shared style for icon-only header buttons. Reused for both
        # the SuperLookup hand-off button and the settings cog so they
        # visually line up.
        _icon_btn_style = """
            QPushButton {
                border: none;
                background: transparent;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 4px;
            }
            QPushButton:focus {
                outline: none;
            }
        """

        # "Run in SuperLookup" hand-off button (v1.10.12, label
        # extended in v1.10.13). When a user runs QuickTrans on a
        # phrase and then thinks "I'd actually like to look this up
        # in my TMs / termbases / web resources too", this button
        # takes them there in one click: closes the popup and opens
        # Workbench's SuperLookup top tab with the same query
        # pre-filled and the search auto-fired. Same plumbing as
        # Ctrl+Alt+L. Icon-plus-label rather than icon-only because
        # the bare 🔍 next to ⚙ wasn't self-explanatory enough –
        # users couldn't tell at a glance what it did.
        superlookup_btn = QPushButton("🔍 Run in SuperLookup")
        superlookup_btn.setFixedHeight(24)
        superlookup_btn.setToolTip("Run this query in SuperLookup")
        superlookup_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-size: 11px;
                padding: 0 8px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 4px;
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        superlookup_btn.clicked.connect(self._send_to_superlookup)

        # Re-translate button: re-run every engine on the (edited) source.
        retranslate_btn = QPushButton("↻ Re-translate")
        retranslate_btn.setFixedHeight(24)
        retranslate_btn.setToolTip("Re-translate the edited source (or press Ctrl+Enter)")
        retranslate_btn.setStyleSheet(superlookup_btn.styleSheet())
        retranslate_btn.clicked.connect(self._retranslate_from_source)

        # Settings button
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(24, 24)
        settings_btn.setToolTip("Configure QuickTrans providers")
        settings_btn.setStyleSheet(_icon_btn_style)
        settings_btn.clicked.connect(self._open_settings)

        # Source text display
        source_frame = QFrame()
        source_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #B9D4F0;
                border-radius: 4px;
            }
        """)
        source_layout = QVBoxLayout(source_frame)
        source_layout.setContentsMargins(8, 6, 8, 6)

        # Source label on the left; the action buttons (Run in SuperLookup,
        # settings) on the right of the same row.
        source_header_row = QHBoxLayout()
        source_header_row.setContentsMargins(0, 0, 0, 0)
        source_header_row.setSpacing(4)
        source_header = QLabel("Source:")
        source_header.setStyleSheet("font-size: 9px; color: #666; font-weight: bold;")
        source_header_row.addWidget(source_header, 0, Qt.AlignmentFlag.AlignVCenter)
        source_header_row.addStretch()
        source_header_row.addWidget(retranslate_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        source_header_row.addWidget(superlookup_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        source_header_row.addWidget(settings_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        source_layout.addLayout(source_header_row)

        # Editable source: tweak the text and press Ctrl+Enter to re-translate.
        self.source_edit = _SourceTextEdit(
            self.source_text,
            on_focus_changed=lambda focused: self._set_insert_shortcuts_enabled(not focused),
            on_retranslate=self._retranslate_from_source,
        )
        source_layout.addWidget(self.source_edit)

        container_layout.addWidget(source_frame)

        # Language-pair selector. Pre-set to the (possibly auto-detected)
        # direction this popup was opened with; changing it re-fetches in the
        # new direction and makes that pair sticky for subsequent QuickTrans
        # popups (see _on_lang_pair_changed → parent_app override).
        container_layout.addWidget(self._build_lang_bar())

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #B9D4F0;")
        sep.setFixedHeight(1)
        container_layout.addWidget(sep)

        # Suggestions scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.suggestions_container = QWidget()
        self.suggestions_layout = QVBoxLayout(self.suggestions_container)
        self.suggestions_layout.setContentsMargins(0, 0, 0, 0)
        self.suggestions_layout.setSpacing(4)

        # Loading indicator
        self.loading_label = QLabel("⏳ Fetching translations...")
        self.loading_label.setStyleSheet("color: #666; font-size: 11px; padding: 20px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.suggestions_layout.addWidget(self.loading_label)

        self.suggestions_layout.addStretch()

        scroll.setWidget(self.suggestions_container)
        container_layout.addWidget(scroll, 1)

        # Footer with hint
        hint = QLabel("Press 1-9 to insert • ↑↓ to navigate • Enter to insert selected • Esc to close")
        hint.setStyleSheet("font-size: 9px; color: #999; padding-top: 4px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint)

        main_layout.addWidget(container)

        # Position popup near cursor
        self._position_near_cursor()

    def _position_near_cursor(self):
        """Position the popup near the cursor (only if no saved position)"""
        # Skip if we restored a saved position
        if getattr(self, '_has_saved_position', False):
            # Verify saved position is still on a valid screen
            screen = QApplication.screenAt(self.pos())
            if screen:
                return  # Saved position is valid, use it

        # Position near cursor
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if screen:
            screen_geo = screen.availableGeometry()

            # Try to position popup below and to the right of cursor
            x = cursor_pos.x() + 10
            y = cursor_pos.y() + 10

            # Ensure popup stays on screen
            if x + self.width() > screen_geo.right():
                x = cursor_pos.x() - self.width() - 10
            if y + self.height() > screen_geo.bottom():
                y = cursor_pos.y() - self.height() - 10

            # Clamp to screen bounds
            x = max(screen_geo.left(), min(x, screen_geo.right() - self.width()))
            y = max(screen_geo.top(), min(y, screen_geo.bottom() - self.height()))

            self.move(x, y)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # These must yield to the editable source box while it's focused —
        # otherwise typing "1" would insert a translation instead of a digit.
        self._insert_shortcuts = []

        # Number keys 1-9 for quick selection
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(str(i)), self)
            shortcut.activated.connect(lambda idx=i: self._select_by_number(idx))
            self._insert_shortcuts.append(shortcut)

        # Navigation
        up = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        up.activated.connect(self._navigate_up)
        down = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        down.activated.connect(self._navigate_down)
        ret = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        ret.activated.connect(self._insert_selected)
        ent = QShortcut(QKeySequence(Qt.Key.Key_Enter), self)
        ent.activated.connect(self._insert_selected)
        self._insert_shortcuts += [up, down, ret, ent]

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self.close)

    def _set_insert_shortcuts_enabled(self, enabled: bool):
        """Enable/disable the 1-9 / arrow / Enter insert-shortcuts (off while the
        source box is being edited so its keystrokes reach the text)."""
        for sc in getattr(self, '_insert_shortcuts', []):
            sc.setEnabled(enabled)

    def _retranslate_from_source(self):
        """Re-run every engine on the (possibly edited) source text."""
        new_text = self.source_edit.toPlainText().strip()
        if not new_text:
            return
        self.source_text = new_text
        self._reset_and_refetch()

    def _make_section_header(self, text: str) -> QLabel:
        """A lightweight group-header label ('Machine translation' / 'AI / LLM')."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "QLabel { color: #888; font-size: 8pt; font-weight: bold; "
            "border: none; padding: 6px 2px 1px 2px; }"
        )
        return lbl

    def _build_lang_bar(self) -> QWidget:
        """Build the source → target language-pair selector shown under the
        source text. Lets the user correct a wrong auto-detected direction in
        place; the choice re-fetches and sticks for later popups."""
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(6)

        lbl = QLabel("Languages:")
        lbl.setStyleSheet("font-size: 9px; color: #666; font-weight: bold; border: none;")
        row.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        combo_style = (
            "QComboBox { font-size: 10px; padding: 1px 4px; border: 1px solid #cfcfcf; "
            "border-radius: 3px; background: white; }"
        )

        self.src_combo = QComboBox()
        self.src_combo.addItems(AVAILABLE_LANGUAGES)
        self.src_combo.setFixedHeight(22)
        self.src_combo.setMaximumWidth(160)
        self.src_combo.setStyleSheet(combo_style)
        self.src_combo.setToolTip("Source language – what the selected text is in")

        arrow = QLabel("→")
        arrow.setStyleSheet("font-size: 12px; color: #888; border: none;")

        self.tgt_combo = QComboBox()
        self.tgt_combo.addItems(AVAILABLE_LANGUAGES)
        self.tgt_combo.setFixedHeight(22)
        self.tgt_combo.setMaximumWidth(160)
        self.tgt_combo.setStyleSheet(combo_style)
        self.tgt_combo.setToolTip("Target language – what to translate into")

        # Pre-select the direction the popup opened with. setCurrentText is a
        # no-op for an unknown value (e.g. a raw 'en' code), which only leaves
        # the first item selected – names are the normal case from callers.
        self.src_combo.setCurrentText(self.source_lang)
        self.tgt_combo.setCurrentText(self.target_lang)

        swap_btn = QPushButton("⇄")
        swap_btn.setFixedSize(22, 22)
        swap_btn.setToolTip("Swap source and target languages")
        swap_btn.setStyleSheet(
            "QPushButton { border: 1px solid #cfcfcf; border-radius: 3px; background: white; "
            "font-size: 12px; } QPushButton:hover { background-color: #e0e0e0; }"
        )
        swap_btn.clicked.connect(self._on_swap_langs)

        row.addWidget(self.src_combo, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(arrow, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.tgt_combo, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(swap_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch()

        # Connect after the initial setCurrentText so building the bar doesn't
        # fire the change handler.
        self.src_combo.currentTextChanged.connect(self._on_lang_pair_changed)
        self.tgt_combo.currentTextChanged.connect(self._on_lang_pair_changed)
        self._lang_bar_ready = True
        return bar

    def _on_swap_langs(self):
        """Swap the two combos and re-fetch once (not twice for the two
        currentTextChanged signals the swap would otherwise emit)."""
        s = self.src_combo.currentText()
        t = self.tgt_combo.currentText()
        self._lang_bar_ready = False
        self.src_combo.setCurrentText(t)
        self.tgt_combo.setCurrentText(s)
        self._lang_bar_ready = True
        self._on_lang_pair_changed()

    def _on_lang_pair_changed(self, *_):
        """A combo changed: adopt the new direction, persist it as the sticky
        QuickTrans override on the main app, and re-fetch."""
        if not getattr(self, '_lang_bar_ready', False):
            return
        new_src = self.src_combo.currentText()
        new_tgt = self.tgt_combo.currentText()
        if not new_src or not new_tgt:
            return
        if new_src == self.source_lang and new_tgt == self.target_lang:
            return
        self.source_lang = new_src
        self.target_lang = new_tgt
        # Make the pick sticky: subsequent popups reuse it (until the project /
        # default pair is changed elsewhere). Best-effort – the popup still
        # works for this one fetch even if the host doesn't expose the hook.
        try:
            if self.parent_app and hasattr(self.parent_app, 'set_quicktrans_direction_override'):
                self.parent_app.set_quicktrans_direction_override(new_src, new_tgt)
        except Exception:
            pass
        self._reset_and_refetch()

    def _clear_suggestions(self):
        """Tear down all result rows / section headers, keeping the loading
        label and trailing stretch so the layout can be repopulated."""
        layout = self.suggestions_layout
        for i in reversed(range(layout.count())):
            w = layout.itemAt(i).widget()
            if w is None or w is self.loading_label:
                continue  # keep the trailing stretch and the loading label
            w.setParent(None)
            w.deleteLater()
        self.suggestions = []
        self.suggestion_items = []
        self.selected_index = -1
        self._mt_header = None
        self._ai_header = None
        self.loading_label.setText("⏳ Fetching translations...")
        self.loading_label.show()

    def _reset_and_refetch(self):
        """Stop any in-flight workers, clear results, and fetch again in the
        current (just-changed) direction."""
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)
        self.worker = None
        for w in list(getattr(self, '_fetch_workers', []) or []):
            if w.isRunning():
                w.wait(500)
        self._fetch_workers = []
        self._clear_suggestions()
        self.start_fetching()

    def start_fetching(self):
        """Start fetching translations from all enabled providers.

        MT engines always auto-fetch. AI/LLM providers either auto-fetch too or
        appear as on-demand 'Fetch' buttons, controlled by the
        'mtql_popup_ai_autofetch' setting (default on) so the popup doesn't make
        billable AI calls automatically when the user doesn't want it to.
        """
        providers = self._get_enabled_providers()

        if not providers:
            self.loading_label.setText("⚠️ No MT providers configured. Check Settings → MT Settings.")
            return

        mt_providers = [p for p in providers if not _is_ai_code(p[1])]
        ai_providers = [p for p in providers if _is_ai_code(p[1])]

        autofetch_ai = True
        try:
            autofetch_ai = bool(self._load_mt_quick_settings().get('mtql_popup_ai_autofetch', True))
        except Exception:
            pass

        # Pre-create group headers: Machine translation (top), AI / LLM (below).
        # Results stream in arrival order but are routed into the right section in
        # _on_result_ready; _on_all_complete then renumbers top-to-bottom.
        self._mt_header = None
        self._ai_header = None
        if mt_providers:
            self._mt_header = self._make_section_header("⚡  Machine translation")
            self.suggestions_layout.insertWidget(self.suggestions_layout.count() - 1, self._mt_header)
        if ai_providers:
            ai_label = "\U0001F916  AI / LLM" if autofetch_ai else "\U0001F916  AI / LLM  ·  click to fetch"
            self._ai_header = self._make_section_header(ai_label)
            self.suggestions_layout.insertWidget(self.suggestions_layout.count() - 1, self._ai_header)

        # AI as on-demand fetch rows (below the AI header) when not auto-fetching.
        if ai_providers and not autofetch_ai:
            for name, code, call_func in ai_providers:
                self._make_fetch_row(name, code, call_func)

        auto_providers = mt_providers + (ai_providers if autofetch_ai else [])
        if not auto_providers:
            # Only AI providers and they're in fetch mode – nothing to auto-fetch.
            self.loading_label.hide()
            return

        self.worker = MTFetchWorker(
            self.source_text,
            self.source_lang,
            self.target_lang,
            auto_providers,
            self
        )
        self.worker.result_ready.connect(self._on_result_ready)
        self.worker.all_complete.connect(self._on_all_complete)
        self.worker.start()

    def _make_fetch_row(self, name, code, call_func):
        """Add an on-demand 'Fetch' row for an AI provider in the popup. Clicking
        it fetches that one provider and replaces the row with the result."""
        from PyQt6.QtWidgets import QPushButton
        row = QFrame()
        row.setStyleSheet("QFrame { background: #fafafa; border: 1px dashed #cfcfcf; border-radius: 4px; }")
        h = QHBoxLayout(row)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(8)

        chip = QLabel(name)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        bg = PROVIDER_COLORS.get(code, "#666")
        chip.setStyleSheet(f"QLabel {{ background-color: {bg}; color: white; font-weight: 600; "
                           f"font-size: 9px; border-radius: 9px; padding: 1px 8px; }}")
        h.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)

        hint = QLabel("AI – click to fetch")
        hint.setStyleSheet("color: #999; font-size: 9pt; border: none;")
        h.addWidget(hint)
        h.addStretch()

        btn = QPushButton("Fetch")
        btn.setFixedHeight(22)
        btn.setToolTip(f"Fetch an AI translation from {name} (makes one API call)")
        h.addWidget(btn)

        self.suggestions_layout.insertWidget(self.suggestions_layout.count() - 1, row)

        if not hasattr(self, '_fetch_workers'):
            self._fetch_workers = []

        def on_click():
            btn.setEnabled(False)
            btn.setText("…")
            worker = MTFetchWorker(self.source_text, self.source_lang, self.target_lang,
                                   [(name, code, call_func)])
            self._fetch_workers.append(worker)

            def on_ready(pn, pc, tr, err, lo=False):
                if self._closed:
                    return  # Q.6: response after close is dropped
                if self.loading_label.isVisible():
                    self.loading_label.hide()
                idx = self.suggestions_layout.indexOf(row)
                if idx < 0:
                    idx = self.suggestions_layout.count() - 1
                suggestion = MTSuggestion(pn, pc, tr, err, link_only=lo)
                item = MTSuggestionItem(0, suggestion)  # number assigned by renumber
                item.clicked.connect(self._on_item_clicked)
                self.suggestions_layout.insertWidget(idx, item)
                row.setParent(None)
                row.deleteLater()
                self._renumber_grouped()

            def on_done(_w=worker):
                if _w in self._fetch_workers:
                    self._fetch_workers.remove(_w)

            worker.result_ready.connect(on_ready)
            worker.all_complete.connect(on_done)
            worker.start()

        btn.clicked.connect(on_click)

    def _send_to_superlookup(self):
        """Close the popup and open Workbench's SuperLookup tab with
        the current QuickTrans query pre-filled.

        Wired to the 🔍 button in the popup header. Same plumbing as
        the Ctrl+Alt+L global hotkey – `open_workbench_to_superlookup`
        on the main window does the lazy-tab ensure, foreground
        hammer chain, text seeding, and deferred search-button click.

        Deferred via QTimer.singleShot(0) for the same reason as
        `_open_settings`: the popup's close() events need a Qt
        event-loop turn to fully unwind before the foreground
        transition starts, otherwise the hammer chain can race
        against still-queued popup destruction events and leave
        Workbench painted behind the source app.
        """
        query = (self.source_text or "").strip()
        if not query:
            return
        if not (self.parent_app and hasattr(self.parent_app, 'open_workbench_to_superlookup')):
            return
        self.close()
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(
                0,
                lambda: self.parent_app.open_workbench_to_superlookup(query),
            )
        except Exception:
            # Synchronous fallback – the v1.10.9 hammer chain inside
            # open_workbench_to_superlookup is robust enough to win
            # the foreground race most of the time without the defer.
            self.parent_app.open_workbench_to_superlookup(query)

    def _open_settings(self):
        """Open Workbench Settings → ⚡ QuickTrans.

        v1.10.11: defer the parent-app call via QTimer.singleShot(0)
        so the popup's close() has a Qt event-loop turn to fully
        unwind before _bring_workbench_forward() fires. Without the
        defer, the foreground-grab hammer chain races against the
        popup-destruction events still queued in our own process,
        which can leave Workbench painted behind whichever app
        actually owns the OS-level foreground (typically Trados,
        since QuickTrans is most often summoned from there).
        """
        if self.parent_app and hasattr(self.parent_app, 'open_mt_quick_lookup_settings'):
            self.close()  # Close popup first (sync, but events queue)
            try:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(
                    0, self.parent_app.open_mt_quick_lookup_settings
                )
            except Exception:
                # If QTimer import fails (extremely unlikely), fall
                # back to the synchronous path – the v1.10.11 hammer
                # chain inside open_mt_quick_lookup_settings is
                # robust enough to win the foreground race most of
                # the time even without the defer.
                self.parent_app.open_mt_quick_lookup_settings()

    def _on_result_ready(self, provider_name: str, provider_code: str, translation: str,
                         is_error: bool, link_only: bool = False):
        """Handle a single MT result"""
        if self._closed:
            return  # Q.6: response after close is dropped
        # Hide loading label on first result
        if self.loading_label.isVisible():
            self.loading_label.hide()

        # Create suggestion
        suggestion = MTSuggestion(
            provider_name=provider_name,
            provider_code=provider_code,
            translation=translation,
            is_error=is_error,
            link_only=link_only
        )
        self.suggestions.append(suggestion)

        # Create and add item widget
        item = MTSuggestionItem(len(self.suggestions), suggestion)
        item.clicked.connect(self._on_item_clicked)
        self.suggestion_items.append(item)

        # Route into the right group: MT rows go above the AI / LLM header so MT
        # stays grouped at the top; AI rows (and the no-grouping case) go before
        # the trailing stretch.
        ai_header = getattr(self, '_ai_header', None)
        if (not _is_ai_code(provider_code)
                and ai_header is not None
                and self.suggestions_layout.indexOf(ai_header) >= 0):
            idx = self.suggestions_layout.indexOf(ai_header)
        else:
            idx = self.suggestions_layout.count() - 1
        self.suggestions_layout.insertWidget(idx, item)

        # Auto-select first non-error result (corrected after regrouping).
        if self.selected_index == -1 and not is_error:
            self._select_index(len(self.suggestion_items) - 1)

    def _on_all_complete(self):
        """Handle completion of all MT fetches"""
        if self._closed:
            return  # Q.6: completion after close is dropped
        if not self.suggestions:
            self.loading_label.setText("⚠️ No translations available.")
            self.loading_label.show()
            return
        # Results streamed in arrival order; renumber them top-to-bottom so the
        # pick-numbers (1-9) match the grouped MT-then-AI visual order.
        self._renumber_grouped()
        # Don't call adjustSize() - it shrinks the window and loses user's preferred size

    def _renumber_grouped(self):
        """Walk the (already grouped) layout top to bottom, assign sequential
        pick-numbers, and rebuild the parallel lists so number-key selection and
        index-based selection stay correct."""
        new_suggestions = []
        new_items = []
        n = 0
        for i in range(self.suggestions_layout.count()):
            w = self.suggestions_layout.itemAt(i).widget()
            if isinstance(w, MTSuggestionItem):
                n += 1
                w.set_number(n)
                w.deselect()
                new_items.append(w)
                new_suggestions.append(w.suggestion)
        self.suggestions = new_suggestions
        self.suggestion_items = new_items
        # Re-select the first non-error row in the new order.
        self.selected_index = -1
        for idx, it in enumerate(new_items):
            if not it.suggestion.is_error:
                self._select_index(idx)
                break

    def _on_item_clicked(self, translation: str):
        """Handle click on a suggestion item"""
        self.translation_selected.emit(translation)
        self.close()

    def _select_by_number(self, number: int):
        """Select suggestion by number (1-based)"""
        idx = number - 1
        if 0 <= idx < len(self.suggestion_items):
            suggestion = self.suggestions[idx]
            if not suggestion.is_error:
                self.translation_selected.emit(suggestion.translation)
                self.close()

    def _select_index(self, index: int):
        """Select suggestion by index"""
        # Deselect previous
        if 0 <= self.selected_index < len(self.suggestion_items):
            self.suggestion_items[self.selected_index].deselect()

        # Select new (skip errors)
        if 0 <= index < len(self.suggestion_items):
            self.selected_index = index
            self.suggestion_items[index].select()
            # Ensure visible
            self.suggestion_items[index].setFocus()

    def _navigate_up(self):
        """Navigate to previous suggestion"""
        if not self.suggestion_items:
            return

        new_idx = self.selected_index - 1
        while new_idx >= 0:
            if not self.suggestions[new_idx].is_error:
                self._select_index(new_idx)
                return
            new_idx -= 1

    def _navigate_down(self):
        """Navigate to next suggestion"""
        if not self.suggestion_items:
            return

        new_idx = self.selected_index + 1
        while new_idx < len(self.suggestions):
            if not self.suggestions[new_idx].is_error:
                self._select_index(new_idx)
                return
            new_idx += 1

    def _insert_selected(self):
        """Insert the currently selected suggestion"""
        if 0 <= self.selected_index < len(self.suggestions):
            suggestion = self.suggestions[self.selected_index]
            if not suggestion.is_error:
                self.translation_selected.emit(suggestion.translation)
                self.close()

    def closeEvent(self, event):
        """Q.6: cooperative cancel on close — mark closed, detach in-flight
        workers, save window geometry. The network request is NOT aborted: it
        lives until the server answers or times out; the detached QThread is
        parked in _DETACHED_WORKERS, its late result dropped (handlers
        disconnected + ``_closed`` guard), and it is garbage-collected once
        finished — no dangling threads, no post-close UI writes."""
        self._closed = True
        if self.worker is not None:
            if self.worker.isRunning():
                _detach_worker_for_close(self.worker)
            self.worker = None
        for w in list(getattr(self, '_fetch_workers', []) or []):
            if w.isRunning():
                _detach_worker_for_close(w)
        self._fetch_workers = []

        # Save window size and position for next time (P1.6a: same
        # <state_root()>/quicktrans.ini as setup_ui, not the registry)
        settings = QSettings(str(state_root() / "quicktrans.ini"),
                             QSettings.Format.IniFormat)
        settings.setValue("width", self.width())
        settings.setValue("height", self.height())
        settings.setValue("x", self.x())
        settings.setValue("y", self.y())
        super().closeEvent(event)


class QuickTransPanel(QuickTransProviderMixin, QWidget):
    """Docked QuickTrans panel for the under-grid tab area.

    A trimmed, always-on version of the QuickTrans popup. Q.3: it sends NO
    automatic requests — on every segment change each enabled provider (MT
    engines and LLMs alike) gets an on-demand "Fetch" row, and each block
    header ("Machine translation", "AI / LLM") carries a "Fetch all" button.
    A request leaves the panel only when the user presses a row's Fetch
    button (or Fetch all). Link-only segments (Q.2) show the source verbatim
    in every row immediately, with no network at all. Q.4: each result row
    is an editable field with a Paste button — clicking a row only places
    the cursor in its field; insertion goes through Paste or Ctrl+1..9, both
    reading the field's current (possibly edited) text.

    A Fetch result is bound to the segment it was requested for: the next
    segment change bumps ``_fetch_token`` and rebuilds the rows in their
    initial "press Fetch" state, so a late answer from the previous segment
    is dropped (the request itself is never aborted, as in Q.6 — it lives
    until the server answers or times out).

    The host wires it up by:
        panel = QuickTransPanel(main_window)
        panel.translation_selected.connect(insert_fn)
        # on every segment change:
        panel.request_update(source_text, source_lang, target_lang)
    """

    translation_selected = pyqtSignal(str)

    def __init__(self, parent_app, parent=None):
        super().__init__(parent)
        self.parent_app = parent_app
        self.source_lang = getattr(parent_app, 'source_language', 'en')
        self.target_lang = getattr(parent_app, 'target_language', 'nl')

        self._pending: Optional[Tuple[str, str, str]] = None  # (source, src, tgt)
        self._last_fetched: Optional[str] = None              # source actually fetched
        self._fetch_token: int = 0          # bumped each fetch; stale workers are ignored
        self._workers: List[MTFetchWorker] = []   # keep refs so threads aren't GC'd mid-run
        self.suggestions: List[MTSuggestion] = []
        self._rows: List[PanelResultRow] = []     # result rows in visual order (Q.4)
        # Q.3: (row, fetch-button) pairs of the current segment's still-unfetched
        # rows, per block — what the block-header "Fetch all" button fires.
        self._mt_fetch_rows: List[Tuple[QFrame, QPushButton]] = []
        self._ai_fetch_rows: List[Tuple[QFrame, QPushButton]] = []
        # Q.6: set by closeEvent — late worker results are dropped, not written
        # into the closed panel's UI.
        self._closed = False

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._do_fetch)

        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 6)
        outer.setSpacing(4)

        # Header: just the action buttons, right-aligned. No title label –
        # the tab is already named "QuickTrans".
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(2)
        header.addStretch()

        self._refresh_btn = QPushButton("🔄")
        self._refresh_btn.setFixedSize(22, 22)
        self._refresh_btn.setToolTip(
            "Reset QuickTrans rows for the current segment (clears results; no requests are sent)")
        self._refresh_btn.setStyleSheet(_PANEL_ICON_BTN_STYLE)
        self._refresh_btn.clicked.connect(self._force_refresh)
        header.addWidget(self._refresh_btn)

        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(22, 22)
        settings_btn.setToolTip("Configure QuickTrans providers")
        settings_btn.setStyleSheet(_PANEL_ICON_BTN_STYLE)
        settings_btn.clicked.connect(self._open_settings)
        header.addWidget(settings_btn)
        outer.addLayout(header)

        # Persistent status / placeholder line. Lives in the OUTER layout, not
        # inside results_layout – _clear_results() wipes the results layout, so
        # keeping the label out of it avoids deleting the very widget we reuse.
        self.status_label = QLabel("Select a segment to see translations.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #888; font-size: 9pt; padding: 6px;")
        outer.addWidget(self.status_label)

        # Scrollable list of result rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self.results_layout = QVBoxLayout(container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(4)
        self.results_layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

    def _open_settings(self):
        if self.parent_app and hasattr(self.parent_app, 'open_mt_quick_lookup_settings'):
            self.parent_app.open_mt_quick_lookup_settings()

    # ── update lifecycle ────────────────────────────────────────────────
    def request_update(self, source_text: str, source_lang: str = None, target_lang: str = None):
        """Called by the host on every segment change. Stores the pending
        segment and (if the panel is visible) schedules a debounced rebuild
        of the rows. Q.3: the rebuild is local only — selecting a segment
        never sends a network request; requests leave solely via the rows'
        Fetch buttons."""
        source_text = (source_text or "").strip()
        if source_lang:
            self.source_lang = source_lang
        if target_lang:
            self.target_lang = target_lang
        self._pending = (source_text, self.source_lang, self.target_lang)
        if self.isVisible() and source_text and source_text != self._last_fetched:
            self._debounce.start()

    def showEvent(self, event):
        """When the tab becomes visible, rebuild the rows for the pending
        segment (the panel doesn't rebuild while hidden; no network either
        way — Fetch is manual since Q.3)."""
        super().showEvent(event)
        if self._pending and self._pending[0] and self._pending[0] != self._last_fetched:
            self._debounce.start()

    def _force_refresh(self):
        """Manual ↻: rebuild the current segment's rows from scratch — any
        fetched results are discarded and every row returns to its initial
        'press Fetch' state (the providers list is re-read, so a settings
        change shows up here too)."""
        self._last_fetched = None
        if self._pending and self._pending[0]:
            self._do_fetch()

    # ── rendering ───────────────────────────────────────────────────────
    def _make_section_header(self, text: str) -> QLabel:
        """A lightweight group-header label ('Machine translation' / 'AI / LLM')."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "QLabel { color: #888; font-size: 8pt; font-weight: bold; "
            "border: none; padding: 6px 2px 1px 2px; }"
        )
        return lbl

    def _make_section_header_with_fetch(self, text: str, on_fetch_all) -> QWidget:
        """Group-header row carrying the block's 'Fetch all' button (Q.3):
        one press fires every still-unfetched row of the block (in-flight
        rows are skipped — their Fetch button is disabled while running)."""
        bar = QWidget()
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        h.addWidget(self._make_section_header(text))
        h.addStretch()
        btn = QPushButton("Fetch all")
        btn.setFixedHeight(18)
        btn.setStyleSheet(
            "QPushButton { color: #666; font-size: 8pt; border: none; "
            "padding: 0 4px; }"
            "QPushButton:hover { color: #2196F3; }"
        )
        btn.setToolTip("Fetch every row of this block (one request per provider)")
        btn.clicked.connect(on_fetch_all)
        h.addWidget(btn)
        return bar

    def _clear_results(self):
        # Remove every widget except the trailing stretch (last item).
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.suggestions = []
        self._rows = []
        # Section-header anchors and fetch-row bookkeeping are recreated per
        # rebuild (see _do_fetch).
        self._mt_header = None
        self._ai_header = None
        self._mt_fetch_rows = []
        self._ai_fetch_rows = []

    def _do_fetch(self):
        """Rebuild the panel for the pending segment (Q.3): every enabled
        provider — MT engines and LLMs alike — gets an on-demand Fetch row.
        NO automatic network request is made; the panel only calls out when
        the user presses a row's Fetch button or a block's Fetch all. The
        token bump drops any still-running worker's late result from the
        previous segment (the request itself lives on, Q.6)."""
        if self._closed:
            return  # Q.6: no new fetches on a closed panel
        if not self._pending:
            return
        source_text, src, tgt = self._pending
        if not source_text:
            return
        self._last_fetched = source_text
        self._clear_results()

        # Bump the token so any still-running worker from a previous segment
        # has its (late) results ignored rather than appended to this one.
        # (Fetch rows capture the current generation when their button is
        # pressed — see _add_fetch_row.)
        self._fetch_token += 1

        mt_providers = self._get_enabled_providers(include_mt=True, include_llms=False)
        llm_providers = self._get_enabled_providers(include_mt=False, include_llms=True)

        if not mt_providers and not llm_providers:
            self.status_label.setText("⚠️ No QuickTrans providers enabled. Click ⚙ to configure.")
            self._show_status()
            return

        self._hide_status()

        # Group headers: Machine translation first, then AI / LLM. MT rows are
        # inserted above the AI header; LLM rows below it (see _add_fetch_row
        # and _append_result). A header is only shown if its section has providers.
        self._mt_header = None
        self._ai_header = None

        # Q.2/Q.3: link-only segment — every enabled profile's row carries the
        # source verbatim plus the skip note immediately: no Fetch buttons, no
        # network (the gate is free and reads the text only).
        if _is_link_only_text(source_text):
            if mt_providers:
                self._mt_header = self._make_section_header("⚡  Machine translation")
                self.results_layout.insertWidget(self.results_layout.count() - 1, self._mt_header)
            if llm_providers:
                self._ai_header = self._make_section_header("\U0001F916  AI / LLM  ·  billed per use")
                self.results_layout.insertWidget(self.results_layout.count() - 1, self._ai_header)
            for name, code, _call in mt_providers + llm_providers:
                self._append_result(name, code, source_text, False, True)
            return

        if mt_providers:
            self._mt_header = self._make_section_header_with_fetch(
                "⚡  Machine translation", self._fetch_all_mt)
            self.results_layout.insertWidget(self.results_layout.count() - 1, self._mt_header)
        if llm_providers:
            self._ai_header = self._make_section_header_with_fetch(
                "\U0001F916  AI / LLM  ·  billed per use", self._fetch_all_ai)
            self.results_layout.insertWidget(self.results_layout.count() - 1, self._ai_header)

        # One on-demand Fetch row per provider — MT and AI alike.
        for name, code, call_func in mt_providers:
            self._add_fetch_row(name, code, call_func, source_text, src, tgt, 'mt')
        for name, code, call_func in llm_providers:
            self._add_fetch_row(name, code, call_func, source_text, src, tgt, 'ai')

    def _start_worker(self, source_text, src, tgt, providers, on_ready, token, on_complete=None):
        """Start an MTFetchWorker, tracking it so it isn't GC'd mid-run and
        dropping its results if a newer fetch has superseded this one."""
        worker = MTFetchWorker(source_text, src, tgt, providers)
        self._workers.append(worker)

        def _ready(pn, pc, tr, err, lo=False, _tok=token):
            if self._closed or _tok != self._fetch_token:
                return  # Q.6 / stale-token: result is dropped
            on_ready(pn, pc, tr, err, lo)

        def _done(_w=worker, _tok=token):
            if not self._closed and on_complete is not None and _tok == self._fetch_token:
                on_complete()
            if _w in self._workers:
                self._workers.remove(_w)

        worker.result_ready.connect(_ready)
        worker.all_complete.connect(_done)
        worker.start()
        return worker

    def _show_status(self):
        self.status_label.show()

    def _hide_status(self):
        self.status_label.hide()

    def _renumber_rows(self):
        """Keep pick-numbers (and self.suggestions / self._rows) in
        top-to-bottom visual order so Ctrl+1..9 always inserts the numbered
        row the user sees. Q.3 made every provider on-demand, so result rows
        now resolve in arbitrary arrival order — re-walk the layout after
        each insertion."""
        items = []
        for i in range(self.results_layout.count()):
            w = self.results_layout.itemAt(i).widget()
            if isinstance(w, PanelResultRow):
                items.append(w)
        self.suggestions = [w.suggestion for w in items]
        self._rows = items
        for n, w in enumerate(items, 1):
            w.set_number(n)

    def _append_result(self, name, code, translation, is_error, link_only=False,
                       at_index=None) -> 'PanelResultRow':
        """Append a result row (Q.4: an editable PanelResultRow). Default
        placement follows the block routing (MT above the AI header, AI below
        it); ``at_index`` pins the row to a specific position (used when a
        Fetch row is replaced by its result)."""
        # Q.4: bracketed notice strings ('[MT proxy …]', '[Custom MT …]', …)
        # are error rows in the panel even where the worker's is_error flag
        # doesn't cover them — no Paste, no Ctrl+N (see _is_panel_error_text).
        row_error = is_error or _is_panel_error_text(translation)
        suggestion = MTSuggestion(name, code, translation, row_error, link_only=link_only)
        self.suggestions.append(suggestion)
        item = PanelResultRow(len(self.suggestions), suggestion)
        # Q.4: Paste emits through the panel's existing translation_selected
        # path (the host's _insert_quicktrans_translation) — nothing new is
        # added to the target-write chain.
        item.paste_requested.connect(self.translation_selected)
        if at_index is not None:
            idx = at_index
        else:
            # MT rows live above the AI / LLM header so MT stays grouped at
            # the top; fall back to before the trailing stretch when there is
            # no AI section.
            ai_header = getattr(self, '_ai_header', None)
            if (not _is_ai_code(code)
                    and ai_header is not None
                    and self.results_layout.indexOf(ai_header) >= 0):
                idx = self.results_layout.indexOf(ai_header)
            else:
                idx = self.results_layout.count() - 1
        self.results_layout.insertWidget(idx, item)
        self._renumber_rows()
        return item

    def _fetch_all_mt(self):
        """'Fetch all' of the Machine translation block (Q.3)."""
        for _row, btn in list(self._mt_fetch_rows):
            if btn.isEnabled():
                btn.click()

    def _fetch_all_ai(self):
        """'Fetch all' of the AI / LLM block (Q.3)."""
        for _row, btn in list(self._ai_fetch_rows):
            if btn.isEnabled():
                btn.click()

    def _add_fetch_row(self, name, code, call_func, source_text, src, tgt, block):
        """Add an on-demand 'Fetch' row (Q.3) — one per enabled provider, MT
        and AI alike. Visually and behaviourally identical for both blocks:
        pressing Fetch starts exactly one request for this provider and the
        result replaces the row in place. The worker runs through
        _start_worker, so a segment change (token bump) or panel close (Q.6)
        drops its late result; the request itself is never aborted."""
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: #fafafa; border: 1px dashed #cfcfcf; border-radius: 4px; }"
        )
        h = QHBoxLayout(row)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(8)

        chip = QLabel(name)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Compact pill, matching the result chips (see MTSuggestionItem).
        chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        bg = PROVIDER_COLORS.get(code, "#666")
        chip.setStyleSheet(
            f"QLabel {{ background-color: {bg}; color: white; font-weight: 600; "
            f"font-size: 9px; border-radius: 9px; padding: 1px 8px; }}"
        )
        h.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)

        hint = QLabel("MT – click to fetch" if block == 'mt' else "AI – click to fetch")
        hint.setStyleSheet("color: #999; font-size: 9pt; border: none;")
        h.addWidget(hint)
        h.addStretch()

        btn = QPushButton("Fetch")
        btn.setFixedHeight(22)
        btn.setToolTip(f"Fetch a translation from {name} (makes one API call)")
        h.addWidget(btn)

        # MT rows live above the AI / LLM header so MT stays grouped at the
        # top; AI rows go below it (before the trailing stretch).
        anchor = self._ai_header if block == 'mt' else None
        if anchor is not None and self.results_layout.indexOf(anchor) >= 0:
            idx = self.results_layout.indexOf(anchor)
        else:
            idx = self.results_layout.count() - 1
        self.results_layout.insertWidget(idx, row)

        rows_list = self._mt_fetch_rows if block == 'mt' else self._ai_fetch_rows
        rows_list.append((row, btn))

        def on_click():
            btn.setEnabled(False)
            btn.setText("…")

            def on_ready(pn, pc, tr, err, lo=False):
                try:
                    rows_list.remove((row, btn))
                except ValueError:
                    pass
                idx2 = self.results_layout.indexOf(row)
                if idx2 < 0:
                    idx2 = self.results_layout.count() - 1
                self._append_result(pn, pc, tr, err, link_only=lo, at_index=idx2)
                row.setParent(None)
                row.deleteLater()

            self._start_worker(source_text, src, tgt, [(name, code, call_func)],
                               on_ready=on_ready, token=self._fetch_token)

        btn.clicked.connect(on_click)

    def insert_match_by_number(self, number: int) -> bool:
        """Insert the Nth currently-displayed QuickTrans row into the target.

        N is 1-based and matches the pick-number shown on each row. Q.4: the
        inserted text is the row field's CURRENT content (user edits
        included), not the original provider answer. Error rows are skipped,
        so an error message can never reach the target cell. Returns True if
        a (non-error) row existed and was emitted for insertion, else False
        so the caller can fall back to another panel.
        """
        idx = number - 1
        if 0 <= idx < len(self._rows):
            row = self._rows[idx]
            if not row.suggestion.is_error:
                text = row.current_text()
                if text:
                    self.translation_selected.emit(text)
                    return True
        return False

    def closeEvent(self, event):
        # Q.6: cooperative cancel on close — mark closed and detach in-flight
        # workers (no abort: each request lives until the server answers or
        # times out; the QThread is parked in _DETACHED_WORKERS and released
        # when finished, so no thread is destroyed while running and no late
        # result reaches this panel's UI).
        self._closed = True
        for w in list(self._workers):
            if w.isRunning():
                _detach_worker_for_close(w)
        self._workers = []
        super().closeEvent(event)
