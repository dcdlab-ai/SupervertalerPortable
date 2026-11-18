"""
Translation Memory Manager for Supervertaler Qt
Provides comprehensive TM management features:
- Browse all TM entries
- Concordance search
- Import/Export TMX files
- Delete entries
- View statistics
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QTableWidget, QTableWidgetItem, QLineEdit, QPushButton,
                              QLabel, QMessageBox, QFileDialog, QHeaderView,
                              QGroupBox, QTextEdit, QComboBox, QSpinBox,
                              QProgressBar, QProgressDialog, QWidget, QStyle,
                              QStyledItemDelegate, QApplication,
                              QStyleOptionViewItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QRectF, QTimer
from PyQt6.QtGui import (QColor, QFont, QPalette, QTextDocument,
                         QAbstractTextDocumentLayout, QKeySequence)
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable

from modules.styled_widgets import CheckmarkCheckBox


class TMXImportThread(QThread):
    """Background thread for importing TMX files"""
    progress = pyqtSignal(int, str)  # progress percentage, status message
    finished = pyqtSignal(bool, str, int)  # success, message, entries_imported
    
    def __init__(self, tmx_path: str, db_manager, source_lang: str, target_lang: str, tm_id: str = 'imported'):
        super().__init__()
        self.tmx_path = tmx_path
        self.db_manager = db_manager
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.tm_id = tm_id
    
    def run(self):
        """Import TMX file in background"""
        try:
            tree = ET.parse(self.tmx_path)
            root = tree.getroot()
            
            # Find body element
            body = root.find('.//body')
            if body is None:
                self.finished.emit(False, "Invalid TMX file: no body element found", 0)
                return
            
            # Get all translation units
            tus = body.findall('tu')
            total = len(tus)
            imported = 0
            
            for idx, tu in enumerate(tus):
                # Extract source and target
                tuvs = tu.findall('tuv')
                if len(tuvs) < 2:
                    continue
                
                source_text = None
                target_text = None
                
                for tuv in tuvs:
                    lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang', 
                                  tuv.get('lang', ''))
                    seg = tuv.find('seg')
                    if seg is None or seg.text is None:
                        continue
                    
                    # Simple language matching (could be improved)
                    if not source_text:
                        source_text = seg.text
                    else:
                        target_text = seg.text
                
                # Add to TM if both source and target found
                if source_text and target_text:
                    self.db_manager.add_translation_unit(
                        source=source_text,
                        target=target_text,
                        source_lang=self.source_lang,
                        target_lang=self.target_lang,
                        tm_id=self.tm_id,
                        save_mode='all'  # Always use 'all' mode for imports
                    )
                    imported += 1
                
                # Update progress every 10 entries
                if idx % 10 == 0:
                    progress_pct = int((idx / total) * 100)
                    self.progress.emit(progress_pct, f"Importing... {idx}/{total}")
            
            self.finished.emit(True, f"Successfully imported {imported} entries", imported)

        except Exception as e:
            self.finished.emit(False, f"Import failed: {str(e)}", 0)


class TMCleanupThread(QThread):
    """Background worker for TM Maintenance cleanup operations.

    Opens its own SQLite connection inside ``run`` so it never touches the
    main-thread connection. WAL mode (set on the database at startup) lets
    this writer coexist with the main thread's readers without locking the
    UI.

    Modes:
      MODE_IDENTICAL_PAIRS   – DELETE rows where source_text == target_text.
      MODE_DUPLICATE_SOURCES – for each duplicated source_hash, keep the row
                               with the most recent modified_date and delete
                               the rest (ties broken by id, deterministic).
    """

    MODE_IDENTICAL_PAIRS = "identical_pairs"
    MODE_DUPLICATE_SOURCES = "duplicate_sources"

    progress = pyqtSignal(int, int, str)        # done, total, status text
    finished = pyqtSignal(bool, str, int, int)  # success, error_msg, deleted, considered

    def __init__(self, db_path: str, mode: str, filter_tm_ids=None):
        super().__init__()
        self.db_path = db_path
        self.mode = mode
        self.filter_tm_ids = list(filter_tm_ids) if filter_tm_ids else None

    def _filter_clause(self, joiner: str):
        """Return ('AND tm_id IN (?,?,?)', [ids…]) or ('', [])."""
        if not self.filter_tm_ids:
            return "", []
        placeholders = ",".join("?" * len(self.filter_tm_ids))
        return f"{joiner} tm_id IN ({placeholders})", list(self.filter_tm_ids)

    def run(self):
        try:
            conn = sqlite3.connect(self.db_path, timeout=60)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            try:
                if self.mode == self.MODE_IDENTICAL_PAIRS:
                    deleted, considered = self._clean_identical_pairs(cursor)
                elif self.mode == self.MODE_DUPLICATE_SOURCES:
                    deleted, considered = self._clean_duplicate_sources(cursor)
                else:
                    raise ValueError(f"Unknown cleanup mode: {self.mode}")
                conn.commit()
                self.finished.emit(True, "", deleted, considered)
            finally:
                conn.close()
        except Exception as e:
            self.finished.emit(False, str(e), 0, 0)

    def _clean_identical_pairs(self, cursor):
        clause, params = self._filter_clause("AND")
        self.progress.emit(0, 0, "Counting identical source/target pairs…")
        cursor.execute(
            f"SELECT COUNT(*) FROM translation_units "
            f"WHERE source_text = target_text {clause}",
            params,
        )
        before = cursor.fetchone()[0]
        if before == 0:
            return 0, 0
        self.progress.emit(0, 0, f"Deleting {before:,} identical pairs…")
        cursor.execute(
            f"DELETE FROM translation_units "
            f"WHERE source_text = target_text {clause}",
            params,
        )
        return before, before

    def _clean_duplicate_sources(self, cursor):
        # Find all duplicated source hashes (one row per group).
        where_clause, where_params = self._filter_clause("WHERE")
        self.progress.emit(0, 0, "Finding duplicate sources…")
        cursor.execute(
            f"""
            SELECT source_hash
            FROM translation_units
            {where_clause}
            GROUP BY source_hash
            HAVING COUNT(*) > 1
            """,
            where_params,
        )
        duplicate_hashes = [r[0] for r in cursor.fetchall()]
        total_groups = len(duplicate_hashes)
        if total_groups == 0:
            return 0, 0

        and_clause, and_params = self._filter_clause("AND")
        total_deleted = 0
        report_every = max(1, total_groups // 200)  # ≈200 progress ticks max

        for idx, source_hash in enumerate(duplicate_hashes, start=1):
            params = [source_hash] + and_params
            cursor.execute(
                f"""
                SELECT id FROM translation_units
                WHERE source_hash = ? {and_clause}
                ORDER BY modified_date DESC, id DESC
                """,
                params,
            )
            ids = [row[0] for row in cursor.fetchall()]
            if len(ids) > 1:
                ids_to_delete = ids[1:]  # keep the newest
                placeholders = ",".join("?" * len(ids_to_delete))
                cursor.execute(
                    f"DELETE FROM translation_units WHERE id IN ({placeholders})",
                    ids_to_delete,
                )
                total_deleted += len(ids_to_delete)
            if idx % report_every == 0 or idx == total_groups:
                self.progress.emit(
                    idx, total_groups,
                    f"Processing duplicate sources… {idx:,} / {total_groups:,} "
                    f"(removed {total_deleted:,} so far)"
                )
        return total_deleted, total_groups


class HighlightDelegate(QStyledItemDelegate):
    """Custom delegate to render HTML with highlighted text in table cells"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_term = ""
    
    def set_search_term(self, term: str):
        """Set the term to highlight"""
        self.search_term = term
    
    def paint(self, painter, option, index):
        """Paint the cell with HTML rendering for highlighting"""
        from PyQt6.QtGui import QTextDocument, QAbstractTextDocumentLayout
        from PyQt6.QtCore import QRectF
        
        # Get the text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            super().paint(painter, option, index)
            return
        
        # Create HTML with highlighting
        if self.search_term:
            import re
            pattern = re.compile(re.escape(self.search_term), re.IGNORECASE)
            html_text = pattern.sub(
                lambda m: f"<span style='background-color: #FFD54F; font-weight: bold;'>{m.group()}</span>",
                text
            )
        else:
            html_text = text
        
        # Setup painter
        painter.save()
        
        # Draw selection background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        
        # Create document for HTML rendering
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(html_text)
        doc.setTextWidth(option.rect.width() - 6)  # Some padding
        
        # Translate to cell position
        painter.translate(option.rect.left() + 3, option.rect.top() + 2)
        
        # Create clip rect
        clip = QRectF(0, 0, option.rect.width() - 6, option.rect.height() - 4)
        
        # Draw the document
        ctx = QAbstractTextDocumentLayout.PaintContext()
        if option.state & QStyle.StateFlag.State_Selected:
            ctx.palette.setColor(QPalette.ColorRole.Text, option.palette.highlightedText().color())
        doc.documentLayout().draw(painter, ctx)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        """Return size hint based on content"""
        from PyQt6.QtGui import QTextDocument
        
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            return super().sizeHint(option, index)
        
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(text)
        doc.setTextWidth(option.rect.width() if option.rect.width() > 0 else 400)
        
        return QSize(int(doc.idealWidth()), max(int(doc.size().height()) + 8, 50))


