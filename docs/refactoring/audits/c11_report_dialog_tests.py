# -*- coding: utf-8 -*-
"""Headless-тесты Batch C1.1: окно отчёта экспорта Tagged Text.

Проверки (по промпту): окно изменяемого размера с разумным дефолтом (минимум
720x420); предупреждения в прокручиваемом поле с переносом длинных строк (без
горизонтальной прокрутки); предупреждения об эхе промта — отдельным блоком
НАВЕРХУ под своим заголовком, красным и жирным; остальные предупреждения ниже
обычным шрифтом; число предупреждений — в заголовке окна/первой строке.
Логика экспорта и writer не затрагивается: «Копировать» кладёт прежний
report.to_text().

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/c11_report_dialog_tests.py
"""
import faulthandler
import os
import pathlib
import sys

faulthandler.dump_traceback_later(90, repeat=True, file=sys.stderr)

REPO = r'E:\Dev\SupervertalerPortable'
STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-c1\tests\run-c11')
ISO = STAGE / 'iso'
OUT = STAGE / 'out'
OUT.mkdir(parents=True, exist_ok=True)

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['USERPROFILE'] = str(ISO)
os.environ['APPDATA'] = str(ISO / 'AppData' / 'Roaming')
os.environ['LOCALAPPDATA'] = str(ISO / 'AppData' / 'Local')
os.environ['HOME'] = str(ISO)
os.environ['TEMP'] = str(ISO / 'tmp')
os.environ['TMP'] = str(ISO / 'tmp')
os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)
for d in ('Desktop', 'Documents', 'Downloads'):
    (ISO / d).mkdir(parents=True, exist_ok=True)

sys.path.insert(0, REPO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from PyQt6.QtWidgets import (QApplication, QDialog,  # noqa: E402
                             QTextEdit, QWidget)

PASSED = 0
FAILED = 0


def check(name, cond, detail=''):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f'PASS {name}', flush=True)
    else:
        FAILED += 1
        print(f'FAIL {name} {detail}', flush=True)


app = QApplication(sys.argv)

# Захват диалога: exec подменяется, экземпляр сохраняется для инспекции.
_captured = []


def _capture_exec(self, *a, **k):
    _captured.append(self)
    return QDialog.DialogCode.Accepted


QDialog.exec = _capture_exec

import Supervertaler as SV  # noqa: E402
from modules.tagged_text.writer import ExportReport  # noqa: E402

ECHO_W1 = ('похоже на эхо промта (строка 2): (Сегмент, отмеченный >>> <<<, '
           'подлежит переводу) ' + 'очень длинное предупреждение ' * 12)
ECHO_W2 = ('похоже на эхо промта (строка 8): >>> 30. ### ЦЕЛИ И ПОБЕДА  <<<  '
           '[ПЕРЕВЕСТИ ЭТО]')
IMG_W1 = 'файл не найден (строка 5): images/missing_map.png'
IMG_W2 = 'относительный путь вне images/ — записан как есть (строка 9): data/x.png'


class _Host(QWidget):
    """Лёгкий хост вместо полного SupervertalerQt: методу нужны только
    QDialog(self) (родитель-виджет) и self.tr()."""


_HOST = _Host()  # живой родитель: иначе GC удаляет QDialog вместе с ним


def _show(report, name='file.tagged.txt'):
    _captured.clear()
    SV.SupervertalerQt._show_tagged_text_report(
        _HOST, report, str(OUT / name))
    return _captured[-1]


def _view(dialog):
    views = [w for w in dialog.findChildren(QTextEdit)
             if w.isReadOnly()]
    return views[0] if views else None


# ── 1. Только эхо ────────────────────────────────────────────────────────
rep = ExportReport(color_table_mode='minimal')
rep.warnings.extend([ECHO_W1, ECHO_W2])
dlg = _show(rep)
view = _view(dlg)
check('C1.1-1 окно изменило размер и минимум >= 720x420',
      dlg.minimumSize().width() >= 720 and dlg.minimumSize().height() >= 420
      and dlg.width() >= 720 and dlg.height() >= 420,
      (dlg.minimumSize().width(), dlg.minimumSize().height(),
       dlg.width(), dlg.height()))
check('C1.1-2 число предупреждений в заголовке окна',
      '2 warning(s)' in dlg.windowTitle(), dlg.windowTitle())
from PyQt6.QtWidgets import QLabel  # noqa: E402
_labels = ' | '.join(lb.text() for lb in dlg.findChildren(QLabel))
check('C1.1-3 число предупреждений в первой строке (над полем)',
      '2 warning(s)' in _labels, _labels[:160])
