# Файл создан механическим переносом из Supervertaler.py (Batch #3b, Step 3 EXTRACTION_PLAN.md).
# Тело класса перенесено ВЕРБАТИМ — не редактировать без отдельного решения.

import time

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QFont, QTextCursor
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QVBoxLayout

class LiveProgressDialog(QDialog):
    """Диалог прогресса с живым выводом консоли."""
    
    def __init__(self, parent, total_segments, provider_info):
        super().__init__(parent)
        self.total_segments = total_segments
        self.provider_info = provider_info
        self.start_time = time.time()
        self.segment_times = []  # Track processing times for estimation
        
        self.setWindowTitle(self.tr("Batch Translation Progress"))
        self.setMinimumSize(800, 600)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(f"<h3>🚀 Translating {total_segments} segment{'s' if total_segments != 1 else ''}</h3>")
        layout.addWidget(header_label)
        
        # Provider info
        provider_label = QLabel(provider_info)
        provider_label.setStyleSheet("color: #666; padding: 5px 0;")
        layout.addWidget(provider_label)
        
        # Progress info section
        info_layout = QHBoxLayout()
        self.progress_label = QLabel("0/0 (0%)")
        self.time_label = QLabel(self.tr("Elapsed: 0:00 | Remaining: --:--"))
        self.speed_label = QLabel(self.tr("Speed: -- seg/min"))
        info_layout.addWidget(self.progress_label)
        info_layout.addStretch()
        info_layout.addWidget(self.time_label)
        info_layout.addWidget(self.speed_label)
        layout.addLayout(info_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(total_segments)
        layout.addWidget(self.progress_bar)
        
        # Console output
        console_label = QLabel(self.tr("<b>Console Output:</b>"))
        layout.addWidget(console_label)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 9))
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        layout.addWidget(self.console)
        
        # Statistics
        self.stats_label = QLabel(self.tr("✓ Success: 0  |  ✗ Errors: 0"))
        self.stats_label.setStyleSheet("padding: 5px 0; font-weight: bold;")
        layout.addWidget(self.stats_label)
        
        # Button section
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton(self.tr("Cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Timer for elapsed time updates
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time_display)
        self.timer.start(1000)  # Update every second
        
        # Initial console message
        self.add_console_line(f"Starting batch translation: {total_segments} segments", True)
        self.add_console_line(provider_info, True)
        self.add_console_line("-" * 80, True)
    
    def add_console_line(self, message, is_success=True):
        """Добавляет строку в консоль с цветовой кодировкой."""
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Set text color
        fmt = cursor.charFormat()
        if is_success:
            fmt.setForeground(QColor("#4ec9b0"))  # Greenish (VS Code style)
        else:
            fmt.setForeground(QColor("#f48771"))  # Reddish (VS Code style)
        
        cursor.setCharFormat(fmt)
        cursor.insertText(message + "\n")
        
        # Auto-scroll to bottom
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()
    
    def update_progress(self, current, total, elapsed_seconds, success_count, error_count):
        """Обновляет полосу прогресса и подписи."""
        self.progress_bar.setValue(current)
        
        # Update progress label
        percent = int((current / total) * 100) if total > 0 else 0
        self.progress_label.setText(f"{current}/{total} ({percent}%)")
        
        # Update statistics
        self.stats_label.setText(f"✓ Success: {success_count}  |  ✗ Errors: {error_count}")
        
        # Track timing
        if elapsed_seconds > 0:
            self.segment_times.append(elapsed_seconds)
        
        # Calculate speed and estimate remaining time
        if len(self.segment_times) > 0:
            avg_time = sum(self.segment_times) / len(self.segment_times)
            speed = 60 / avg_time if avg_time > 0 else 0
            remaining_segments = total - current
            remaining_seconds = remaining_segments * avg_time
            
            # Update labels
            self.speed_label.setText(f"Speed: {speed:.1f} seg/min")
            
            remaining_str = self._format_time(remaining_seconds)
            elapsed_str = self._format_time(time.time() - self.start_time)
            self.time_label.setText(f"Elapsed: {elapsed_str} | Remaining: {remaining_str}")
    
    def _update_time_display(self):
        """Обновляет показ прошедшего времени (вызывается раз в секунду)."""
        if self.progress_bar.value() < self.total_segments:
            elapsed = time.time() - self.start_time
            current_text = self.time_label.text()
            # Update only elapsed portion
            if " | " in current_text:
                remaining_part = current_text.split(" | ")[1]
                self.time_label.setText(f"Elapsed: {self._format_time(elapsed)} | {remaining_part}")
    
    @staticmethod
    def _format_time(seconds):
        """Форматирует секунды как ММ:СС."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def show_completion_message(self, success_count, error_count):
        """Показывает итоговое сообщение о завершении в консоли."""
        self.add_console_line("", True)  # Blank line
        self.add_console_line("=" * 80, True)
        self.add_console_line(f"Translation Complete!", True)
        self.add_console_line(f"✓ Success: {success_count}", True)
        if error_count > 0:
            self.add_console_line(f"✗ Errors: {error_count}", False)
        total_time = time.time() - self.start_time
        self.add_console_line(f"Total time: {self._format_time(total_time)}", True)
        self.add_console_line("=" * 80, True)
        
        # Change button to "Close"
        self.cancel_btn.setText(self.tr("Close"))
