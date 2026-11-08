"""
tagged_text_export_dialog — окно экспорта «роль → имя стиля InDesign» (Batch I2).

Вызывается из Project → Export → InDesign Tagged Text (TXT)...: таблица
соответствий ролей md (h1…table_row) и символьных выделений (Bold, Italic,
BoldItalic) именам стилей InDesign, набор соответствий («серия») с загрузкой
и сохранением в ``<data_root>\\mapping\\<серия>.tagmap.json`` (формат
modules.tagged_text.stylemap) и поле папки images (только для проверки
«найдено/не найдено» — копирование картинок отдельным решением).

По образцу modules/segmentation_rules_widget.py: данные задаёт монолит,
ввод/вывод серии — по путю ``maps_dir``, который монолит вычисляет через
seam (modules.portable_paths), поэтому модуль сам ничего не решает о
расположении данных. Последние серия и папка images persist-ит монолит
в settings.json после принятия диалога.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from modules.styled_widgets import CheckmarkRadioButton
from modules.tagged_text.stylemap import PARA_ROLES, StyleMap

MAP_SUFFIX = '.tagmap.json'

_ROLE_ROWS = (
    ('h1', 'Chapter heading (#)'),
    ('h2', 'Section heading (##)'),
    ('h3', 'Subheading (###)'),
    ('p', 'Paragraph'),
    ('li', 'Bulleted list item'),
    ('li_n', 'Numbered list item (the number stays as text)'),
    ('img', 'Image marker (alt text and path)'),
    ('table_row', 'Table row (temporary: tables are written as paragraphs)'),
)

_CHAR_ROWS = (
    ('bold', 'Character style for **bold** spans'),
    ('italic', 'Character style for *italic* spans'),
    ('bold_italic', 'Character style for ***bold italic*** spans'),
)

# Windows-запрещённые символы и разделители путей в имени серии.
_BAD_SERIES_CHARS = set('\\/:*?"<>|')


def list_series(maps_dir):
    """Имена имеющихся серий (файлы ``<имя>.tagmap.json``), по алфавиту."""
    try:
        names = [fn[:-len(MAP_SUFFIX)] for fn in os.listdir(maps_dir)
                 if fn.endswith(MAP_SUFFIX)
                 and os.path.isfile(os.path.join(maps_dir, fn))]
    except OSError:
        return []
    return sorted(names)


def series_path(maps_dir, series):
    """Путь файла соответствий серии в папке карт соответствий."""
    return os.path.join(maps_dir, series + MAP_SUFFIX)


class TaggedTextExportDialog(QDialog):
    """Окно «роль → имя стиля InDesign» для экспорта Tagged Text (Batch I2)."""

    COL_ROLE, COL_STYLE, COL_DESC = range(3)

    def __init__(self, style_map, images_dir='', series_name='',
                 series_names=(), maps_dir='', parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Export InDesign Tagged Text"))
        self.setMinimumWidth(560)
        self._maps_dir = maps_dir
        self._series_names = list(series_names)

        layout = QVBoxLayout(self)

        info = QLabel(self.tr(
            "Markdown roles are written to InDesign as paragraph styles and "
            "**bold** / *italic* / ***mixed*** spans as character styles. "
            "Adjust the style names below; for a style group write "
            "\"Group:Style\"."))
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(info)

        # ── Таблица «роль → имя стиля → пояснение» ───────────────────────
        rows = _ROLE_ROWS + _CHAR_ROWS
        self.table = QTableWidget(len(rows), 3)
        self.table.setHorizontalHeaderLabels([
            self.tr("Role"), self.tr("InDesign style name"), self.tr("Meaning")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_ROLE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_STYLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_DESC, QHeaderView.ResizeMode.Stretch)
        for row, (key, desc) in enumerate(rows):
            role_item = QTableWidgetItem(key)
            role_item.setFlags(role_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, self.COL_ROLE, role_item)
            name = (style_map.para_name(key) if key in PARA_ROLES
                    else style_map.char_name(key))
            self.table.setItem(row, self.COL_STYLE, QTableWidgetItem(name))
            desc_item = QTableWidgetItem(desc)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            desc_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, self.COL_DESC, desc_item)
        layout.addWidget(self.table)

        # ── Серия (набор соответствий) ───────────────────────────────────
        series_group = QGroupBox(self.tr("Mapping set (series)"))
        series_layout = QHBoxLayout(series_group)
        series_layout.addWidget(QLabel(self.tr("Name:")))
        self.series_edit = QLineEdit(series_name)
        self.series_edit.setToolTip(self.tr(
            "Saved sets live in the mapping folder as <name>.tagmap.json."))
        series_layout.addWidget(self.series_edit)
        self.series_combo = QComboBox()
        self.series_combo.setToolTip(self.tr("Load a saved mapping set"))
        self.series_combo.addItem(self.tr("(choose saved set)"))
        for name in self._series_names:
            self.series_combo.addItem(name)
        self.series_combo.currentIndexChanged.connect(self._on_series_picked)
        series_layout.addWidget(self.series_combo)
        load_btn = QPushButton(self.tr("Load"))
        load_btn.clicked.connect(self._load_series)
        series_layout.addWidget(load_btn)
        save_btn = QPushButton(self.tr("Save"))
        save_btn.clicked.connect(self._save_series)
        series_layout.addWidget(save_btn)
        reset_btn = QPushButton(self.tr("Reset"))
        reset_btn.setToolTip(self.tr("Restore the default role-to-style names"))
        reset_btn.clicked.connect(self._reset_defaults)
        series_layout.addWidget(reset_btn)
        layout.addWidget(series_group)

        # Немодальная статусная строка (Batch I2.1, T-I2c): результат Save/Load
        # и ошибки серий — здесь, красным при ошибке; сбрасывается при смене
        # имени серии. self.tr — как у соседей.
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 9pt; padding: 2px;")
        layout.addWidget(self.status_label)
        self.series_edit.textChanged.connect(self._on_series_name_changed)

        # ── Папка images ─────────────────────────────────────────────────
        images_group = QGroupBox(self.tr("Images folder"))
        images_layout = QHBoxLayout(images_group)
        self.images_edit = QLineEdit(images_dir)
        self.images_edit.setToolTip(self.tr(
            "Used only to check whether referenced images exist "
            "(reported as found / not found); images are not copied."))
        images_layout.addWidget(self.images_edit)
        browse_btn = QPushButton(self.tr("Browse..."))
        browse_btn.clicked.connect(self._browse_images)
        images_layout.addWidget(browse_btn)
        layout.addWidget(images_group)

        # ── Непереведённые сегменты (как в Simple Text File) ─────────────
        untranslated_group = QGroupBox(self.tr("Untranslated Segments"))
        untranslated_layout = QVBoxLayout(untranslated_group)
        self.use_source_radio = CheckmarkRadioButton(self.tr(
            "Use source text for untranslated segments"))
        self.use_source_radio.setChecked(True)
        self.use_empty_radio = CheckmarkRadioButton(self.tr(
            "Leave untranslated segments empty"))
        untranslated_layout.addWidget(self.use_source_radio)
        untranslated_layout.addWidget(self.use_empty_radio)
        layout.addWidget(untranslated_group)

        # ── Кнопки ───────────────────────────────────────────────────────
        button_layout = QHBoxLayout()
        ok_btn = QPushButton(self.tr("Export"))
        ok_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; "
            "border: none; outline: none;")
        ok_btn.clicked.connect(self._validate_and_accept)
        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)

    # ── Таблица ↔ StyleMap ───────────────────────────────────────────
    def style_map(self):
        """Собрать StyleMap из таблицы (роли — PARA_ROLES, далее char)."""
        para = {}
        chars = {}
        for row, (key, _desc) in enumerate(_ROLE_ROWS):
            para[key] = self._cell_text(row)
        for row, (key, _desc) in enumerate(_CHAR_ROWS, start=len(_ROLE_ROWS)):
            chars[key] = self._cell_text(row)
        return StyleMap(paragraph_styles=para, char_styles=chars)

    def _cell_text(self, row):
        item = self.table.item(row, self.COL_STYLE)
        return (item.text().strip() if item is not None else '')

    def _set_map(self, style_map):
        for row, (key, _desc) in enumerate(_ROLE_ROWS):
            self.table.setItem(row, self.COL_STYLE,
                               QTableWidgetItem(style_map.para_name(key)))
        for row, (key, _desc) in enumerate(_CHAR_ROWS, start=len(_ROLE_ROWS)):
            self.table.setItem(row, self.COL_STYLE,
                               QTableWidgetItem(style_map.char_name(key)))

    def _reset_defaults(self):
        self._set_map(StyleMap())

    # ── Серия: загрузка / сохранение ─────────────────────────────────
    def series_name(self):
        return self.series_edit.text().strip()

    def images_dir(self):
        return self.images_edit.text().strip()

    def use_source_fallback(self):
        return self.use_source_radio.isChecked()

    def _on_series_picked(self, index):
        if index > 0:  # 0 — строка-приглашение
            self.series_edit.setText(self.series_combo.itemText(index))
            self._load_series()

    def _on_series_name_changed(self, _text):
        """Статусная строка сбрасывается при смене имени серии (I2.1)."""
        self._set_status('')

    def _set_status(self, message, error=False):
        """Показать немодальный статус Save/Load; error — красным (I2.1)."""
        self.status_label.setText(message)
        self._status_is_error = error
        self.status_label.setStyleSheet(
            "color: #C62828; font-size: 9pt; padding: 2px;" if error
            else "color: #2E7D32; font-size: 9pt; padding: 2px;")

    def status_is_error(self):
        """True, если текущий статус — об ошибке (для тестов)."""
        return getattr(self, '_status_is_error', False)

    def _load_series(self):
        """Загрузить серию из <maps_dir>/<имя>.tagmap.json в таблицу.

        Ошибки (нет файла, битый JSON) — в статусную строку, без модалок (I2.1)."""
        series = self.series_name()
        if not series:
            self._set_status(self.tr("Enter a mapping set name."), error=True)
            return
        path = series_path(self._maps_dir, series)
        if not os.path.isfile(path):
            self._set_status(
                self.tr("Mapping set not found: %s") % path, error=True)
            return
        try:
            from modules.tagged_text.stylemap import load as load_stylemap
            style_map, warnings = load_stylemap(path)
        except Exception as e:
            self._set_status(
                self.tr("Could not read the mapping set: %s") % e, error=True)
            return
        self._set_map(style_map)
        self._set_status(self.tr("Loaded: %s") % series)
        for w in warnings:
            if self.parent() is not None and hasattr(self.parent(), 'log'):
                self.parent().log(f"⚠ {w}")

    def _save_series(self):
        """Сохранить таблицу как серию в <maps_dir>/<имя>.tagmap.json.

        Ошибки (пустое/недопустимое имя, сбой записи) — в статусную строку,
        без модалок (I2.1); успех — «Saved: <полный путь>»."""
        series = self.series_name()
        error = self._series_error(series)
        if error:
            self._set_status(error, error=True)
            return
        path = series_path(self._maps_dir, series)
        try:
            from modules.tagged_text.stylemap import save as save_stylemap
            save_stylemap(path, self.style_map())
        except Exception as e:
            self._set_status(
                self.tr("Could not save the mapping set: %s") % e, error=True)
            return
        self._set_status(self.tr("Saved: %s") % path)
        if series not in self._series_names:
            self._series_names.append(series)
            self._series_names.sort()
            self.series_combo.blockSignals(True)
            self.series_combo.clear()
            self.series_combo.addItem(self.tr("(choose saved set)"))
            for name in self._series_names:
                self.series_combo.addItem(name)
            self.series_combo.blockSignals(False)

    @staticmethod
    def _series_error(series):
        """None, если имя серии корректно; иначе текст ошибки."""
        if not series:
            return "Enter a mapping set name first."
        if set(series) & _BAD_SERIES_CHARS:
            return ("The mapping set name must not contain "
                    "\\ / : * ? \" < > | characters.")
        if series.startswith('.'):
            return "The mapping set name must not start with a dot."
        return None

    # ── Папка images ─────────────────────────────────────────────────
    def _browse_images(self):
        current = self.images_dir()
        chosen = QFileDialog.getExistingDirectory(
            self, self.tr("Images folder"), current or '')
        if chosen:
            self.images_edit.setText(chosen)

    # ── Принятие с проверкой имён стилей ─────────────────────────────
    def _validate_and_accept(self):
        bad_rows = [row for row in range(self.table.rowCount())
                    if not self._cell_text(row)]
        if bad_rows:
            self.table.setCurrentCell(bad_rows[0], self.COL_STYLE)
            QMessageBox.warning(self, "Export InDesign Tagged Text",
                                self.tr("Style names must not be empty."))
            return
        self.accept()
