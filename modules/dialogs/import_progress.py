# Файл создан механическим переносом из Supervertaler.py (Batch #3b, Step 3 EXTRACTION_PLAN.md).
# Тело класса перенесено ВЕРБАТИМ — не редактировать без отдельного решения.

from contextlib import contextmanager

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QProgressDialog

# ============================================================================
# IMPORT PROGRESS DIALOG (shared helper)
# ============================================================================
# v1.10.150: centralises the boilerplate every import_* method used to copy
# around a QProgressDialog. Historically each path reinvented this, with
# inconsistent results — three were correct, four created a dialog that
# closed before the slow grid-load phase (so the user saw "Not Responding"
# for ~30 s), and eleven had no dialog at all. This wrapper makes correct
# behaviour the default: the dialog spans the entire pipeline, every phase
# pumps the Qt event loop so the OS never marks the app unresponsive, and
# the helper exposes callbacks shaped for both the parser-style protocol
# (stage/current/total/message → continue_bool) and load_segments_to_grid
# (rows_done, total).
# ============================================================================

class _ImportProgressDialog:
    """Диалог прогресса, управляемый как контекстный менеджер и покрывающий весь конвейер импорта.
    
    Пример использования::
    
        with _ImportProgressDialog(self, "Importing SDLXLIFF",
                                    initial_label=f"Opening {name}…",
                                    initial_total=len(file_paths)) as prog:
            handler.load(file_paths, progress_callback=prog.parse_callback)
            if prog.cancelled():
                return
            with prog.suspended():
                reply = QMessageBox.question(self, …)
            prog.set_phase(f"Loading {n} segments into grid…", total=n)
            self.load_segments_to_grid(progress_callback=prog.grid_callback)
            prog.set_phase("Finalising import…")
            …"""

    def __init__(self, parent, title: str = "Importing",
                 initial_label: str = "Working…",
                 initial_total: int = 1):
        self._parent = parent
        self._title = title
        self._initial_label = initial_label
        self._initial_total = max(int(initial_total), 1)
        self._dialog = None

    def __enter__(self):
        self._dialog = QProgressDialog(
            self._initial_label, "Cancel", 0, self._initial_total, self._parent
        )
        self._dialog.setWindowTitle(self._title)
        self._dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._dialog.setMinimumDuration(0)
        self._dialog.setAutoClose(False)
        self._dialog.setAutoReset(False)
        self._dialog.setValue(0)
        QApplication.processEvents()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._dialog is not None:
            try:
                self._dialog.close()
            except Exception:
                pass
            self._dialog = None
        return False  # propagate exceptions

    # --- state ----------------------------------------------------------------

    def cancelled(self) -> bool:
        return self._dialog is not None and self._dialog.wasCanceled()

    # --- phase control --------------------------------------------------------

    def set_phase(self, label: str, total: int = 0) -> None:
        """Начинает новую фазу. ``total=0`` переводит индикатор в неопределённый
        (занят) режим; любое положительное значение задаёт определённый диапазон
        с прогрессом 0."""
        if self._dialog is None:
            return
        if total > 0:
            self._dialog.setRange(0, int(total))
            self._dialog.setValue(0)
        else:
            self._dialog.setRange(0, 0)  # busy/indeterminate
        self._dialog.setLabelText(label)
        QApplication.processEvents()

    def update(self, value: int, total: int = None, label: str = None) -> bool:
        """Обновляет прогресс. Возвращает ``False``, если пользователь отменил."""
        if self._dialog is None:
            return True
        if self.cancelled():
            return False
        if total is not None and total > 0:
            self._dialog.setRange(0, int(total))
        self._dialog.setValue(int(value))
        if label is not None:
            self._dialog.setLabelText(label)
        QApplication.processEvents()
        return not self.cancelled()

    # --- ready-made callbacks for common producers ---------------------------

    def parse_callback(self, stage: str, current: int, total: int,
                       message: str) -> bool:
        """Обратный вызов по протоколу (stage, current, total, message) -> continue,
        который используют StandaloneSDLXLIFFHandler.load и подобные."""
        if self._dialog is None:
            return False
        if self.cancelled():
            return False
        self._dialog.setRange(0, max(int(total), 1))
        self._dialog.setValue(int(current))
        label = f"{message} ({current}/{total})" if total else message
        self._dialog.setLabelText(label)
        QApplication.processEvents()
        return not self.cancelled()

    def grid_callback(self, rows_done: int, total: int) -> None:
        """Обратный вызов по протоколу (rows_done, total), который использует
        ``SupervertalerQt.load_segments_to_grid``."""
        if self._dialog is None:
            return
        if self.cancelled():
            return
        self._dialog.setValue(int(rows_done))
        self._dialog.setLabelText(
            f"Loading segments into grid… ({rows_done:,}/{total:,})"
        )
        QApplication.processEvents()

    # --- suspend (для вложенных модальных диалогов) ------------------------------

    @contextmanager
    def suspended(self):
        """Временно прячет диалог (например, для ``QMessageBox.question``, на который
        пользователь должен ответить посреди импорта) и возвращает его на выходе."""
        if self._dialog is not None:
            self._dialog.hide()
        try:
            yield
        finally:
            if self._dialog is not None:
                self._dialog.show()
                QApplication.processEvents()
