# Файл создан механическим переносом из Supervertaler.py (Batch #3b, Step 3 EXTRACTION_PLAN.md).
# Тело класса перенесено ВЕРБАТИМ — не редактировать без отдельного решения.


from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout

class ScratchpadDialog(QDialog):
    """Диалог личных заметок переводчика (черновик).
    
    Заметки хранятся только в файле .svproj и никогда не экспортируются в CAT-инструменты."""
    
    def __init__(self, parent=None, notes_text: str = ""):
        super().__init__(parent)
        self.notes_text = notes_text
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(self.tr("📝 Scratchpad - Private Notes"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.resize(600, 450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Info label
        info_label = QLabel(
            "📝 <b>Private notes for this project</b><br>"
            "<small>These notes are saved with your project (.svproj) file and are <b>never</b> "
            "exported to CAT tools or shared with clients.</small>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 5px; background: #f9f9f9; border-radius: 4px;")
        layout.addWidget(info_label)
        
        # Notes text area
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlainText(self.notes_text)
        self.notes_edit.setPlaceholderText(
            "Use this scratchpad for your private notes during translation:\n\n"
            "• Terminology decisions\n"
            "• Client preferences\n"
            "• Research findings\n"
            "• Questions to ask\n"
            "• Reminders for yourself"
        )
        # Nice monospace-ish font for notes
        font = self.notes_edit.font()
        font.setFamily("Consolas, Courier New, monospace")
        font.setPointSize(10)
        self.notes_edit.setFont(font)
        layout.addWidget(self.notes_edit, 1)  # Stretch to fill
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton(self.tr("💾 Save Notes"))
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 16px; border: none;")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def get_notes(self) -> str:
        """Возвращает текущий текст заметок."""
        return self.notes_edit.toPlainText()
