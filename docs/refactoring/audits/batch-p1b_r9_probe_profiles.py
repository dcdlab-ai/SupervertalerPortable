# -*- coding: utf-8 -*-
"""R9 Ч1: воспроизведение бага профилей Custom (OpenAI-Compatible).

Сценарии (каждый — СВЕЖИЙ iso-профиль, сидируется снаружи):
  a     — добавить профиль "Local" в UI, заполнить поля, Save ->
          ожидание: файл теряет "Local", active_profile="Local" (баг Дмитрия)
          затем (та же процесс): D-фаза — как выглядит сломанный файл в UI/движке
          затем C-фаза — гипотеза 5: base_url без схемы (без сети, только конструирование)
  ctrl  — контроль: 2 профиля на диске, переключение + правка поля, Save ->
          ожидание: оба профиля целы, active обновлён (переключение работает)
  rm    — удалить первый из двух профилей, Save ->
          ожидание: воскрешение удалённого и/или подмена полей (порча)

Запуск: python r9_probe_profiles.py <tree-root> <iso-dir> <scenario>
"""
import faulthandler, json, os, pathlib, sys, traceback

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
os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  # P1-B seam: data root -> <iso>/Supervertaler
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"

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
QInputDialog.getText = staticmethod(lambda *a, **k: ("Local", True))

settings_file = data_dir / "workbench" / "settings" / "settings.json"


def read_llm():
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    return data.get("ui", {}).get("llm_settings", {})


def dump(tag, ls):
    print(f"[{tag}] profiles={json.dumps(ls.get('custom_openai_profiles'), ensure_ascii=False)}")
    print(f"[{tag}] active={ls.get('custom_openai_active_profile')!r} "
          f"flat_endpoint={ls.get('custom_openai_endpoint')!r} flat_model={ls.get('custom_openai_model')!r} "
          f"provider={ls.get('provider')!r}")


PROFILE_NAMES = ["Custom Endpoint", "Profile A", "Profile B", "Local"]


def find_widgets(tab):
    combo = None
    for c in tab.findChildren(QComboBox):
        if c.count() >= 1 and c.itemText(0) in PROFILE_NAMES:
            combo = c
            break
    add_btn = next((b for b in tab.findChildren(QPushButton) if b.text() == "+"), None)
    rm_btn = next((b for b in tab.findChildren(QPushButton) if b.text() == "−"), None)
    save_btn = next((b for b in tab.findChildren(QPushButton)
                     if "Save AI Settings" in b.text()), None)
    ep = next((e for e in tab.findChildren(QLineEdit)
               if e.placeholderText() == "https://api.example.com/v1"), None)
    md = next((e for e in tab.findChildren(QLineEdit)
               if e.placeholderText().startswith("e.g. qwen-plus")), None)
    key = next((e for e in tab.findChildren(QLineEdit)
                if e.placeholderText().startswith("API key for this endpoint")), None)
    return combo, add_btn, rm_btn, save_btn, ep, md, key


win = Supervertaler.SupervertalerQt()
print(f"[{scenario}] window built", flush=True)

