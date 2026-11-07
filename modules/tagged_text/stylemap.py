"""stylemap — JSON-карта «роль → имя стиля» (Batch I1).

По образцу segmentation_rules: простая структура с версией, путь —
параметром (в data root попадёт в I2). Имена по умолчанию = имена ролей;
символьные стили: bold→Bold, italic→Italic, bold_italic→BoldItalic.

Формат::

    {
      "version": 1,
      "paragraph_styles": {"h1": "h1", …},
      "char_styles": {"bold": "Bold", "italic": "Italic",
                      "bold_italic": "BoldItalic"}
    }
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

MAP_VERSION = 1

PARA_ROLES = ('h1', 'h2', 'h3', 'p', 'li', 'li_n', 'img', 'table_row')
CHAR_KEYS = ('bold', 'italic', 'bold_italic')

DEFAULT_CHAR_STYLES = {
    'bold': 'Bold',
    'italic': 'Italic',
    'bold_italic': 'BoldItalic',
}


def default_paragraph_styles():
    """Имена стилей по умолчанию = имена ролей."""
    return {role: role for role in PARA_ROLES}


@dataclass
class StyleMap:
    """Карта «роль → имя стиля» для шапки Define*Style и тегов ParaStyle."""

    paragraph_styles: dict = field(default_factory=default_paragraph_styles)
    char_styles: dict = field(default_factory=lambda: dict(DEFAULT_CHAR_STYLES))
    version: int = MAP_VERSION

    def para_name(self, role):
        """Имя абзацного стиля для роли (неизвестная роль → сама роль)."""
        return self.paragraph_styles.get(role, role)

    def char_name(self, key):
        """Имя символьного стиля (bold/italic/bold_italic)."""
        return self.char_styles.get(key, DEFAULT_CHAR_STYLES.get(key, key))

    def to_dict(self):
        return {
            'version': self.version,
            'paragraph_styles': dict(self.paragraph_styles),
            'char_styles': dict(self.char_styles),
        }


def load(path):
    """Загрузить карту из JSON; отсутствующие ключи — значения по умолчанию.

    Некорректный JSON или не-словарь → ValueError. Неизвестные роли в JSON
    сохраняются как есть (используются, только если роль встретится).
    Версия ≠ 1 — предупреждение возвращается в warnings, карта принимается.
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError('stylemap: JSON должен быть объектом (словарём)')
    warnings = []
    version = data.get('version', MAP_VERSION)
    if version != MAP_VERSION:
        warnings.append('stylemap: версия %r ≠ %d, читаю как есть'
                        % (version, MAP_VERSION))
    sm = StyleMap(version=version)
    para = data.get('paragraph_styles', {})
    if not isinstance(para, dict):
        raise ValueError('stylemap: paragraph_styles должен быть словарём')
    sm.paragraph_styles.update({str(k): str(v) for k, v in para.items()})
    chars = data.get('char_styles', {})
    if not isinstance(chars, dict):
        raise ValueError('stylemap: char_styles должен быть словарём')
    sm.char_styles.update({str(k): str(v) for k, v in chars.items()})
    return sm, warnings


def save(path, style_map):
    """Сохранить карту в JSON (utf-8, ensure_ascii=False, отступ 2)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(style_map.to_dict(), f, ensure_ascii=False, indent=2)
        f.write('\n')
