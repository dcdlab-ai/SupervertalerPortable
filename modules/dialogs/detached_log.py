# Файл создан механическим переносом из Supervertaler.py (Batch #3b, Step 3 EXTRACTION_PLAN.md).
# Тело класса перенесено ВЕРБАТИМ — не редактировать без отдельного решения.


from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

# ============================================================================
# DETACHED LOG WINDOW
# ============================================================================

class DetachedLogWindow(QWidget):
    """Отдельное окно журнала, которое можно переместить на другой экран."""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setWindowTitle(self.tr("Supervertaler Workbench - Session Log"))
        self.setWindowIcon(self.parent.windowIcon())
        self.resize(800, 600)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Top toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # Info label
        info_label = QLabel(self.tr("📋 This is a detached log window. It will update in real-time."))
        info_label.setStyleSheet("color: #666; font-style: italic;")
        toolbar_layout.addWidget(info_label)

        toolbar_layout.addStretch()

        # Re-attach button
        reattach_btn = QPushButton(self.tr("↩️ Close"))
        reattach_btn.setToolTip(self.tr("Close this detached window"))
        reattach_btn.clicked.connect(self.close)
        toolbar_layout.addWidget(reattach_btn)

        layout.addWidget(toolbar)

        # Log display
        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid #ccc;
            }
        """)
        layout.addWidget(self.log_display)

        # Copy existing log content. Prefer the always-built session_log_text
        # buffer; fall back to the Settings ▸ Log widget if that path ran first.
        source_widget = None
        if hasattr(parent, 'session_log_text') and parent.session_log_text:
            source_widget = parent.session_log_text
        elif hasattr(parent, 'session_log') and parent.session_log:
            source_widget = parent.session_log
        if source_widget is not None:
            self.log_display.setPlainText(source_widget.toPlainText())
            # Scroll to bottom
            scrollbar = self.log_display.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """Обрабатывает закрытие окна."""
        # Remove from parent's list
        try:
            if self in self.parent.detached_log_windows:
                self.parent.detached_log_windows.remove(self)
        except:
            pass
        event.accept()
