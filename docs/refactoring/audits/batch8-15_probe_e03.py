# -*- coding: utf-8 -*-
"""Спец-проба E-03 (решение Дмитрия 2026-10-11, условия 2 и 3).

Для провайдеров openai / claude / custom_openai / gemini:
  - vision-флаг подменён на True, LLM-вызов подменён заглушкой, сеть не нужна;
  - сегмент с 'Figure 1A', папка фигур с 'Figure 1A.png' (настоящий PIL PNG);
  - в аргументах заглушки должно быть видно прикреплённое изображение:
    openai/claude/custom_openai -> [(ref, raw_base64_png_str)],
    gemini -> [(ref, PIL.Image)].
Без «Figure» (режим nofigure): images=None, а текстовые аргументы запроса
(text/source_lang/target_lang) — для сравнения до/после построчно.

Запуск: python batch8-15_probe_e03.py <tree-root> <iso-dir> <tag> <provider> [nofigure]
Exit 0 = всё ок; JSON-строка CAPTURE передаёт формат images.
"""
import base64, faulthandler, io, json, os, pathlib, sys, time

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]
provider = sys.argv[4]
mode = sys.argv[5] if len(sys.argv) > 5 else "figure"

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
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8"
)

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected

win = Supervertaler.SupervertalerQt()
print(f"[{tag}] window built", flush=True)

# --- сегмент (с Figure 1A или без) ---
from modules.models import Project, Segment  # noqa: E402

src_text = ("The assembly is shown in Figure 1A. Tighten the screws evenly."
            if mode != "nofigure" else
            "Tighten the screws evenly. See the assembly instructions.")
proj = Project(name="probe-e03", source_lang="en", target_lang="nl",
               segments=[Segment(id=1, source=src_text)])
win.current_project = proj
win.table.setRowCount(1)
win.table.selectRow(0)

# --- папка фигур: карта инъекцией. В embed-питоне нет tkinter -> ImageTk ->
# PIL_AVAILABLE=False -> load_from_folder недоступен в СРЕДЕ пробы (в сборке
# Дмитрия Pillow полный). has_images()/get_images_for_text читают
# figure_context_map напрямую — наполняем его тем же объектом PIL.Image.
if mode != "nofigure":
    from PIL import Image  # noqa: E402
    fig_dir = iso / "figures"
    fig_dir.mkdir(exist_ok=True)
    img = Image.new("RGB", (4, 4), (200, 10, 10))
    img.save(fig_dir / "Figure 1A.png")
    win.figure_context.figure_context_folder = str(fig_dir)
    win.figure_context.figure_context_map["1a"] = Image.open(fig_dir / "Figure 1A.png")
    print(f"[{tag}] figures injected into map: "
          f"{win.figure_context.get_image_count()}", flush=True)

# --- подмены ---
win.load_llm_settings = lambda: {"provider": provider, "model": "stub-model"}
win._resolve_provider_model = lambda settings, provider_, default="": "stub-model"
win.load_api_keys = lambda: {"openai": "sk-stub", "claude": "sk-stub",
                             "google": "goog-stub", "mymemory": "xxx"}

captured = {}

class _StubClient:
    def translate(self, text=None, source_lang=None, target_lang=None,
                  custom_prompt=None, images=None, **kw):
        captured["text"] = text
        captured["source_lang"] = source_lang
        captured["target_lang"] = target_lang
        captured["custom_prompt_sha"] = __import__("hashlib").sha256(
            (custom_prompt or "").encode()).hexdigest()[:16]
        captured["custom_prompt_len"] = len(custom_prompt or "")
        if images is None:
            captured["images"] = None
        else:
            ims = []
            for ref, payload in images:
                if hasattr(payload, "save"):  # PIL.Image
                    ims.append({"ref": ref, "kind": "PIL.Image",
                                "size": list(payload.size)})
                else:
                    raw = base64.b64decode(payload)
                    ims.append({"ref": ref, "kind": "base64-png" if raw[:4] == b"\x89PNG" else f"base64-other:{raw[:4]!r}",
                                "len": len(payload)})
            captured["images"] = ims
        return "STUB TRANSLATION"

win.create_llm_client = lambda provider_, model_, api_keys_, settings=None: _StubClient()

import modules.llm_clients as _llm  # noqa: E402
_orig_vision = _llm.LLMClient.model_supports_vision
if os.environ.get("E03_VISION", "1") != "0":
    _llm.LLMClient.model_supports_vision = classmethod(lambda cls, p, m: True)

try:
    win.translate_current_segment()
    app.processEvents()
    print(f"[{tag}] CAPTURE {json.dumps(captured, ensure_ascii=False)}", flush=True)
    ok = (
        captured.get("images") is not None and len(captured["images"]) == 1
        and captured["images"][0]["ref"] == "1a"
        and (
            (provider == "gemini" and captured["images"][0]["kind"] == "PIL.Image")
            or (provider in ("openai", "claude", "custom_openai")
                and captured["images"][0]["kind"] == "base64-png")
        )
    ) if (mode == "figure" and os.environ.get("E03_VISION", "1") != "0") else (
        (captured.get("images") is None
         and captured.get("text", "").startswith("Tighten"))
        if mode == "nofigure" else
        (captured.get("images") is None
         and captured.get("text", "").startswith("The assembly"))
    )
    print(f"[{tag}] RESULT {'OK' if ok else 'FAIL'}", flush=True)
finally:
    _llm.LLMClient.model_supports_vision = _orig_vision
    # ВАЖНО: не вызывать win.close() — в этой пробе проект помечен изменённым,
    # и closeEvent (@~49335) подвисает (наблюдение 8.15); os._exit минует очистку.
    os._exit(0)