check('C1.1-4 просмотр QTextEdit (не QPlainTextEdit), перенос строк включён',
      view is not None
      and view.lineWrapMode() == QTextEdit.LineWrapMode.WidgetWidth)
check('C1.1-5 горизонтальной прокрутки нет',
      view.horizontalScrollBar().maximum() == 0,
      view.horizontalScrollBar().maximum())
plain = view.toPlainText()
_echo_pos = plain.find('похоже на эхо промта (строка 2)')
_stats_pos = plain.find('Отчёт экспорта InDesign Tagged Text')
check('C1.1-6 блок эха НАВЕРХУ: раньше сводки (сценарий «только эхо» — '
      'секции «Предупреждения:» в поле нет, она в Copy-тексте)',
      0 <= _echo_pos < _stats_pos,
      (_echo_pos, _stats_pos))
html = view.toHtml().lower()
check('C1.1-7 эхо красным и жирным',
      'c00000' in html and ('font-weight:600' in html or 'bold' in html))
check('C1.1-8 длинное предупреждение присутствует целиком (перенос, не обрезка)',
      ECHO_W1.split(': ', 1)[1][:40] in plain)
dlg.close()

# ── 2. Эхо + картинки ────────────────────────────────────────────────────
rep2 = ExportReport(color_table_mode='minimal')
rep2.warnings.extend([IMG_W1, ECHO_W2, IMG_W2])
dlg2 = _show(rep2)
view2 = _view(dlg2)
plain2 = view2.toPlainText()
echo_pos = plain2.find('похоже на эхо промта')
check('C1.1-10 порядок блоков: эхо -> сводка -> остальные предупреждения',
      0 <= echo_pos < plain2.find('Отчёт экспорта InDesign Tagged Text')
      < plain2.find(IMG_W1)
      and plain2.find(IMG_W1) < plain2.find(IMG_W2),
      (echo_pos, plain2.find('Отчёт экспорта InDesign Tagged Text'),
       plain2.find(IMG_W1), plain2.find(IMG_W2)))
check('C1.1-11 заголовок блока эха с числом (1)',
      'Prompt echo in the translation — 1' in plain2)
# Copy-кнопка: программный клик.
from PyQt6.QtWidgets import QPushButton  # noqa: E402
copy_btns = [b for b in dlg2.findChildren(QPushButton) if b.text() == 'Copy']
if copy_btns:
    copy_btns[0].click()
    clip = app.clipboard().text()
    check('C1.1-12 «Копировать» кладёт полный to_text()',
          clip == rep2.to_text() and 'Предупреждения:' in clip
          and IMG_W1 in clip)
else:
    check('C1.1-12 «Копировать» кладёт полный to_text()', False, 'no Copy button')

# ── 3. Без предупреждений ────────────────────────────────────────────────
rep3 = ExportReport(color_table_mode='minimal')
dlg3 = _show(rep3)
view3 = _view(dlg3)
check('C1.1-14 без предупреждений: заголовок «0 warning(s)», эхо-блока нет',
      '0 warning(s)' in dlg3.windowTitle()
      and 'похоже на эхо промта' not in view3.toPlainText()
      and 'Предупреждения: нет' in view3.toPlainText())
check('C1.1-15 окно отчёта — по-прежнему QDialog (не новое модальное окно)',
      isinstance(dlg3, QDialog))

# ── 4. Красный ТОЛЬКО у эха (эхо+картинки) ───────────────────────────────
red_html = view2.toHtml()
import re as _re
# Фрагменты с красным цветом:
red_chunks = [m.start() for m in _re.finditer(r'#c00000', red_html)]
check('C1.1-16 красный встречается (эхо-блок есть)', len(red_chunks) >= 1)


def _red_fragments(view):
    """Текстовые фрагменты красного цвета из QTextEdit HTML (упрощённо)."""
    html_doc = view.toHtml()
    out = []
    for m in _re.finditer(r'<span style="([^"]*)">(.*?)</span>', html_doc):
        if 'c00000' in m.group(1):
            out.append(_strip_tags(m.group(2)))
    return out


def _strip_tags(s):
    return _re.sub(r'<[^>]+>', '', s)


red_text = ' '.join(_red_fragments(view2))
check('C1.1-17 красным помечено ТОЛЬКО эхо (IMG-строки вне красного)',
      'похоже на эхо промта' in red_text
      and IMG_W1[:30] not in red_text and IMG_W2[:30] not in red_text,
      red_text[:120])

print(f'[c11] done: {PASSED} passed / {FAILED} failed', flush=True)
sys.exit(1 if FAILED else 0)