if scenario == "a":
    # ---------- фаза A: add "Local" -> Save ----------
    tab = win._create_ai_settings_tab()
    combo, add_btn, rm_btn, save_btn, ep, md, key = find_widgets(tab)
    assert combo is not None and add_btn is not None and save_btn is not None, "widgets not found"
    print(f"[a] combo items before: {[combo.itemText(i) for i in range(combo.count())]}")
    add_btn.click()                      # QInputDialog patched -> "Local"
    print(f"[a] combo items after add: {[combo.itemText(i) for i in range(combo.count())]} "
          f"current={combo.currentText()!r}")
    ep.setText("http://127.0.0.1:9999/v1"); ep.editingFinished.emit()
    md.setText("test-model"); md.editingFinished.emit()
    save_btn.click()
    ls = read_llm()
    dump("a-after-save", ls)
    lost = not any(p.get("name") == "Local" for p in ls.get("custom_openai_profiles", []))
    act = ls.get("custom_openai_active_profile")
    print(f"[a] VERDICT: profile 'Local' lost from file={lost}, active_profile={act!r} "
          f"-> bug reproduced={lost and act == 'Local'}")

    # ---------- фаза D: тот же сломанный файл, свежая вкладка ----------
    tab2 = win._create_ai_settings_tab()
    combo2, _, _, _, ep2, md2, _ = find_widgets(tab2)
    print(f"[d] fresh tab combo items: {[combo2.itemText(i) for i in range(combo2.count())]} "
          f"shown={combo2.currentText()!r}")
    ls2 = win.load_llm_settings()
    prof = win._get_active_custom_profile(ls2)
    model = win._resolve_provider_model(ls2, "custom_openai")
    print(f"[d] engine resolves: name={prof.get('name')!r} endpoint={prof.get('endpoint')!r} "
          f"model={model!r} (file active={ls2.get('custom_openai_active_profile')!r})")
    win._update_llm_indicator()
    lbl = getattr(win, "llm_indicator_label", None)
    print(f"[d] status bar indicator: {lbl.text()!r}" if lbl is not None else "[d] no indicator label")

    # ---------- фаза C: base_url без схемы (конструирование, БЕЗ сети) ----------
    print("[c] hypothesis 5: schemeless endpoint handling")
    from modules.llm_clients import LLMClient
    try:
        cl = LLMClient(api_key="not-needed", provider="custom_openai",
                       model="m", base_url="127.0.0.1:3445/v1")
        print(f"[c] LLMClient constructed, base_url={cl.base_url!r}")
        from openai import OpenAI
        try:
            sdk = OpenAI(api_key="x", base_url="127.0.0.1:3445/v1")
            print(f"[c] openai.OpenAI constructed, base_url={sdk.base_url} "
                  f"(type={type(sdk.base_url).__name__})")
        except Exception as e:
            print(f"[c] openai.OpenAI raised at construction: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"[c] LLMClient raised: {type(e).__name__}: {e}")

elif scenario == "ctrl":
    tab = win._create_ai_settings_tab()
    combo, add_btn, rm_btn, save_btn, ep, md, key = find_widgets(tab)
    print(f"[ctrl] combo before: {[combo.itemText(i) for i in range(combo.count())]} "
          f"current={combo.currentText()!r} ep={ep.text()!r}")
    combo.setCurrentIndex(1)             # выбрать второй профиль
    print(f"[ctrl] after switch: current={combo.currentText()!r} ep={ep.text()!r} md={md.text()!r}")
    ep.setText("http://127.0.0.1:7777/v1"); ep.editingFinished.emit()
    save_btn.click()
    ls = read_llm()
    dump("ctrl-after-save", ls)
    names = [p.get("name") for p in ls.get("custom_openai_profiles", [])]
    print(f"[ctrl] VERDICT: both profiles intact={names == ['Profile A', 'Profile B']}, "
          f"active={ls.get('custom_openai_active_profile')!r}")

elif scenario == "rm":
    tab = win._create_ai_settings_tab()
    combo, add_btn, rm_btn, save_btn, ep, md, key = find_widgets(tab)
    print(f"[rm] combo before: {[combo.itemText(i) for i in range(combo.count())]} "
          f"current={combo.currentText()!r} ep={ep.text()!r} md={md.text()!r}")
    rm_btn.click()                       # QMessageBox.question patched -> Yes
    print(f"[rm] combo after remove: {[combo.itemText(i) for i in range(combo.count())]} "
          f"current={combo.currentText()!r} ep={ep.text()!r} md={md.text()!r}")
    save_btn.click()
    ls = read_llm()
    dump("rm-after-save", ls)
    names = [p.get("name") for p in ls.get("custom_openai_profiles", [])]
    print(f"[rm] VERDICT: removed 'Profile A' present again={'Profile A' in names} "
          f"(resurrection), active={ls.get('custom_openai_active_profile')!r}")

print(f"[{scenario}] RESULT OK", flush=True)
os._exit(0)
