# -*- coding: utf-8 -*-
"""Batch #9.1 проба c: схема endpoint (9.1b).

c1: сид профиля с endpoint без схемы -> UI-ввод «127.0.0.1:3445/v1» -> Save:
    в файле и в поле «http://127.0.0.1:3445/v1».
c2: файл со старой schemeless-записью: _get_active_custom_profile возвращает
    НОРМАЛИЗОВАННУЮ КОПИЮ, файл на диске не меняется.
c3: LLMClient с нормализованным base_url конструируется, base_url == схема+адрес
    (пакет openai в рантайме отсутствует — НЕ ставить, только конструирование).
Запуск: python batch9-1_probe_c.py <tree-root> <iso-dir> <phase: c1|c2|c3>
"""
import faulthandler, hashlib, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
phase = sys.argv[3]

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
                             QPushButton, QMessageBox)

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

settings_file = data_dir / "workbench" / "settings" / "settings.json"
CE_RAW = {"name": "Custom Endpoint", "endpoint": "127.0.0.1:3445/v1",
          "model": "Qwen3.8-27B-GGUF:UD-IQ2_XXS", "api_key": "sk-seed-TEST"}


def read_llm():
    return json.loads(settings_file.read_text(encoding="utf-8")).get("ui", {}).get("llm_settings", {})


def file_hash():
    return hashlib.sha256(settings_file.read_bytes()).hexdigest() if settings_file.exists() else "<absent>"


win = Supervertaler.SupervertalerQt()
print(f"[{phase}] window built", flush=True)

if phase == "c1":
    tab = win._create_ai_settings_tab()
    combo = next(c for c in tab.findChildren(QComboBox)
                 if c.count() >= 1 and c.itemText(0) == "Custom Endpoint")
    ep = next(e for e in tab.findChildren(QLineEdit)
              if e.placeholderText() == "https://api.example.com/v1")
    print(f"[c1] field after populate: {ep.text()!r}")
    ep.setText("127.0.0.1:3445/v1")
    ep.editingFinished.emit()
    save_btn = next(b for b in tab.findChildren(QPushButton) if "Save AI Settings" in b.text())
    save_btn.click()
    ls = read_llm()
    prof = ls["custom_openai_profiles"][0]
    print(f"[c1] file endpoint: {prof['endpoint']!r}")
    print(f"[c1] field after save: {ep.text()!r}")
    print(f"[c1] VERDICT: normalized in file and field="
          f"{prof['endpoint'] == 'http://127.0.0.1:3445/v1' and ep.text() == 'http://127.0.0.1:3445/v1'}")

elif phase == "c2":
    h_before = file_hash()
    ls = win.load_llm_settings()
    prof = win._get_active_custom_profile(ls)
    h_after = file_hash()
    print(f"[c2] reader endpoint: {prof.get('endpoint')!r} (file active name {ls.get('custom_openai_active_profile')!r})")
    print(f"[c2] file hash unchanged: {h_before == h_after}")
    print(f"[c2] VERDICT: normalized copy, disk untouched="
          f"{prof.get('endpoint') == 'http://127.0.0.1:3445/v1' and h_before == h_after}")

elif phase == "c3":
    from modules.llm_clients import LLMClient
    cl = LLMClient(api_key="not-needed", provider="custom_openai", model="m",
                   base_url="http://127.0.0.1:3445/v1")
    print(f"[c3] LLMClient constructed, base_url={cl.base_url!r}")
    try:
        from openai import OpenAI  # noqa: F401
        print("[c3] openai SDK present")
    except ImportError as e:
        print(f"[c3] openai SDK absent in dev runtime (as documented in R9 §2.8): {e}")
    print(f"[c3] VERDICT: base_url normalized passed through={cl.base_url == 'http://127.0.0.1:3445/v1'}")

print(f"[{phase}] RESULT OK", flush=True)
os._exit(0)
