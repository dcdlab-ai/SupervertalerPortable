"""Shared styled widgets used across Supervertaler.

Currently a single class – :class:`CheckmarkCheckBox` – that previously
existed as nine near-identical copies scattered through the codebase.
Designed to grow into the home for any other custom-styled widget that
needs to be reused in three or more places.

If you tweak the look of one of these widgets, the change applies
everywhere automatically. Don't paste local copies back into other files.
"""
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush
from PyQt6.QtWidgets import QCheckBox, QPushButton, QRadioButton, QStyleOptionButton


class CheckmarkCheckBox(QCheckBox):
    """Standard Supervertaler styled checkbox.

    16×16 rounded indicator, white background unchecked, green fill
    (Material 500 / hover 600) when checked, with a manually-painted
    white checkmark so the visual is consistent across platforms (Qt's
    default checkmark glyph differs between Windows / macOS / Linux
    styles and at small sizes can render too thin or be cut off).
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setEnabled(True)
        self.setStyleSheet("""
            QCheckBox {
                font-size: 9pt;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #999;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QCheckBox::indicator:hover {
                border-color: #666;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #45a049;
                border-color: #45a049;
            }
        """)

    def paintEvent(self, event):
        """Draw a white checkmark on top of the indicator when checked."""
        super().paintEvent(event)
        if not self.isChecked():
            return

        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        indicator_rect = self.style().subElementRect(
            self.style().SubElement.SE_CheckBoxIndicator, opt, self
        )
        if not indicator_rect.isValid():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen_width = max(
                2.0,
                min(indicator_rect.width(), indicator_rect.height()) * 0.12,
            )
            painter.setPen(QPen(
                QColor(255, 255, 255), pen_width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            ))
            painter.setBrush(QColor(255, 255, 255))

            x = indicator_rect.x()
            y = indicator_rect.y()
            w = indicator_rect.width()
            h = indicator_rect.height()

            # 15% padding so the checkmark sits comfortably inside
            # the indicator square at small sizes.
            padding = min(w, h) * 0.15
            x += padding
            y += padding
            w -= padding * 2
            h -= padding * 2

            # Two-segment checkmark – start lower-left, dip to bottom,
            # rise to upper-right.
            check_x1 = x + w * 0.10
            check_y1 = y + h * 0.50
            check_x2 = x + w * 0.35
            check_y2 = y + h * 0.70
            check_x3 = x + w * 0.90
            check_y3 = y + h * 0.25

            painter.drawLine(QPointF(check_x2, check_y2), QPointF(check_x3, check_y3))
            painter.drawLine(QPointF(check_x1, check_y1), QPointF(check_x2, check_y2))
        finally:
            painter.end()


class PurpleCheckmarkCheckBox(CheckmarkCheckBox):
    """Purple-themed variant of :class:`CheckmarkCheckBox` – same
    geometry, same hand-painted white checkmark, just a deeper purple
    fill (Material 500 / hover 700) instead of the green default.
    Used by the voice-dictation-bias UI:

      - Termbase Manager → 🎤 Voice column (one per termbase)
      - Voice tab → "Also bias from your termbases" toggle

    Both UI surfaces drive the same feature (per-termbase voice-
    dictation vocabulary biasing); using the same colour keeps the
    visual identity consistent so users can connect them at a glance.

    The CheckmarkCheckBox parent class handles the paintEvent that
    draws the white checkmark – we only need to override the stylesheet
    to swap the green for purple. The unchecked-state border is
    bumped from #999 to #888 so the box reads as a deliberate UI
    element rather than the faded "barely-there" look of the bare
    QCheckBox unchecked state on white backgrounds.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QCheckBox {
                font-size: 9pt;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #888;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #9C27B0;
                border-color: #9C27B0;
            }
            QCheckBox::indicator:hover {
                border-color: #555;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #7B1FA2;
                border-color: #7B1FA2;
            }
        """)


class TealCheckmarkCheckBox(CheckmarkCheckBox):
    """Teal-themed variant of :class:`CheckmarkCheckBox` – same geometry
    and hand-painted white checkmark, with a teal fill (Material 500 /
    hover 700) instead of green.

    Used by the **SuperLookup** column in the TMs and Termbases tabs: a
    per-resource toggle controlling whether that TM / termbase is
    searched by SuperLookup. It is deliberately independent of the
    Read flag, so the colour is deliberately distinct from Read (green),
    Write (blue), Bridge/AI (orange), Project (pink) and Voice (purple) –
    one glance tells you which switch you're looking at.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QCheckBox {
                font-size: 9pt;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #888;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #009688;
                border-color: #009688;
            }
            QCheckBox::indicator:hover {
                border-color: #555;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #00796B;
                border-color: #00796B;
            }
        """)


class HelpButton(QPushButton):
    """A small, unobtrusive "?" button that opens the relevant help page.

    Mirrors the Trados plugin's context-sensitive help convention: a
    small flat "?" sits in the top-right of every dialog / section /
    tab and one click takes the user to that section's GitBook page.

    Usage::

        from modules.styled_widgets import HelpButton
        from modules.help_system import Topics

        # Drop into a horizontal row at the top-right of a section:
        header = QHBoxLayout()
        header.addWidget(QLabel("Always-On Listening"))
        header.addStretch()
        header.addWidget(HelpButton(Topics.AUTOFINGERS))

    Pairs with :func:`modules.help_system.set_topic` for F1 support –
    F1 already walks the widget tree to find the nearest tagged
    ancestor, so adding a HelpButton AND tagging the same widget gives
    users two equivalent paths to the same documentation page.

    Args:
        topic: A topic identifier from :class:`modules.help_system.Topics`
            (or any path string ``open_help`` accepts). Click → opens
            ``DOCS_BASE_URL/<topic>`` in the user's default browser.
        tooltip: Optional override for the hover tooltip. Defaults to
            ``"Open help for this section"``.
    """

    def __init__(self, topic: str, tooltip: str = None, parent=None):
        super().__init__("?", parent)
        self._topic = topic
        # Compact size; matches the visual weight of the Trados-side button.
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip or "Open help for this section")
        # Don't grab tab focus – the button is supplementary navigation,
        # not part of the form's tab order.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Flat circular grey button, slightly bolder text on hover.
        self.setStyleSheet("""
            QPushButton {
                font-size: 10pt;
                font-weight: bold;
                color: #666;
                background-color: transparent;
                border: 1px solid #BBB;
                border-radius: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #222;
                background-color: #EEE;
                border-color: #888;
            }
            QPushButton:pressed {
                background-color: #DDD;
            }
        """)
        self.clicked.connect(self._open)

    def _open(self):
        # Lazy import to avoid a circular dependency at module import time
        # (help_system currently doesn't pull styled_widgets, but the
        # contract is intentionally one-way).
        from modules.help_system import open_help
        open_help(self._topic)

    @property
    def topic(self) -> str:
        return self._topic

    def set_topic(self, topic: str):
        """Re-target an existing button at a different help page."""
        self._topic = topic


class CheckmarkRadioButton(QRadioButton):
    """Standard Supervertaler styled radio button.

    Matches :class:`CheckmarkCheckBox` (same 16px indicator, green-when-checked
    look) but round, with a manually-painted white centre dot so the checked
    state is clearly visible under the app theme — raw QRadioButton renders an
    empty indicator here.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QRadioButton {
                font-size: 9pt;
                spacing: 6px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #999;
                border-radius: 9px;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QRadioButton::indicator:hover {
                border-color: #666;
            }
            QRadioButton::indicator:checked:hover {
                background-color: #45a049;
                border-color: #45a049;
            }
        """)

    def paintEvent(self, event):
        """Draw a white centre dot on top of the indicator when checked."""
        super().paintEvent(event)
        if not self.isChecked():
            return

        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        indicator_rect = self.style().subElementRect(
            self.style().SubElement.SE_RadioButtonIndicator, opt, self
        )
        if not indicator_rect.isValid():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor("white")))
            painter.setPen(Qt.PenStyle.NoPen)
            center = indicator_rect.center()
            center_pt = QPointF(center.x(), center.y())
            radius = indicator_rect.width() * 0.25
            painter.drawEllipse(center_pt, radius, radius)
        finally:
            painter.end()


# ---------------------------------------------------------------------------
# Цветные варианты чекбокса (Batch #3c, Step 3 EXTRACTION_PLAN.md).
#
# Монолит нёс Pink/Blue/Orange-копии CheckmarkCheckBox, чьи тела отличались
# от базового класса только четырьмя hex-значениями в stylesheet (проверено
# гейтом 1.4 Batch #3c: 12 offscreen-сценариев рендера пиксельно идентичны,
# отличия stylesheet — ровно 4 подстановки цвета). Тела paintEvent не
# дублируются: используется единственный CheckmarkCheckBox.paintEvent, цвета
# задаются двумя class-атрибутами через шаблон ниже.
# ---------------------------------------------------------------------------

_CHECKMARK_COLOR_STYLESHEET = """
            QCheckBox {
                font-size: 9pt;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #999;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: @CHECKED@;
                border-color: @CHECKED@;
            }
            QCheckBox::indicator:hover {
                border-color: #666;
            }
            QCheckBox::indicator:checked:hover {
                background-color: @CHECKED_HOVER@;
                border-color: @CHECKED_HOVER@;
            }
        """


class _ColoredCheckmarkCheckBox(CheckmarkCheckBox):
    """Приватная база цветных вариантов :class:`CheckmarkCheckBox`.

    Сигнатура конструктора ``__init__(text="", parent=None)`` наследуется от
    базового класса; переопределяется только stylesheet с подстановкой двух
    цветов. Белая галочка рисуется унаследованным paintEvent.
    """

    _checked_color = None        # checked: заливка + рамка индикатора
    _checked_hover_color = None  # checked+hover: заливка + рамка

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            _CHECKMARK_COLOR_STYLESHEET
            .replace("@CHECKED@", self._checked_color)
            .replace("@CHECKED_HOVER@", self._checked_hover_color)
        )


class PinkCheckmarkCheckBox(_ColoredCheckmarkCheckBox):
    """Чекбокс с розовым фоном и белой галочкой в отмеченном состоянии (для термбаз проекта)."""

    _checked_color = "#FFB6C1"
    _checked_hover_color = "#FF99AD"


class BlueCheckmarkCheckBox(_ColoredCheckmarkCheckBox):
    """Чекбокс с синим фоном и белой галочкой в отмеченном состоянии (для глобальных/фоновых термбаз)."""

    _checked_color = "#4d94ff"
    _checked_hover_color = "#3d7dd9"


class OrangeCheckmarkCheckBox(_ColoredCheckmarkCheckBox):
    """Чекбокс с оранжевым фоном и белой галочкой в отмеченном состоянии (для AI-инъекции контекста)."""

    _checked_color = "#FF9800"
    _checked_hover_color = "#F57C00"


# CustomRadioButton (Batch #3c): перенесён ВЕРБАТИМ из Supervertaler.py.
# Это НЕ дубль CheckmarkRadioButton, хотя оба рисуют точку в круглом
# индикаторе: монолитный виджет — 18px кольцо #4CAF50 на белом фоне с
# ЗЕЛЁНОЙ центральной точкой (r = min*0.25); CheckmarkRadioButton — 16px
# зелёная ЗАЛИВКА с БЕЛОЙ точкой (r = width*0.25). Слияние запрещено
# решением гейта 1.4 Batch #3c.
class CustomRadioButton(QRadioButton):
    """Переключатель с круглым индикатором: зелёное кольцо и зелёная точка в отмеченном состоянии.
    
    В ранних версиях класса рисовался квадратный индикатор с белой галочкой на
    зелёной заливке — визуально точная копия чекбокса, из-за чего как минимум один
    пользователь (отзыв на форуме, май 2026) решил, что список LLM-провайдеров
    допускает множественный выбор, хотя выбор на самом деле взаимоисключающий.
    Теперь вид соответствует универсальному обозначению переключателя: пустой
    кружок в выключенном состоянии, залитая точка в центре — во включённом."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setEnabled(True)
        # 18 px diameter → border-radius 9 px = a perfect circle.
        self.setStyleSheet("""
            QRadioButton {
                font-size: 9pt;
                spacing: 6px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #999;
                border-radius: 9px;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                border-color: #4CAF50;
                background-color: white;
            }
            QRadioButton::indicator:hover {
                border-color: #666;
            }
            QRadioButton::indicator:checked:hover {
                border-color: #45a049;
            }
        """)

    def paintEvent(self, event):
        """Рисует центральную точку при отметке — визуальный сигнал «именно
                этот радиобаттон активен». Рисуется вручную, потому что движок
                таблиц стилей Qt не даёт удобного способа поместить цветную
                точку внутрь стилизованного ::indicator, не потеряв кольцо
                и поведение при наведении, только что заданные."""
        super().paintEvent(event)
        if not self.isChecked():
            return

        from PyQt6.QtWidgets import QStyleOptionButton
        from PyQt6.QtGui import QPainter, QColor
        from PyQt6.QtCore import QRectF

        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        indicator_rect = self.style().subElementRect(
            self.style().SubElement.SE_RadioButtonIndicator, opt, self
        )
        if not indicator_rect.isValid():
            return

        # Centre dot: ~50% of the indicator diameter, green to match the ring.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4CAF50"))
        cx = indicator_rect.x() + indicator_rect.width() / 2
        cy = indicator_rect.y() + indicator_rect.height() / 2
        r = min(indicator_rect.width(), indicator_rect.height()) * 0.25
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        painter.end()
