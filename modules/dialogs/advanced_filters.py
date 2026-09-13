# Файл создан механическим переносом из Supervertaler.py (Batch #3b, Step 3 EXTRACTION_PLAN.md).
# Тело класса перенесено ВЕРБАТИМ — не редактировать без отдельного решения.

from modules.styled_widgets import CheckmarkCheckBox, CheckmarkRadioButton

from PyQt6.QtWidgets import QDialog, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget

class AdvancedFiltersDialog(QDialog):
    """Диалог расширенных параметров фильтрации."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(self.tr("Advanced Filters"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        layout = QVBoxLayout(self)
        
        # Create scroll area for filters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)
        
        # Match Rate Filter
        match_group = QGroupBox(self.tr("Match Rate (%)"))
        match_layout = QHBoxLayout()
        
        self.match_rate_check = CheckmarkCheckBox(self.tr("Enable"))
        match_layout.addWidget(self.match_rate_check)
        
        match_layout.addWidget(QLabel(self.tr("From:")))
        self.match_min_spin = QSpinBox()
        self.match_min_spin.setRange(0, 102)
        self.match_min_spin.setValue(0)
        self.match_min_spin.setSuffix("%")
        match_layout.addWidget(self.match_min_spin)
        
        match_layout.addWidget(QLabel(self.tr("To:")))
        self.match_max_spin = QSpinBox()
        self.match_max_spin.setRange(0, 102)
        self.match_max_spin.setValue(102)
        self.match_max_spin.setSuffix("%")
        match_layout.addWidget(self.match_max_spin)
        match_layout.addStretch()
        
        match_group.setLayout(match_layout)
        content_layout.addWidget(match_group)
        
        # Row Status Filter
        status_group = QGroupBox(self.tr("Row Status"))
        status_layout = QVBoxLayout()
        
        self.status_not_started = CheckmarkCheckBox(self.tr("Not started"))
        self.status_edited = CheckmarkCheckBox(self.tr("Edited"))
        self.status_pretranslated = CheckmarkCheckBox(self.tr("Pre-translated"))
        self.status_translated = CheckmarkCheckBox(self.tr("Translated"))
        self.status_confirmed = CheckmarkCheckBox(self.tr("Confirmed"))
        self.status_draft = CheckmarkCheckBox(self.tr("Draft"))

        status_layout.addWidget(self.status_not_started)
        status_layout.addWidget(self.status_edited)
        status_layout.addWidget(self.status_pretranslated)
        status_layout.addWidget(self.status_translated)
        status_layout.addWidget(self.status_confirmed)
        status_layout.addWidget(self.status_draft)

        # Match Origin statuses
        match_origin_label = QLabel(self.tr("Match Origin"))
        match_origin_label.setStyleSheet("font-weight: bold; color: #666; margin-top: 8px; margin-bottom: 2px;")
        status_layout.addWidget(match_origin_label)

        self.status_pm = CheckmarkCheckBox(self.tr("PM (102%)"))
        self.status_cm = CheckmarkCheckBox(self.tr("CM (101%)"))
        self.status_tm_100 = CheckmarkCheckBox(self.tr("TM 100%"))
        self.status_tm_fuzzy = CheckmarkCheckBox(self.tr("TM Fuzzy"))
        self.status_repetition = CheckmarkCheckBox(self.tr("Repetition"))
        self.status_mt = CheckmarkCheckBox(self.tr("MT"))

        status_layout.addWidget(self.status_pm)
        status_layout.addWidget(self.status_cm)
        status_layout.addWidget(self.status_tm_100)
        status_layout.addWidget(self.status_tm_fuzzy)
        status_layout.addWidget(self.status_repetition)
        status_layout.addWidget(self.status_mt)

        status_group.setLayout(status_layout)
        content_layout.addWidget(status_group)
        
        # Locked/Unlocked Filter
        locked_group = QGroupBox(self.tr("Locked Status"))
        locked_layout = QVBoxLayout()
        
        self.locked_both = CheckmarkRadioButton(self.tr("Both locked and unlocked rows"))
        self.locked_only = CheckmarkRadioButton(self.tr("Only locked rows"))
        self.locked_unlocked_only = CheckmarkRadioButton(self.tr("Only unlocked rows"))
        self.locked_both.setChecked(True)
        
        locked_layout.addWidget(self.locked_both)
        locked_layout.addWidget(self.locked_only)
        locked_layout.addWidget(self.locked_unlocked_only)
        
        locked_group.setLayout(locked_layout)
        content_layout.addWidget(locked_group)
        
        # Other Properties
        other_group = QGroupBox(self.tr("Other Properties"))
        other_layout = QVBoxLayout()
        
        self.has_comments_check = CheckmarkCheckBox(self.tr("Has comments/notes"))
        self.has_proofreading_check = CheckmarkCheckBox(self.tr("Has proofreading issues"))
        self.repetitions_check = CheckmarkCheckBox(self.tr("Repetitions only"))
        self.auto_propagated_check = CheckmarkCheckBox(self.tr("Auto-propagated"))
        
        other_layout.addWidget(self.has_comments_check)
        other_layout.addWidget(self.has_proofreading_check)
        other_layout.addWidget(self.repetitions_check)
        other_layout.addWidget(self.auto_propagated_check)
        
        other_group.setLayout(other_layout)
        content_layout.addWidget(other_group)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        reset_btn = QPushButton(self.tr("Reset All"))
        reset_btn.clicked.connect(self.reset_filters)
        button_layout.addWidget(reset_btn)
        
        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton(self.tr("Apply Filters"))
        apply_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px 15px; border: none; outline: none;")
        apply_btn.clicked.connect(self.accept)
        apply_btn.setDefault(True)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
    
    def reset_filters(self):
        """Сбрасывает все фильтры к значениям по умолчанию."""
        self.match_rate_check.setChecked(False)
        self.match_min_spin.setValue(0)
        self.match_max_spin.setValue(102)

        self.status_not_started.setChecked(False)
        self.status_edited.setChecked(False)
        self.status_pretranslated.setChecked(False)
        self.status_translated.setChecked(False)
        self.status_confirmed.setChecked(False)
        self.status_draft.setChecked(False)
        self.status_pm.setChecked(False)
        self.status_cm.setChecked(False)
        self.status_tm_100.setChecked(False)
        self.status_tm_fuzzy.setChecked(False)
        self.status_repetition.setChecked(False)
        self.status_mt.setChecked(False)
        
        self.locked_both.setChecked(True)
        
        self.has_comments_check.setChecked(False)
        self.has_proofreading_check.setChecked(False)
        self.repetitions_check.setChecked(False)
        self.auto_propagated_check.setChecked(False)
    
    def get_filters(self):
        """Возвращает словарь настроек фильтров."""
        filters = {}
        
        # Match rate
        filters['match_rate_enabled'] = self.match_rate_check.isChecked()
        filters['match_rate_min'] = self.match_min_spin.value()
        filters['match_rate_max'] = self.match_max_spin.value()
        
        # Row status
        row_status = []
        if self.status_not_started.isChecked():
            row_status.append('not_started')
        if self.status_edited.isChecked():
            row_status.append('edited')
        if self.status_pretranslated.isChecked():
            row_status.append('pretranslated')
        if self.status_translated.isChecked():
            row_status.append('draft')
        if self.status_confirmed.isChecked():
            row_status.append('confirmed')
        if self.status_draft.isChecked():
            row_status.append('draft')
        if self.status_pm.isChecked():
            row_status.append('pm')
        if self.status_cm.isChecked():
            row_status.append('cm')
        if self.status_tm_100.isChecked():
            row_status.append('tm_100')
        if self.status_tm_fuzzy.isChecked():
            row_status.append('tm_fuzzy')
        if self.status_repetition.isChecked():
            row_status.append('repetition')
        if self.status_mt.isChecked():
            row_status.append('machine_translated')
        filters['row_status'] = row_status
        
        # Locked filter
        if self.locked_only.isChecked():
            filters['locked_filter'] = 'locked'
        elif self.locked_unlocked_only.isChecked():
            filters['locked_filter'] = 'unlocked'
        else:
            filters['locked_filter'] = None
        
        # Other properties
        filters['has_comments'] = self.has_comments_check.isChecked()
        filters['has_proofreading'] = self.has_proofreading_check.isChecked()
        filters['repetitions_only'] = self.repetitions_check.isChecked()
        filters['auto_propagated'] = self.auto_propagated_check.isChecked()
        
        return filters
