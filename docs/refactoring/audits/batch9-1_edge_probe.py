# -*- coding: utf-8 -*-
"""Batch #9.1 Э1.2: крайние случаи профилей Custom на baseline (рекон, ничего не чинит).

Сценарии (каждый — СВЕЖИЙ iso-профиль, сидируется снаружи):
  edge_dup     — (а) дублирующееся имя отклоняется; (б) пустое имя и отмена — no-op
  edge_delonly — (в) удаление единственного профиля + Save; (д) повторный Save при нуле профилей
  edge_uni     — (ж) имя с пробелами (обрезка) и юникодом; (е) профиль без api_key сохраняется
Запуск: python batch9-1_edge_probe.py <tree-root> <iso-dir> <scenario>
"""
import faulthandler, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
scenario = sys.argv[3]

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
cfg_dir = iso / "AppData" / "Roaming" / "Supervertaler"
cfg_dir.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
(cfg_dir / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8")

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import (QApplication, QDialog, QComboBox, QLineEdit,  # noqa: E402
                             QPushButton, QInputDialog, QMessageBox)

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

_queue = []
QInputDialog.getText = staticmethod(lambda *a, **k: (_queue.pop(0) if _queue else ("", False)))

settings_file = data_dir / "workbench" / "settings" / "settings.json"


def read_llm():
    return json.loads(settings_file.read_text(encoding="utf-8")).get("ui", {}).get("llm_settings", {})


CE = {"name": "Custom Endpoint", "endpoint": "http://127.0.0.1:8888/v1",
      "model": "Qwen3.8-27B-GGUF:UD-IQ2_XXS", "api_key": "sk-seed-TEST"}


def find_widgets(tab):
    names = ["Custom Endpoint", "Profile A", "Profile B", "Local", "Профиль Тест 1"]
    combo = next((c for c in tab.findChildren(QComboBox)
                  if c.count() >= 1 and c.itemText(0) in names), None)
    add_btn = next((b for b in tab.findChildren(QPushButton) if b.text() == "+"), None)
    rm_btn = next((b for b in tab.findChildren(QPushButton) if b.text() == "−"), None)
    save_btn = next((b for b in tab.findChildren(QPushButton) if "Save AI Settings" in b.text()), None)
    return combo, add_btn, rm_btn, save_btn


win = Supervertaler.SupervertalerQt()
print(f"[{scenario}] window built", flush=True)

if scenario == "edge_dup":
    tab = win._create_ai_settings_tab()
    combo, add_btn, rm_btn, save_btn = find_widgets(tab)
    _queue[:] = [("Local", True), ("Local", True), ("   ", True), ("X", False)]
    add_btn.click()                                   # (а-1) создаёт "Local"
    n_after_first = combo.count()
    add_btn.click()                                   # (а-2) дубль -> warning, отклонён
    print(f"[edge_dup] after first add: {n_after_first} items; after duplicate add: {combo.count()} "
          f"items {[combo.itemText(i) for i in range(combo.count())]}")
    add_btn.click()                                   # (б-1) пустое имя (пробелы) -> no-op
    add_btn.click()                                   # (б-2) отмена -> no-op
    print(f"[edge_dup] after empty-name and cancel: {combo.count()} items")
    save_btn.click()
    ls = read_llm()
    print(f"[edge_dup] VERDICT: dup rejected={combo.count() == 2 and n_after_first == 2}; "
          f"file profiles={[p['name'] for p in ls.get('custom_openai_profiles', [])]}")

elif scenario == "edge_delonly":
    tab = win._create_ai_settings_tab()
    combo, add_btn, rm_btn, save_btn = find_widgets(tab)
    rm_btn.click()                                    # (в) удалить единственный
    print(f"[edge_delonly] after remove: combo count={combo.count()}")
    save_btn.click()
    ls = read_llm()
    print(f"[edge_delonly] after save#1: profiles={[p['name'] for p in ls.get('custom_openai_profiles', [])]} "
          f"active={ls.get('custom_openai_active_profile')!r} "
          f"flat={ls.get('custom_openai_endpoint')!r}/{ls.get('custom_openai_model')!r}")
    save_btn.click()                                  # (д) повторный Save при нуле профилей (в UI)
    ls = read_llm()
    print(f"[edge_delonly] after save#2 (zero in UI): profiles={[p['name'] for p in ls.get('custom_openai_profiles', [])]} "
          f"active={ls.get('custom_openai_active_profile')!r} "
          f"flat={ls.get('custom_openai_endpoint')!r}/{ls.get('custom_openai_model')!r}")

elif scenario == "edge_uni":
    tab = win._create_ai_settings_tab()
    combo, add_btn, rm_btn, save_btn = find_widgets(tab)
    _queue[:] = [("  Профиль Тест 1  ", True)]
    add_btn.click()                                   # (ж) пробелы обрежутся, юникод сохранится
    print(f"[edge_uni] combo: {[combo.itemText(i) for i in range(combo.count())]} "
          f"current={combo.currentText()!r}")
    save_btn.click()
    ls = read_llm()
    profs = ls.get("custom_openai_profiles", [])
    newp = next((p for p in profs if p["name"] == "Профиль Тест 1"), None)
    print(f"[edge_uni] VERDICT: unicode+trim profile saved={newp is not None}; "
          f"api_key field empty={bool(newp) and newp.get('api_key') == ''}; "
          f"active={ls.get('custom_openai_active_profile')!r}")

print(f"[{scenario}] RESULT OK", flush=True)
os._exit(0)
