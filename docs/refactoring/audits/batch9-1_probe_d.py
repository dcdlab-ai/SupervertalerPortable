# -*- coding: utf-8 -*-
"""Batch #9.1 проба d: файл с dangling-активным именем (как у Дмитрия).

Сид: profiles=[Custom Endpoint], custom_openai_active_profile='Local' (имени нет в списке).
Ожидания ПОСЛЕ 9.1a:
  - вкладка открывается, комбо показывает 'Custom Endpoint' (снапшот из списка);
  - движок (_get_active_custom_profile) использует 'Custom Endpoint' (fallback profiles[0]);
  - Save из UI: активное имя исправлено на 'Custom Endpoint' (самолечение),
    плоские зеркала = поля 'Custom Endpoint', список не изменился.
Запуск: python batch9-1_probe_d.py <tree-root> <iso-dir>
"""
import faulthandler, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()

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


def read_llm():
    return json.loads(settings_file.read_text(encoding="utf-8")).get("ui", {}).get("llm_settings", {})


win = Supervertaler.SupervertalerQt()
print("[d] window built", flush=True)

tab = win._create_ai_settings_tab()
combo = next(c for c in tab.findChildren(QComboBox)
             if c.count() >= 1 and c.itemText(0) == "Custom Endpoint")
print(f"[d] fresh tab combo: {[combo.itemText(i) for i in range(combo.count())]} "
      f"shown={combo.currentText()!r}")
ls0 = win.load_llm_settings()
prof = win._get_active_custom_profile(ls0)
print(f"[d] engine before save: name={prof.get('name')!r} endpoint={prof.get('endpoint')!r} "
      f"(file active={ls0.get('custom_openai_active_profile')!r})")

save_btn = next(b for b in tab.findChildren(QPushButton) if "Save AI Settings" in b.text())
save_btn.click()
ls = read_llm()
names = [p["name"] for p in ls.get("custom_openai_profiles", [])]
act = ls.get("custom_openai_active_profile")
flat = (ls.get("custom_openai_endpoint"), ls.get("custom_openai_model"))
print(f"[d] after save: profiles={names} active={act!r} flat={flat}")

tab2 = win._create_ai_settings_tab()
combo2 = next(c for c in tab2.findChildren(QComboBox)
              if c.count() >= 1 and c.itemText(0) == "Custom Endpoint")
print(f"[d] fresh tab after save: shown={combo2.currentText()!r}")
ok = (names == ["Custom Endpoint"] and act == "Custom Endpoint"
      and flat == ("http://127.0.0.1:8888/v1", "Qwen3.8-27B-GGUF:UD-IQ2_XXS"))
print(f"[d] VERDICT: dangling name healed, list intact, mirrors from active profile -> {ok}")

print("[d] RESULT OK", flush=True)
os._exit(0)
