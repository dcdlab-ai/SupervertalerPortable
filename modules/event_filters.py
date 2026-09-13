# ============================================================================
# modules/event_filters.py — Qt event-фильтры уровня приложения.
#
# Содержимое перенесено ВЕРБАТИМ из монолита Supervertaler.py (Batch #3a,
# Step 3 of EXTRACTION_PLAN.md): _QuitEventFilter (Supervertaler.py:675),
# _WheelGuard (925), _LoneCtrlEventFilter (947), GridTableEventFilter (1041).
# Тела классов не изменялись; ленивые импорты внутри eventFilter сохранены
# как есть.
#
# _CtrlReturnEventFilter и _GridArrowKeyEventFilter перенесены НЕ были
# (решение владельца от 2026-09-13): они ссылаются на классы монолита
# ReadOnlyGridTextEditor / EditableGridTextEditor и хелпер _cleaned_modifiers;
# их перенос — после извлечения грид-редакторов (см. EXTRACTION_PLAN.md).
# ============================================================================
from PyQt6.QtCore import QObject, Qt


class _QuitEventFilter(QObject):
    """Фильтр уровня приложения: отличает настоящий выход из закрытия окна.

    v1.10.238: closeEvent главного окна сворачивает приложение в системный
    лоток/док (намеренное поведение «закрыть в трей»), а не завершает его,
    поэтому клик по крестику окна (Windows) или красной кнопке (macOS)
    оставляет Supervertaler работать — для глобальных хоткеев SuperLookup
    и Clipboard Manager.

    Но *явный* выход — «Quit Supervertaler» на macOS / ⌘Q или выключение
    системы — должен действительно завершать приложение. Эти события
    приходят как ``QEvent.Quit`` на объект приложения; увидев его, мы
    ставим ``main_window._really_quit``, чтобы последующий closeEvent
    принял закрытие и завершил процесс, а не спрятал окно. Событие мы не
    поглощаем, чтобы обычная последовательность выхода Qt продолжилась.
    """

    def __init__(self, main_window):
        super().__init__(main_window)
        self._main_window = main_window

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Quit:
            try:
                self._main_window._really_quit = True
            except Exception:
                pass
        return False


class _WheelGuard(QObject):
    """Не даёт виджету под курсором «съедать» колесо мыши.

    По умолчанию ``QSlider``, ``QAbstractSpinBox`` и ``QComboBox`` имеют
    ``Qt.FocusPolicy.WheelFocus`` и реагируют на колесо, когда курсор над
    ними — даже без клика. Из-за этого прокрутка страницы настроек может
    молча сдвинуть ползунок, которого вы не трогали. Фильтр ставится на такие
    виджеты и игнорирует их события колеса, ЕСЛИ виджет реально не имеет
    клавиатурного фокуса (т.е. пользователь в него не кликал и не переходил
    по Tab). Итог: прокрутка страницы работает как ожидается; явное
    взаимодействие — тоже.
    """

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Wheel:
            if not (hasattr(obj, "hasFocus") and obj.hasFocus()):
                event.ignore()
                return True
        return False


class _LoneCtrlEventFilter(QObject):
    """Фильтр уровня приложения: открывает всплывающий список вставки терминов
    при одиночном нажатии Ctrl.

    «Одиночное нажатие Ctrl» определяется как:
      - KeyPress Ctrl (без автоповтора)
      - KeyRelease Ctrl (без автоповтора)
      - без НИКАКОЙ другой клавиши, прокрутки колеса или сработавшего хоткея
        между ними

    Повторяет поведение memoQ, где одиночный Ctrl открывает список вставки
    из глоссария / непереводимых элементов. Любая другая клавиша, нажатая
    пока Ctrl удерживается (например, Ctrl+C, Ctrl+Shift+Q), отменяет
    распознавание, и обычный хоткей срабатывает как обычно.

    Три слоя отмены защищают от ложных срабатываний:
      1. KeyPress любой не-Ctrl клавиши -> немедленная отмена (обычные хоткеи)
      2. WheelEvent при удерживаемом Ctrl -> отмена (зум Ctrl+прокрутка)
      3. Событие ShortcutOverride -> отмена (зарегистрированные QShortcut,
         чьё событие клавиши может быть поглощено до слоя 1)
      4. queryKeyboardModifiers() при отпускании Ctrl -> отмена, если удерживается
         любой другой модификатор (перехватывает системные хоткеи, глотающие
         промежуточные клавиши, например Ctrl+Alt+Dash в методах ввода Windows)
    """

    def __init__(self, main_window):
        super().__init__(main_window)
        self._main_window = main_window
        self._ctrl_pressed_alone = False

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QApplication

        try:
            if not self._main_window or not self._main_window.isActiveWindow():
                return False

            etype = event.type()

            # ── Слой 2: Ctrl+колесо (зум и т.п.) ──────────────────────────────
            if etype == QEvent.Type.Wheel:
                self._ctrl_pressed_alone = False
                return False

            # ── Слой 3: зарегистрированный QShortcut вот-вот сработает ────────
            # ShortcutOverride отправляется виджету в фокусе непосредственно
            # перед активацией хоткея; он приходит даже когда последующее
            # событие KeyPress поглощается, так что ловим здесь хоткеи
            # Ctrl+= / Ctrl+- / Ctrl+Alt+…
            if etype == QEvent.Type.ShortcutOverride:
                self._ctrl_pressed_alone = False
                return False

            # ── Слой 1: нажатия клавиш ────────────────────────────────────────
            if etype == QEvent.Type.KeyPress:
                if event.isAutoRepeat():
                    self._ctrl_pressed_alone = False
                    return False
                if event.key() == Qt.Key.Key_Control:
                    self._ctrl_pressed_alone = True
                else:
                    self._ctrl_pressed_alone = False
                return False

            # ── Отпускание Ctrl: срабатываем, только если все слои согласны ───
            if etype == QEvent.Type.KeyRelease:
                if event.key() == Qt.Key.Key_Control and not event.isAutoRepeat():
                    if self._ctrl_pressed_alone:
                        # Слой 4: живое состояние модификаторов ОС — ловит хоткеи,
                        # поглощённые системой (например, комбинации AltGr/Ctrl+Alt,
                        # съедающие промежуточные клавиши)
                        live = QApplication.queryKeyboardModifiers()
                        other = live & ~Qt.KeyboardModifier.ControlModifier
                        if other == Qt.KeyboardModifier.NoModifier:
                            self._ctrl_pressed_alone = False
                            self._main_window.show_term_insert_popup()
                            return True   # поглощаем это событие отпускания
                    self._ctrl_pressed_alone = False
                return False

            return False

        except RuntimeError:
            # C++-объект главного окна удалён (приложение завершается).
            # Снимаем фильтр, чтобы он больше не срабатывал, и замолкаем.
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self)
            self._main_window = None
            self._ctrl_pressed_alone = False
            return False


class GridTableEventFilter:
    """Примесь для передачи хоткеев из редактора в таблицу"""
    pass