class _BrowserCellDelegate(QStyledItemDelegate):
    """Cell painter for the Browse All table (BATCH TM3, задачи 3 + 7).

    Paints the whole cell itself so it can layer three things the default
    delegate cannot combine:
      - selected-row background stays as-is, while the CURRENT cell gets a
        darker shade of the same highlight colour (задача 7);
      - Source/Target text is wrapped at the real column width and the
        matches of the APPLIED filter are highlighted (задача 3) — paint
        only, the item text/data are never modified;
      - sizeHint mirrors the paint geometry (same padding constants), so
        resizeRowsToContents() computes heights from the true wrapped
        height instead of the QCommonStyle wrap heuristic (задача 1).
    """

    # Total padding inside a cell, used by both paint() and sizeHint().
    PAD_X = 8   # 4 left + 4 right
    PAD_Y = 6   # 3 top + 3 bottom
    HIGHLIGHT_CSS = "background-color: #FFD54F;"

    def __init__(self, table, column: int, highlightable: bool):
        super().__init__(table)
        self._table = table
        self._column = column
        self._highlightable = highlightable
        self._term = ""
        self._whole_words = False
        self._enabled = True

    def set_highlight(self, term: str, whole_words: bool = False,
                      enabled: bool = True):
        """Set the APPLIED filter term to highlight ('' or disabled = none).

        ``enabled`` mirrors the «Search in» mode: a column outside the mode
        (e.g. Target in «Source only») is never highlighted."""
        self._term = term or ""
        self._whole_words = bool(whole_words)
        self._enabled = bool(enabled)

    @staticmethod
    def match_ranges(text: str, term: str, whole_words: bool):
        """Ranges of ``term`` in ``text`` for highlighting.

        Matches on the ORIGINAL string with re.IGNORECASE (Unicode case
        folding covers Cyrillic); never on a casefold copy — lengths can
        differ, and the ranges are applied to the original text.
        """
        if not text or not term:
            return []
        if whole_words:
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
        return [(m.start(), m.end()) for m in pattern.finditer(text)]

    def _build_html(self, text: str) -> str:
        """Escape the whole text and wrap the matched ranges in a span."""
        from html import escape
        if not self._term:
            return escape(text)
        out = []
        last = 0
        for start, end in self.match_ranges(text, self._term, self._whole_words):
            out.append(escape(text[last:start]))
            out.append(
                f"<span style='{self.HIGHLIGHT_CSS}'>{escape(text[start:end])}</span>")
            last = end
        out.append(escape(text[last:]))
        return "".join(out)

    def _make_doc(self, option, index) -> QTextDocument:
        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setDefaultFont(option.font)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        # Plain text when nothing is highlighted: setHtml() resolves the
        # document font differently (taller line metrics on the fontless
        # test platform), so height and text rendering must not go through
        # HTML unless there is something to highlight.
        if self._term and self._enabled:
            doc.setHtml(self._build_html(text))
            doc.setDefaultFont(option.font)  # setHtml may reset the font
        else:
            doc.setPlainText(text)
        doc.setTextWidth(max(10, option.rect.width() - self.PAD_X))
        return doc

    def paint(self, painter, option, index):
        painter.save()
        # Background / selection / alternating colour: drawn by the same
        # style path the default delegate uses (CE_ItemViewItem with empty
        # text), so the theme stylesheet and row alternation keep working.
        # Qt6 has no State_Alternate to fill manually.
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        self._table.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem, opt, painter, self._table)
        # BATCH TM3, задача 7: текущая ячейка выделенной строки — более
        # тёмный оттенок того же цвета выделения.
        if ((opt.state & QStyle.StateFlag.State_Selected)
                and index == self._table.currentIndex()):
            painter.fillRect(
                option.rect, option.palette.highlight().color().darker(125))

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if self._highlightable and self._enabled and self._term and text:
            doc = self._make_doc(option, index)
            ctx = QAbstractTextDocumentLayout.PaintContext()
            if opt.state & QStyle.StateFlag.State_Selected:
                ctx.palette.setColor(
                    QPalette.ColorRole.Text,
                    opt.palette.highlightedText().color())
            painter.translate(option.rect.left() + self.PAD_X // 2,
                              option.rect.top() + self.PAD_Y // 2)
            painter.setClipRect(QRectF(0, 0,
                                       option.rect.width() - self.PAD_X,
                                       option.rect.height() - self.PAD_Y))
            doc.documentLayout().draw(painter, ctx)
        else:
            painter.setPen(option.palette.text().color())
            if text is not None:
                painter.drawText(
                    option.rect.adjusted(self.PAD_X // 2, 0,
                                         -(self.PAD_X // 2), 0),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    str(text))
        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        fm = option.fontMetrics
        if not self._highlightable or not text:
            # Plain columns (ID / TM / Usage / Modified): compact height by
            # the same formula as the text columns. The default delegate's
            # sizeHint (style CT_ItemViewItem padding) is ~6 px taller and
            # would inflate every single-line row (BATCH TM3, задача 1).
            return QSize(option.rect.width(), max(fm.height() + self.PAD_Y, 1))
        # Single deterministic path (QTextDocument at the real column width):
        # height must match paint() exactly, and QFontMetrics line metrics
        # diverge from QTextDocument on the fontless offscreen test platform.
        # Measured (BATCH TM3 T4): 500 long rows still fill well under 1 s.
        doc = self._make_doc(option, index)
        height = int(doc.size().height()) + self.PAD_Y
        return QSize(option.rect.width(),
                     max(height, fm.height() + self.PAD_Y))


class _BrowserTable(QTableWidget):
    """Browse All table with Delete-key and Ctrl+C support.

    BATCH TM2, задача 4: Qt.Key_Delete is a key CODE, so the handler works
    in any keyboard layout (the letter on the key differs, the code does
    not). The signal fires only when there is a selection and the table has
    focus: Delete typed in the Filter line edit goes to QLineEdit and never
    reaches this handler.

    BATCH TM3, задача 7: Ctrl+C copies the FULL text of the current cell
    (plain text, no markup) — click Source + Ctrl+C = Source, click Target
    + Ctrl+C = Target, other columns copy their own text.

    BATCH TM3, задача 1: shown/viewport-resized signals let the dialog
    re-sync row heights once the widget is actually visible and the stretch
    columns have their final width.
    """

    delete_requested = pyqtSignal()
    shown_to_user = pyqtSignal()
    viewport_resized = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete and self.selectedIndexes():
            self.delete_requested.emit()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Copy):
            current = self.currentIndex()
            if current.isValid():
                text = current.data(Qt.ItemDataRole.DisplayRole)
                QApplication.clipboard().setText(
                    "" if text is None else str(text))
                event.accept()
                return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.shown_to_user.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewport_resized.emit()


class ConcordanceSearchDialog(QDialog):
    """
    Lightweight Concordance Search dialog for Ctrl+K.
    Focused on quick concordance search without other TM management features.
    Features two view modes: List view and Table view (memoQ-style side-by-side).
    """
    
    def __init__(self, parent, db_manager, log_callback: Optional[Callable] = None, initial_query: str = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.log = log_callback if log_callback else lambda x: None
        self.parent_app = parent
        self.current_results = []  # Store results for both views
        self.current_search_term = ""
        self._updating_heights = False  # Flag to prevent recursive updates
        self._initial_query = initial_query  # Store for after show
        
        # Get language names from parent app
        self.source_lang_name = getattr(parent, 'source_language', 'Source')
        self.target_lang_name = getattr(parent, 'target_language', 'Target')
        
        self.setWindowTitle("Concordance Search")
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
    
    def exec(self):
        """Override exec to restore saved geometry or match parent window"""
        # Try to restore saved geometry from project
        geometry_restored = False
        if hasattr(self.parent_app, 'current_project') and self.parent_app.current_project:
            project = self.parent_app.current_project
            if hasattr(project, 'concordance_geometry') and project.concordance_geometry:
                geom = project.concordance_geometry
                self.setGeometry(geom['x'], geom['y'], geom['width'], geom['height'])
                geometry_restored = True
        
        # If no saved geometry, match parent window size and position
        if not geometry_restored and self.parent_app:
            parent_geom = self.parent_app.geometry()
            self.setGeometry(parent_geom)
        
        self.show()
        
        # Set initial query and search if provided
        if self._initial_query:
            self.search_input.setText(self._initial_query)
            self.do_search()
        
        return super().exec()
    
    def closeEvent(self, event):
        """Save window geometry to project when closing"""
        if hasattr(self.parent_app, 'current_project') and self.parent_app.current_project:
            geom = self.geometry()
            self.parent_app.current_project.concordance_geometry = {
                'x': geom.x(),
                'y': geom.y(),
                'width': geom.width(),
                'height': geom.height()
            }
        super().closeEvent(event)
    
    def setup_ui(self):
        """Setup the UI with the TM concordance view"""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("🔍 Concordance Search")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Search across translation memories for exact and partial matches")
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Search controls
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter text to search...")
        self.search_input.returnPressed.connect(self.do_search)
        self.search_input.setStyleSheet("padding: 8px; font-size: 13px;")
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self.do_search)
        search_btn.setStyleSheet("padding: 8px 16px;")
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
        
        # Tab widget for result views
        self.view_tabs = QTabWidget()

        # TM Concordance (exact/fuzzy text matching)
        self.tm_tab = QWidget()
        tm_layout = QVBoxLayout(self.tm_tab)
        tm_layout.setContentsMargins(0, 10, 0, 0)

        self.search_results = QTextEdit()
        self.search_results.setReadOnly(True)
        self.search_results.setFont(QFont("Segoe UI", 10))
        self.search_results.setStyleSheet("background-color: #fafafa; border: 1px solid #ddd; border-radius: 4px;")
        tm_layout.addWidget(self.search_results)

        # Tab title carries the result count (updated after search)
        self.view_tabs.addTab(self.tm_tab, "📋 TM Matches")
        
        layout.addWidget(self.view_tabs)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Enter a search term and press Search or Enter")
        self.status_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("padding: 6px 20px;")
        status_layout.addWidget(close_btn)
        
        layout.addLayout(status_layout)
        
        self.setLayout(layout)
        
        # Focus on search input
        self.search_input.setFocus()

    def do_search(self):
        """Perform the TM concordance search"""
        search_text = self.search_input.text().strip()
        if not search_text:
            self.status_label.setText("⚠️ Please enter a search term")
            return

        self.status_label.setText("🔍 Searching...")
        self.search_results.clear()
        self.current_search_term = search_text

        tm_count = 0

        # Search TM (concordance)
        try:
            results = self.db_manager.concordance_search(search_text)
            self.current_results = results if results else []
            tm_count = len(self.current_results)
            
            if not results:
                self.search_results.setHtml(
                    f"<p style='color: #666; padding: 20px; text-align: center;'>"
                    f"No TM matches found for '<b>{search_text}</b>'</p>"
                )
            else:
                self.update_tm_view()
                
        except Exception as e:
            self.search_results.setHtml(f"<p style='color: red; padding: 20px;'>TM Search Error: {str(e)}</p>")
            self.log(f"TM Concordance search error: {e}")

        # Update tab title with count
        self.view_tabs.setTabText(0, f"📋 TM Matches ({tm_count})")

        # Update status
        if tm_count > 0:
            self.status_label.setText(f"✓ Found {tm_count} TM matches")
            self.log(f"Concordance: Found {tm_count} TM matches for '{search_text}'")
        else:
            self.status_label.setText("No matches found")
    
    def update_tm_view(self):
        """Update the TM concordance view with current results"""
        if not self.current_results:
            return
        
        search_text = self.current_search_term
        results = self.current_results
        
        # Format results with highlighting
        html = f"<h3 style='color: #333; margin-bottom: 15px;'>Found {len(results)} TM matches for '<span style='color: #2196F3;'>{search_text}</span>'</h3>"
        
        for idx, match in enumerate(results, 1):
            source = match.get('source_text', '')
            target = match.get('target_text', '')
            tm_id = match.get('tm_id', 'Unknown')
            usage_count = match.get('usage_count', 0)
            modified_date = match.get('modified_date', 'Unknown')
            
            # Highlight search term in source and target
            highlighted_source = self._highlight_term(source, search_text)
            highlighted_target = self._highlight_term(target, search_text)
            
            # Alternating background colors for better visibility
            bg_color = '#f5f5f5' if idx % 2 == 0 else '#ffffff'
            
            html += f"""
            <div style='background-color: {bg_color}; padding: 10px 8px; margin: 0;'>
                <div style='color: #555; font-size: 11px; margin-bottom: 6px;'>
                    #{idx} - TM: <b>{tm_id}</b> - Used: {usage_count} times - Modified: {modified_date}
                </div>
                <div style='margin-bottom: 4px;'>
                    <b style='color: #1976D2;'>{self.source_lang_name}:</b> {highlighted_source}
                </div>
                <div>
                    <b style='color: #388E3C;'>{self.target_lang_name}:</b> {highlighted_target}
                </div>
            </div>
            <hr style='border: none; border-top: 2px solid #666; margin: 0;'>
            """
        
        self.search_results.setHtml(html)
    
    def _highlight_term(self, text: str, search_term: str) -> str:
        """Highlight search term in text with yellow/orange background"""
        if not text or not search_term:
            return text or ""
        
        import re
        # Case-insensitive highlighting
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        return pattern.sub(
            lambda m: f"<span style='background-color: #FFD54F; padding: 1px 3px; border-radius: 2px; font-weight: bold;'>{m.group()}</span>",
            text
        )


class TMManagerDialog(QDialog):
    """Translation Memory Manager dialog"""
    
    def __init__(self, parent, db_manager, log_callback: Optional[Callable] = None, tm_ids: list = None,
                 initial_concordance_query: str = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.log = log_callback if log_callback else lambda x: None
        self.parent_app = parent
        self.filter_tm_ids = tm_ids  # Optional filter: only show entries from these TM IDs
        self._initial_concordance_query = initial_concordance_query
        # SQL helper sv_casefold регистрируется лениво при первом фильтре
        # (BATCH TM2, задача 2: регистронезависимый поиск и для кириллицы).
        self._casefold_registered = False
        # BATCH TM3, задача 8: данные (список TM / записи) изменились, пока
        # подвкладка Browse All была скрыта — перезагрузить при показе.
        self._data_dirty = False
        # BATCH TM3, задача 1: дебаунс пересчёта высот строк (showEvent /
        # resizeEvent / изменение ширины колонок приходят пачками).
        self._height_timer = QTimer(self)
        self._height_timer.setSingleShot(True)
        self._height_timer.setInterval(100)
        self._height_timer.timeout.connect(self._sync_row_heights)

        self.setWindowTitle("Translation Memory Manager")
        self.resize(1000, 700)

        self.setup_ui()
        self.load_initial_data()

        # If a concordance query was provided, switch to Concordance tab and run it
        if self._initial_concordance_query:
            self.tabs.setCurrentIndex(1)  # Concordance tab
            self.search_input.setText(self._initial_concordance_query)
            self.do_concordance_search()
    
    def setup_ui(self):
        """Setup the UI with tabs"""
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("📚 Translation Memory Manager")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.browser_tab = self.create_browser_tab()
        self.search_tab = self.create_search_tab()
        self.import_export_tab = self.create_import_export_tab()
        self.stats_tab = self.create_stats_tab()
        
        self.tabs.addTab(self.browser_tab, "📋 Browse")
        self.tabs.addTab(self.search_tab, "🔍 Concordance")
        self.tabs.addTab(self.import_export_tab, "📥 Import/Export")
        self.tabs.addTab(self.stats_tab, "📊 Statistics")
        
        # Add maintenance tab for cleaning
        self.maintenance_tab = self.create_maintenance_tab()
        self.tabs.addTab(self.maintenance_tab, "🧹 Maintenance")
        
        layout.addWidget(self.tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def create_browser_tab(self):
        """Create TM browser tab"""
        widget = QGroupBox()
        layout = QVBoxLayout()

        # Filter controls (BATCH TM2, задача 2). Верхняя строка — только
        # фильтр: список TM + поле + кнопка Filter + Clear + область поиска
        # + Whole words. Глобальные действия (Refresh, Show) переехали в
        # нижнюю панель.
        filter_layout = QHBoxLayout()
        self.browser_tm_label = QLabel("TM:")
        filter_layout.addWidget(self.browser_tm_label)
        # BATCH TM3, задача 9: сужение Browse All до одной TM (применяется
        # в SQL ДО лимита Show и ДО фильтра). В scoped-режиме (TMEditorDialog
        # с filter_tm_ids) список не нужен — одна TM и так фиксирована.
        self.browser_tm_combo = QComboBox()
        self.browser_tm_combo.setToolTip(
            self.tr("Show entries of one TM only (All TMs by default)"))
        self.browser_tm_combo.currentIndexChanged.connect(self._on_browser_tm_changed)
        filter_layout.addWidget(self.browser_tm_combo)
        if self.filter_tm_ids:
            self.browser_tm_label.setVisible(False)
            self.browser_tm_combo.setVisible(False)

        filter_layout.addWidget(QLabel("Filter:"))
        self.browser_filter = QLineEdit()
        self.browser_filter.setPlaceholderText(
            self.tr("Type to filter entries, then press Enter or Filter..."))
        self.browser_filter.returnPressed.connect(self.refresh_browser)
        filter_layout.addWidget(self.browser_filter)

        self.browser_filter_btn = QPushButton(self.tr("Filter"))
        self.browser_filter_btn.clicked.connect(self.refresh_browser)
        filter_layout.addWidget(self.browser_filter_btn)

        self.browser_clear_btn = QPushButton(self.tr("Clear"))
        self.browser_clear_btn.clicked.connect(self.clear_browser_filter)
        filter_layout.addWidget(self.browser_clear_btn)

        filter_layout.addWidget(QLabel("Search in:"))
        self.browser_search_in = QComboBox()
        self.browser_search_in.addItem(self.tr("Source and Target"), "both")
        self.browser_search_in.addItem(self.tr("Source only"), "source")
        self.browser_search_in.addItem(self.tr("Target only"), "target")
        self.browser_search_in.setToolTip(self.tr("Choose where to search"))
        filter_layout.addWidget(self.browser_search_in)

        # BATCH TM3, задача 4: CheckmarkCheckBox вместо голого QCheckBox —
        # под темой приложения (theme_manager.py) у обычного QCheckBox
        # QCheckBox::indicator:checked рисуется заливкой БЕЗ отметки ✓
        # (recon R2a), а CheckmarkCheckBox рисует белую галку поверх
        # зелёной заливки (recon R2b).
        self.browser_whole_words = CheckmarkCheckBox(self.tr("Whole words"))
        self.browser_whole_words.setToolTip(
            self.tr("Match whole words only (word boundaries, not substrings)"))
        filter_layout.addWidget(self.browser_whole_words)

        layout.addLayout(filter_layout)

        # Table
        self.browser_table = _BrowserTable()
        self.browser_table.setColumnCount(6)
        self.browser_table.setHorizontalHeaderLabels([
            "ID", "Source", "Target", "TM", "Usage", "Modified"
        ])
        self.browser_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.browser_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.browser_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.browser_table.setAlternatingRowColors(True)
        # Enable sorting by clicking column headers
        self.browser_table.setSortingEnabled(True)
        # Delete key on the table deletes the selected rows (BATCH TM2, задача 4)
        self.browser_table.delete_requested.connect(self.delete_selected_entry)
        # BATCH TM3, задачи 1+3+7: ячейки рисует свой делегат (перенос по
        # реальной ширине колонки + подсветка применённого фильтра +
        # затемнение текущей ячейки), а показ/изменение размера виджета и
        # ширины колонок включают дебаунс-пересчёт высот строк.
        self._source_delegate = _BrowserCellDelegate(self.browser_table, 1, True)
        self._target_delegate = _BrowserCellDelegate(self.browser_table, 2, True)
        self._plain_delegate = _BrowserCellDelegate(self.browser_table, -1, False)
        self.browser_table.setItemDelegateForColumn(1, self._source_delegate)
        self.browser_table.setItemDelegateForColumn(2, self._target_delegate)
        for col in (0, 3, 4, 5):
            self.browser_table.setItemDelegateForColumn(col, self._plain_delegate)
        self.browser_table.shown_to_user.connect(self._on_browser_shown)
        self.browser_table.viewport_resized.connect(self._schedule_row_height_sync)
        self.browser_table.horizontalHeader().sectionResized.connect(
            self._schedule_row_height_sync)
        layout.addWidget(self.browser_table)

        # Bottom panel (BATCH TM2, задача 2): построчные действия + глобальные.
        btn_layout = QHBoxLayout()
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.clicked.connect(self.delete_selected_entry)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()

        self.browser_limit = QSpinBox()
        self.browser_limit.setRange(100, 10000)
        self.browser_limit.setValue(500)
        self.browser_limit.setSingleStep(100)
        self.browser_limit.setPrefix("Show: ")
        self.browser_limit.setSuffix(" entries")
        btn_layout.addWidget(self.browser_limit)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_browser)
        btn_layout.addWidget(refresh_btn)

        self.browser_status = QLabel("Ready")
        btn_layout.addWidget(self.browser_status)

        layout.addLayout(btn_layout)

        widget.setLayout(layout)
        return widget
    
    def create_search_tab(self):
        """Create concordance search tab"""
        widget = QGroupBox()
        layout = QVBoxLayout()
        
        # Search controls
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter text to search in source and target...")
        self.search_input.returnPressed.connect(self.do_concordance_search)
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self.do_concordance_search)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
        
        # Results display
        self.search_results = QTextEdit()
        self.search_results.setReadOnly(True)
        self.search_results.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.search_results)
        
        # Status
        self.search_status = QLabel("Enter a search term and press Search")
        layout.addWidget(self.search_status)
        
        widget.setLayout(layout)
        return widget
    
    def create_import_export_tab(self):
        """Create import/export tab"""
        widget = QGroupBox()
        layout = QVBoxLayout()
        
        # Import section
        import_group = QGroupBox("Import TMX")
        import_layout = QVBoxLayout()
        
        import_info = QLabel(
            "Import translation units from a TMX file into your database.\n"
            "All entries will be added to a new TM or merged with an existing one."
        )
        import_info.setWordWrap(True)
        import_layout.addWidget(import_info)
        
        import_controls = QHBoxLayout()
        import_controls.addWidget(QLabel("TM ID:"))
        self.import_tm_id = QLineEdit("imported")
        self.import_tm_id.setPlaceholderText("Enter TM identifier")
        import_controls.addWidget(self.import_tm_id)
        
        import_btn = QPushButton("📂 Select and Import TMX...")
        import_btn.clicked.connect(self.import_tmx)
        import_controls.addWidget(import_btn)
        import_layout.addLayout(import_controls)
        
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        import_layout.addWidget(self.import_progress)
        
        self.import_status = QLabel("")
        import_layout.addWidget(self.import_status)
        
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)
        
        # Export section
        export_group = QGroupBox("Export TMX")
        export_layout = QVBoxLayout()
        
        export_info = QLabel(
            "Export your translation memory to a standard TMX file.\n"
            "The TMX file can be used in other CAT tools or shared with colleagues."
        )
        export_info.setWordWrap(True)
        export_layout.addWidget(export_info)
        
        export_controls = QHBoxLayout()
        export_controls.addWidget(QLabel("TM to export:"))
        self.export_tm_selector = QComboBox()
        self.export_tm_selector.addItem("All TMs", "all")
        self.export_tm_selector.addItem("Project TM only", "project")
        export_controls.addWidget(self.export_tm_selector)
        
        export_btn = QPushButton("💾 Export to TMX...")
        export_btn.clicked.connect(self.export_tmx)
        export_controls.addWidget(export_btn)
        export_layout.addLayout(export_controls)
        
        self.export_status = QLabel("")
        export_layout.addWidget(self.export_status)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_stats_tab(self):
        """Create statistics tab"""
        widget = QGroupBox()
        layout = QVBoxLayout()
        
        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setFont(QFont("Courier New", 10))
        layout.addWidget(self.stats_display)
        
        refresh_btn = QPushButton("🔄 Refresh Statistics")
        refresh_btn.clicked.connect(self.refresh_stats)
        layout.addWidget(refresh_btn)
        
        widget.setLayout(layout)
        return widget
    
    def load_initial_data(self):
        """Load initial data for all tabs"""
        self._reload_browser_tm_combo()
        self.refresh_browser()
        self.refresh_stats()
    
    def refresh_browser(self, keep_sort=False):
        """Refresh the TM browser table.

        keep_sort=True keeps the current sort indicator (BATCH TM3, задача
        8: авто-перезагрузка на свежесть данных сохраняет пользовательскую
        сортировку). Обычный refresh по-прежнему возвращает ID asc —
        решение BATCH TM2 (suite tm2 S1 T3)."""
        try:
            limit = self.browser_limit.value()
            filter_text = self.browser_filter.text().strip()

            # BATCH TM3, задача 3: подсветка — только по ПРИМЕНЁННОМУ
            # фильтру (то, что выполнили Enter/Filter/Clear/TM-выбор), а не
            # по набранному в поле тексту. Делегаты читают этот термин при
            # отрисовке; текст item/данные не меняются.
            whole = self.browser_whole_words.isChecked()
            mode = self.browser_search_in.currentData()
            self._source_delegate.set_highlight(
                filter_text, whole, mode in ("both", "source"))
            self._target_delegate.set_highlight(
                filter_text, whole, mode in ("both", "target"))

            entries = self._fetch_browser_entries(limit, filter_text)

            # Populate table. Sorting must be suspended while filling: with
            # sorting enabled every setItem() triggers a re-sort, rows move
            # mid-fill and the cells of one entry scatter across different
            # display rows (BATCH TM1.1: duplicated IDs, Delete Selected
            # removing entries other than the ones shown).
            table = self.browser_table
            table.setSortingEnabled(False)
            table.setUpdatesEnabled(False)
            table.clearContents()
            # BATCH TM3, задача 8: перезагрузка сбрасывает выделение
            # (clearContents сам его не снимает — selection ranges живут
            # в selection model независимо от items).
            table.clearSelection()
            table.setRowCount(len(entries))
            # BATCH TM2, задача 3: в item кладём ПОЛНЫЙ текст; ячейки
            # переносятся (word wrap) с авто-высотой строк. Порог elide НЕ
            # введён: замер заполнения 500 строк с ~2000-символьными
            # текстами дал 0.19 c (<1 c) — см. отчёт BATCH TM2, задача 3.
            # BATCH TM3, задача 2: tooltip на Source/Target убран — полный
            # текст виден в ячейке; остальные tooltip не тронуты.
            table.setWordWrap(True)
            for row, entry in enumerate(entries):
                entry_id = int(entry['id'])
                # ID as int DisplayRole: sorts numerically; entry id also kept
                # in Qt.UserRole on EVERY cell so deletion keys stay valid
                # no matter which column the user sorted by.
                id_item = QTableWidgetItem()
                id_item.setData(Qt.ItemDataRole.DisplayRole, entry_id)
                id_item.setData(Qt.ItemDataRole.UserRole, entry_id)
                table.setItem(row, 0, id_item)
                source_item = QTableWidgetItem(entry['source_text'])
                source_item.setData(Qt.ItemDataRole.UserRole, entry_id)
                table.setItem(row, 1, source_item)
                target_item = QTableWidgetItem(entry['target_text'])
                target_item.setData(Qt.ItemDataRole.UserRole, entry_id)
                table.setItem(row, 2, target_item)
                tm_item = QTableWidgetItem(entry['tm_id'])
                tm_item.setData(Qt.ItemDataRole.UserRole, entry_id)
                table.setItem(row, 3, tm_item)
                usage_item = QTableWidgetItem(str(entry.get('usage_count', 0)))
                usage_item.setData(Qt.ItemDataRole.UserRole, entry_id)
                table.setItem(row, 4, usage_item)
                modified_item = QTableWidgetItem(entry.get('modified_date', '')[:16])
                modified_item.setData(Qt.ItemDataRole.UserRole, entry_id)
                table.setItem(row, 5, modified_item)
            table.setUpdatesEnabled(True)
            # BATCH TM2, задача 1: валидный индикатор сортировки (ID asc) с
            # самого начала и после каждого refresh. setSortIndicator идёт ДО
            # включения сортировки (урок BATCH TM1.1: setSortingEnabled(True)
            # применяет текущий индикатор ко всей таблице сразу). Клик по
            # заголовку по-прежнему меняет сортировку пользователем.
            # BATCH TM3, задача 8: авто-перезагрузка (freshness) сохраняет
            # текущую сортировку пользователя (keep_sort=True).
            if not keep_sort:
                table.horizontalHeader().setSortIndicator(
                    0, Qt.SortOrder.AscendingOrder)
            # Re-enable sorting AFTER the table is complete: rows are now
            # moved as whole units, so the display matches the database.
            table.setSortingEnabled(True)
            table.resizeRowsToContents()

            self.browser_status.setText(f"Showing {len(entries)} entries")
            self.log(f"TM Browser: Loaded {len(entries)} entries")

        except Exception as e:
            self.browser_status.setText(f"Error: {str(e)}")
            self.log(f"Error refreshing TM browser: {e}")

    def _ensure_casefold_function(self):
        """Register the SQL helper sv_casefold once per dialog connection.

        SQLite LIKE folds case for ASCII only; wrapping both sides in
        str.casefold gives case-insensitive substring search for Cyrillic
        (and any other Unicode script) too. '%' and '_' are ordinary
        characters because the query is escaped and searched with ESCAPE.
        """
        if self._casefold_registered:
            return
        self.db_manager.connection.create_function(
            "sv_casefold", 1, str.casefold, deterministic=True)
        self._casefold_registered = True

    def _browser_search_fields(self):
        """Column names searched by the Browse All filter ('Search in' mode)."""
        mode = self.browser_search_in.currentData()
        if mode == 'source':
            return ('source_text',)
        if mode == 'target':
            return ('target_text',)
        return ('source_text', 'target_text')

    @staticmethod
    def _entry_whole_word_match(entry, pattern, fields):
        """Whole-word match: Unicode word boundaries (Python re \\b covers
        Cyrillic; re.IGNORECASE does Unicode case folding)."""
        return any(pattern.search(entry[col] or "") for col in fields)

    def _browser_tm_constraint(self):
        """TM ids the Browse All query is constrained to (BATCH TM3, задача 9).

        The «TM:» combobox wins when a specific TM is selected; otherwise the
        dialog-level filter_tm_ids (scoped TMEditorDialog mode) applies.
        None means all TMs."""
        selected = self.browser_tm_combo.currentData()
        if selected:
            return [selected]
        return self.filter_tm_ids

    def _fetch_browser_entries(self, limit, filter_text):
        """Fetch Browse All entries.

        BATCH TM2, задачи 1–2:
        - без фильтра отбор N записей остался прежним (N самых свежих по
          modified_date DESC, теперь с детерминированным тай-брейком id DESC),
          порядок ОТОБРАЖЕНИЯ задаёт индикатор сортировки (ID asc);
        - с фильтром подстрока/Whole words применяются ко ВСЕМ записям
          выбранных TM ДО лимита Show (тоже newest-first, затем [:limit]).
        - подстрока: sv_casefold с обеих сторон + ESCAPE — регистр игнорируется
          и для кириллицы, '%' и '_' — обычные символы.
        BATCH TM3, задача 9: ограничение по выбранной TM («TM:»)
        применяется в SQL ДО лимита Show и ДО фильтра.
        """
        tm_filter = ""
        params = []
        tm_ids = self._browser_tm_constraint()
        if tm_ids:
            placeholders = ','.join('?' * len(tm_ids))
            tm_filter = f" WHERE tm_id IN ({placeholders})"
            params = list(tm_ids)

        cursor = self.db_manager.cursor
        if not filter_text:
            query = (f"SELECT * FROM translation_units{tm_filter} "
                     f"ORDER BY modified_date DESC, id DESC LIMIT {int(limit)}")
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

        self._ensure_casefold_function()
        fields = self._browser_search_fields()
        needle = (filter_text.casefold()
                  .replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_"))
        pattern = f"%{needle}%"
        col_conditions = " OR ".join(
            f"sv_casefold({col}) LIKE ? ESCAPE '\\'" for col in fields)
        where = (f"{tm_filter} AND ({col_conditions})" if tm_filter
                 else f" WHERE ({col_conditions})")
        query = (f"SELECT * FROM translation_units{where} "
                 f"ORDER BY modified_date DESC, id DESC")
        cursor.execute(query, params + [pattern] * len(fields))
        entries = [dict(row) for row in cursor.fetchall()]

        if self.browser_whole_words.isChecked():
            word_pattern = re.compile(
                r"\b" + re.escape(filter_text) + r"\b", re.IGNORECASE)
            entries = [e for e in entries
                       if self._entry_whole_word_match(e, word_pattern, fields)]

        return entries[:limit]

    def clear_browser_filter(self):
        """Clear the filter and reload the unfiltered table.

        BATCH TM2, задача 2: no blank rows and no duplicates can appear —
        the unfiltered path re-reads the database directly (one row per
        translation_units entry).
        BATCH TM3, задача 5: Clear сбрасывает также Whole words (выкл.) и
        «Search in» (Source and Target). Список «TM:» НЕ сбрасывается —
        это область просмотра, а не фильтр."""
        self.browser_filter.clear()
        if self.browser_whole_words.isChecked():
            self.browser_whole_words.setChecked(False)
        if self.browser_search_in.currentIndex() != 0:
            self.browser_search_in.blockSignals(True)
            self.browser_search_in.setCurrentIndex(0)
            self.browser_search_in.blockSignals(False)
        self.refresh_browser()

    def _reload_browser_tm_combo(self):
        """Rebuild the «TM:» combobox from translation_memories (задача 9).

        Keeps the current selection when that TM still exists; a TM that was
        deleted while the tab was hidden falls back to «All TMs»."""
        combo = self.browser_tm_combo
        if not combo.isVisible() and self.filter_tm_ids:
            return  # scoped mode: single fixed TM
        combo.blockSignals(True)
        current = combo.currentData()
        combo.clear()
        combo.addItem(self.tr("All TMs"), None)
        try:
            self.db_manager.cursor.execute(
                "SELECT name, tm_id FROM translation_memories "
                "ORDER BY name COLLATE NOCASE")
            for name, tm_id in self.db_manager.cursor.fetchall():
                combo.addItem(str(name), tm_id)
        except Exception as e:
            self.log(f"Error loading TM list for Browse All: {e}")
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _on_browser_tm_changed(self, index):
        """«TM:» selection reloads the table immediately (задача 9)."""
        self.refresh_browser()

    def _on_browser_shown(self):
        """Browse All became visible (задача 8а + высоты, задача 1)."""
        if self._data_dirty:
            self._data_dirty = False
            self._reload_browser_tm_combo()
            self.refresh_browser(keep_sort=True)
        self._schedule_row_height_sync()

    def on_tm_list_changed(self):
        """Hook for the main window (BATCH TM3, задача 8б).

        Called after TM list operations (create / delete / import / rename)
        and after entry deletions elsewhere in the app. A visible sub-tab
        reloads immediately (keeping filter, mode, Whole words, TM selection
        and sort state — refresh_browser only re-reads the data); a hidden
        one is marked dirty and reloads on the next show."""
        if self.browser_table.isVisible():
            self._reload_browser_tm_combo()
            self.refresh_browser(keep_sort=True)
        else:
            self._data_dirty = True

    def _schedule_row_height_sync(self):
        """Debounced row-height recompute (задача 1): showEvent, viewport
        resize and column resize all arrive in bursts; a single-shot timer
        coalesces them into one resizeRowsToContents() pass."""
        self._height_timer.start()

    def _sync_row_heights(self):
        """Recompute row heights from the content (задача 1).

        Only runs while the widget is visible: heights measured on a hidden
        table use the pre-layout column widths and are wrong (recon R1a).
        Called after the widget is shown, on window resize and on column
        resize; refresh_browser also recomputes after every fill."""
        table = self.browser_table
        if not table.isVisible() or table.rowCount() == 0:
            return
        table.resizeRowsToContents()
    
    def delete_selected_entry(self):
        """Delete ALL selected TM entries in one confirmed transaction"""
        # Collect unique entry ids from every selected row (Shift-range,
        # Ctrl-click, Ctrl+A). Cell-level selections collapse to the row's id
        # read from Qt.UserRole (stored on every cell by refresh_browser),
        # never via row indices and never via display text: the user may have
        # re-sorted the table, so display rows are not stable db keys.
        rows = sorted({index.row() for index in self.browser_table.selectedIndexes()})
        if not rows:
            QMessageBox.warning(self, "No Selection", "Please select an entry to delete")
            return

        entry_ids = []
        tm_ids = set()
        for row in rows:
            id_item = self.browser_table.item(row, 0)
            if id_item is None:
                continue
            entry_id = id_item.data(Qt.ItemDataRole.UserRole)
            if entry_id is None:
                # Fallback for cells created before the UserRole convention.
                entry_id = int(id_item.text())
            entry_ids.append(int(entry_id))
            tm_item = self.browser_table.item(row, 3)
            if tm_item is not None:
                tm_ids.add(tm_item.text())
        if not entry_ids:
            QMessageBox.warning(self, "No Selection", "Please select an entry to delete")
            return

        if len(tm_ids) == 1:
            scope_display = f"TM {next(iter(tm_ids))}"
        else:
            scope_display = f"{len(tm_ids)} TMs ({', '.join(sorted(tm_ids))})"

        # List the ids about to be deleted (up to 10, then a "… and K more").
        sorted_ids = sorted(entry_ids)
        if len(sorted_ids) <= 10:
            ids_display = ", ".join(str(i) for i in sorted_ids)
        else:
            ids_display = (
                ", ".join(str(i) for i in sorted_ids[:10])
                + self.tr(" … and {k} more").format(k=len(sorted_ids) - 10)
            )

        # Confirm deletion (one dialog for the whole batch)
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            self.tr(
                "Delete {n} selected entries from {scope}?\n\nIDs: {ids}\n\nThis cannot be undone."
            ).format(n=len(entry_ids), scope=scope_display, ids=ids_display),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            conn = self.db_manager.connection
            cursor = self.db_manager.cursor
            # Flush any pending implicit transaction first, so the rollback on
            # error below covers exactly this batch and nothing partial stays.
            conn.commit()
            # Whole batch in ONE transaction: DELETE ... WHERE id IN (...)
            # in chunks of <= 500 ids, single commit at the end.
            for start in range(0, len(entry_ids), 500):
                chunk = entry_ids[start:start + 500]
                placeholders = ",".join("?" * len(chunk))
                cursor.execute(
                    f"DELETE FROM translation_units WHERE id IN ({placeholders})",
                    chunk,
                )
            conn.commit()
            deleted = len(entry_ids)
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            QMessageBox.critical(self, "Error", f"Failed to delete entries: {str(e)}")
            return

        self.log(f"TM Browser: deleted {deleted} entries from {scope_display}")
        # One refresh for the whole batch (re-reads the table and the entry
        # counts; the FTS/trigram indexes are trigger-maintained by SQLite).
        self.refresh_browser()
    
    def do_concordance_search(self):
        """Perform concordance search"""
        query = self.search_input.text().strip()
        if not query:
            self.search_status.setText("Please enter a search term")
            return
        
        try:
            results = self.db_manager.concordance_search(query)
            
            # Display results
            self.search_results.clear()
            html = f"<h3>Found {len(results)} matches for '{query}'</h3>"
            
            for idx, match in enumerate(results, 1):
                source_highlighted = match['source_text'].replace(
                    query, f"<span style='background-color: yellow;'>{query}</span>"
                )
                target_highlighted = match['target_text'].replace(
                    query, f"<span style='background-color: yellow;'>{query}</span>"
                )
                
                html += f"""
                <div style='border: 1px solid #ccc; padding: 10px; margin: 10px 0;'>
                    <p><strong>#{idx}</strong> - TM: {match['tm_id']} - Used: {match.get('usage_count', 0)} times</p>
                    <p><strong>Source:</strong> {source_highlighted}</p>
                    <p><strong>Target:</strong> {target_highlighted}</p>
                    <p style='color: #888; font-size: 9pt;'>Modified: {match.get('modified_date', 'N/A')}</p>
                </div>
                """
            
            self.search_results.setHtml(html)
            self.search_status.setText(f"Found {len(results)} matches")
            self.log(f"Concordance search: {len(results)} matches for '{query}'")
            
        except Exception as e:
            self.search_status.setText(f"Error: {str(e)}")
            self.log(f"Error in concordance search: {e}")
    
    def import_tmx(self):
        """Import a TMX file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select TMX File", "",
            "TMX Files (*.tmx);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        tm_id = self.import_tm_id.text().strip() or "imported"
        
        # Get source and target languages from parent app
        if hasattr(self.parent_app, 'current_project'):
            source_lang = self.parent_app.current_project.source_lang
            target_lang = self.parent_app.current_project.target_lang
        else:
            source_lang = "en"
            target_lang = "de"
        
        # Show progress bar
        self.import_progress.setValue(0)
        self.import_progress.setVisible(True)
        self.import_status.setText("Importing...")
        
        # Start import thread
        self.import_thread = TMXImportThread(file_path, self.db_manager, source_lang, target_lang, tm_id)
        self.import_thread.progress.connect(self.on_import_progress)
        self.import_thread.finished.connect(self.on_import_finished)
        self.import_thread.start()
    
    def on_import_progress(self, percent, message):
        """Update import progress"""
        self.import_progress.setValue(percent)
        self.import_status.setText(message)
    
    def on_import_finished(self, success, message, count):
        """Import finished"""
        self.import_progress.setVisible(False)
        self.import_status.setText(message)
        
        if success:
            QMessageBox.information(self, "Import Complete", f"{message}\n\nTotal entries: {count}")
            self._reload_browser_tm_combo()
            self.refresh_browser()
            self.refresh_stats()
        else:
            QMessageBox.critical(self, "Import Failed", message)
    
    def export_tmx(self):
        """Export TM to TMX file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save TMX File", "",
            "TMX Files (*.tmx);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            tm_filter = self.export_tm_selector.currentData()
            
            # Get entries to export
            if tm_filter == "all":
                self.db_manager.cursor.execute("SELECT * FROM translation_units")
            else:
                self.db_manager.cursor.execute("SELECT * FROM translation_units WHERE tm_id = ?", (tm_filter,))
            
            entries = [dict(row) for row in self.db_manager.cursor.fetchall()]
            
            if not entries:
                QMessageBox.warning(self, "No Entries", "No translation units to export")
                return
            
            # Create TMX
            tmx = ET.Element('tmx')
            tmx.set('version', '1.4')
            
            header = ET.SubElement(tmx, 'header')
            header.set('creationdate', datetime.now().strftime('%Y%m%dT%H%M%SZ'))
            header.set('srclang', 'en')
            header.set('adminlang', 'en')
            header.set('segtype', 'sentence')
            header.set('creationtool', 'Supervertaler')
            header.set('creationtoolversion', '4.0')
            header.set('datatype', 'plaintext')
            
            body = ET.SubElement(tmx, 'body')
            
            for entry in entries:
                tu = ET.SubElement(body, 'tu')
                
                # Source
                tuv_src = ET.SubElement(tu, 'tuv')
                tuv_src.set('xml:lang', entry.get('source_lang', 'en'))
                seg_src = ET.SubElement(tuv_src, 'seg')
                seg_src.text = entry['source_text']
                
                # Target
                tuv_tgt = ET.SubElement(tu, 'tuv')
                tuv_tgt.set('xml:lang', entry.get('target_lang', 'de'))
                seg_tgt = ET.SubElement(tuv_tgt, 'seg')
                seg_tgt.text = entry['target_text']
            
            # Write to file
            tree = ET.ElementTree(tmx)
            ET.indent(tree, space="  ")
            tree.write(file_path, encoding='utf-8', xml_declaration=True)
            
            self.export_status.setText(f"Exported {len(entries)} entries to {Path(file_path).name}")
            QMessageBox.information(self, "Export Complete", 
                                   f"Successfully exported {len(entries)} translation units")
            self.log(f"Exported {len(entries)} entries to {file_path}")
            
        except Exception as e:
            self.export_status.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Export Failed", f"Failed to export TMX:\n{str(e)}")
            self.log(f"Error exporting TMX: {e}")
    
    def refresh_stats(self):
        """Refresh TM statistics"""
        try:
            # Build TM filter clause
            tm_filter = ""
            params = []
            if self.filter_tm_ids:
                placeholders = ','.join('?' * len(self.filter_tm_ids))
                tm_filter = f" WHERE tm_id IN ({placeholders})"
                params = self.filter_tm_ids[:]
            
            # Get various statistics
            self.db_manager.cursor.execute(f"SELECT COUNT(*) FROM translation_units{tm_filter}", params)
            total_entries = self.db_manager.cursor.fetchone()[0]
            
            self.db_manager.cursor.execute(f"SELECT COUNT(DISTINCT tm_id) FROM translation_units{tm_filter}", params)
            tm_count = self.db_manager.cursor.fetchone()[0]
            
            query = f"""
                SELECT tm_id, COUNT(*) as count 
                FROM translation_units{tm_filter}
                GROUP BY tm_id 
                ORDER BY count DESC
            """
            self.db_manager.cursor.execute(query, params)
            tm_breakdown = self.db_manager.cursor.fetchall()
            
            query = f"""
                SELECT AVG(LENGTH(source_text)), AVG(LENGTH(target_text))
                FROM translation_units{tm_filter}
            """
            self.db_manager.cursor.execute(query, params)
            avg_lengths = self.db_manager.cursor.fetchone()
            
            # Handle empty TM (AVG returns None)
            avg_source = avg_lengths[0] if avg_lengths[0] is not None else 0
            avg_target = avg_lengths[1] if avg_lengths[1] is not None else 0
            
            # Format statistics
            stats_text = f"""
═══════════════════════════════════════════════
  TRANSLATION MEMORY STATISTICS
═══════════════════════════════════════════════

Total Translation Units: {total_entries:,}
Number of TMs: {tm_count}

Average Source Length: {avg_source:.1f} characters
Average Target Length: {avg_target:.1f} characters

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BREAKDOWN BY TM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            for tm_id, count in tm_breakdown:
                pct = (count / total_entries * 100) if total_entries > 0 else 0
                stats_text += f"{tm_id:20s} {count:8,} entries ({pct:5.1f}%)\n"
            
            self.stats_display.setPlainText(stats_text)
            self.log("TM statistics refreshed")
            
        except Exception as e:
            self.stats_display.setPlainText(f"Error loading statistics:\n{str(e)}")
            self.log(f"Error refreshing stats: {e}")
    
    def create_maintenance_tab(self):
        """Create maintenance/cleaning tab"""
        widget = QGroupBox()
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("<h3>🧹 TM Maintenance & Cleaning</h3>")
        layout.addWidget(header_label)
        
        info_label = QLabel(
            "Clean up your translation memory by removing duplicates and redundant entries.\n"
            "This helps keep your TM efficient and reduces clutter."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(info_label)
        
        # Duplicate cleaning section
        dup_group = QGroupBox("Duplicate Entry Cleaning")
        dup_layout = QVBoxLayout()
        
        # Option 1: Identical source + target
        dup1_layout = QHBoxLayout()
        dup1_desc = QLabel(
            "<b>Remove identical source + target pairs:</b><br>"
            "Deletes entries where both source and target text are exactly the same.<br>"
            "<i>Example: 'Hello' → 'Hello' (untranslated entries)</i>"
        )
        dup1_desc.setWordWrap(True)
        dup1_layout.addWidget(dup1_desc, 1)
        
        clean_identical_btn = QPushButton("🗑️ Clean")
        clean_identical_btn.setFixedWidth(100)
        clean_identical_btn.clicked.connect(self.clean_identical_source_target)
        dup1_layout.addWidget(clean_identical_btn)
        dup_layout.addLayout(dup1_layout)
        
        dup_layout.addWidget(QLabel(""))  # Spacer
        
        # Option 2: Identical source (keep newest)
        dup2_layout = QHBoxLayout()
        dup2_desc = QLabel(
            "<b>Remove duplicate sources (keep newest only):</b><br>"
            "For entries with identical source text, keeps only the most recent translation.<br>"
            "<i>Useful for removing outdated translations of the same source.</i>"
        )
        dup2_desc.setWordWrap(True)
        dup2_layout.addWidget(dup2_desc, 1)
        
        clean_duplicates_btn = QPushButton("🗑️ Clean")
        clean_duplicates_btn.setFixedWidth(100)
        clean_duplicates_btn.clicked.connect(self.clean_duplicate_sources)
        dup2_layout.addWidget(clean_duplicates_btn)
        dup_layout.addLayout(dup2_layout)
        
        dup_group.setLayout(dup_layout)
        layout.addWidget(dup_group)
        
        # Results display
        self.maintenance_results = QTextEdit()
        self.maintenance_results.setReadOnly(True)
        self.maintenance_results.setMaximumHeight(200)
        self.maintenance_results.setPlaceholderText("Cleaning results will appear here...")
        layout.addWidget(self.maintenance_results)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def clean_identical_source_target(self):
        """Remove entries where source and target are identical (background)."""
        reply = QMessageBox.question(
            self, "Confirm Cleaning",
            "This will delete all TM entries where the source and target text are identical.\n\n"
            "This action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._run_cleanup(
            mode=TMCleanupThread.MODE_IDENTICAL_PAIRS,
            dialog_title="Cleaning identical pairs",
            initial_label="Counting identical source/target pairs…",
            on_zero_text="✅ No identical source/target entries found. TM is clean!",
            success_template=(
                "✅ Cleaning Complete!\n\n"
                "Removed {deleted:,} entries where source = target\n\n"
                "These were likely untranslated entries or placeholders.\n"
                "Your TM is now cleaner and more efficient."
            ),
            log_template="Cleaned {deleted} identical source/target entries from TM",
        )

    def clean_duplicate_sources(self):
        """Remove duplicate sources, keep newest translation (background)."""
        reply = QMessageBox.question(
            self, "Confirm Cleaning",
            "This will find entries with identical source text and keep only the most recent translation.\n\n"
            "Older translations of the same source will be deleted.\n"
            "This action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._run_cleanup(
            mode=TMCleanupThread.MODE_DUPLICATE_SOURCES,
            dialog_title="Cleaning duplicate sources",
            initial_label="Finding duplicate sources…",
            on_zero_text="✅ No duplicate sources found. TM is clean!",
            success_template=(
                "✅ Cleaning Complete!\n\n"
                "Found {considered:,} sources with multiple translations\n"
                "Removed {deleted:,} older translations\n"
                "Kept the most recent translation for each source\n\n"
                "Your TM now has only the latest translations."
            ),
            log_template="Cleaned {deleted} duplicate source entries from TM (kept newest)",
        )

    def _run_cleanup(self, *, mode, dialog_title, initial_label, on_zero_text,
                     success_template, log_template):
        """Spin up a TMCleanupThread + QProgressDialog and wire the signals.

        Keeps the cleanup off the main thread so the UI stays responsive on
        large TMs. Cancellation is intentionally not offered: a partial
        cleanup mid-DELETE could leave the user wondering which rows
        survived. The progress dialog is informational only.
        """
        progress = QProgressDialog(initial_label, "", 0, 0, self)
        progress.setWindowTitle(dialog_title)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)  # no cancel – see docstring
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)

        thread = TMCleanupThread(
            db_path=self.db_manager.db_path,
            mode=mode,
            filter_tm_ids=self.filter_tm_ids,
        )

        def on_progress(done, total, msg):
            progress.setLabelText(msg)
            if total > 0:
                if progress.maximum() != total:
                    progress.setRange(0, total)
                progress.setValue(done)
            else:
                # Indeterminate – keep range (0,0)
                if progress.maximum() != 0 or progress.minimum() != 0:
                    progress.setRange(0, 0)

        def on_finished(success, error_msg, deleted, considered):
            progress.close()
            if not success:
                text = f"❌ Error during cleaning:\n{error_msg}"
                self.maintenance_results.setPlainText(text)
                QMessageBox.critical(self, "Cleaning Error", error_msg)
                return
            if deleted == 0 and considered == 0:
                self.maintenance_results.setPlainText(on_zero_text)
                return
            self.maintenance_results.setPlainText(
                success_template.format(deleted=deleted, considered=considered)
            )
            self.log(log_template.format(deleted=deleted))
            try:
                self.refresh_stats()
            except Exception:
                pass

        thread.progress.connect(on_progress)
        thread.finished.connect(on_finished)
        # Keep a reference so the thread isn't garbage-collected mid-run.
        self._cleanup_thread = thread
        thread.start()
