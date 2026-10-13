# Batch 9.4d editor: QuickTrans tab LLM part (llm_providers loop + ollama row +
# api_keys/enabled_providers loads), quicktrans.py chip colors/AI-codes/has_key,
# chat_view_widget model menu -> active-profile info + AI Settings nav.
# Bottom-up per file, py_compile after each edit.
import pathlib, subprocess, sys

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
PY = r"E:\Dev\python-embed\python.exe"

def load(rel, expect):
    F = ROOT / rel
    raw = F.read_bytes().decode("utf-8")
    # Supervertaler.py is CRLF; module files are LF — detect per file.
    nl = "\r\n" if raw.count("\r\n") >= raw.count("\n") / 2 else "\n"
    lines = raw.split(nl)
    assert len(lines) == expect, (rel, len(lines))
    return F, lines, nl

def apply(F, lines, i, a, b, repl, anchor_start, anchor_end, nl="\r\n"):
    s = lines[a-1].strip(); e = lines[b-1].strip()
    assert s.startswith(anchor_start), (i, s[:70])
    assert e.startswith(anchor_end), (i, e[:70])
    lines[a-1:b] = repl
    out = nl.join(lines).encode("utf-8")
    F.write_bytes(out)
    r = subprocess.run([PY, "-m", "py_compile", str(F)], capture_output=True, text=True)
    crlf = out.count(b"\r\n"); lf = out.count(b"\n"); dcr = out.count(b"\r\r\n")
    print(f"edit {i} ({a}-{b} -> {len(repl)}): rc={r.returncode} lines={len(lines)} CRLF={crlf} LF={lf} dCR={dcr}")
    if r.returncode != 0:
        print(r.stderr); sys.exit(1)
    if lf != crlf or dcr != 0:
        print("EOL ANOMALY"); sys.exit(1)

# ---------- Supervertaler.py ----------
F, L = load("Supervertaler.py", 55077)
apply(F, L, 1, 20201, 20218, [], "# Ollama (local LLM", "llm_layout.addLayout(ollama_row)")
apply(F, L, 2, 20090, 20172, [], "llm_providers = [", "llm_layout.addLayout(llm_row)")
apply(F, L, 3, 19891, 19892, [], "api_keys = self.load_api_keys()", "enabled_providers = self.load_provider_enabled_states()")

# ---------- modules/quicktrans.py ----------
F, L = load("modules/quicktrans.py", 1626)
HAS_KEY = ["            # Batch #9.4: единственный LLM — Custom; ключ живёт в профиле,",
           "            # ключа в api_keys.txt не требует.",
           "            has_key = True"]
DOCSTR = ["        Batch #9.3/#9.4: облачные LLM (Claude/OpenAI/Gemini/Mistral/",
          "        DeepSeek/OpenRouter) и Ollama удалены из движка и UI — остаётся",
          "        только Custom (активный профиль custom_openai, чип CUS).\"\"\""]
apply(F, L, 4, 373, 378, HAS_KEY, "if api_key_name == 'gemini':", "has_key = bool(api_keys.get(api_key_name))")
apply(F, L, 5, 357, 361, DOCSTR, "Batch #9.3: облачные LLM", "«Local LLM» после 9.4 показывается как профиль Custom.")
apply(F, L, 6, 113, 113, ['    provider_code: str  # Short code: "CMT", "CUS", …'],
      'provider_code: str  # Short code:', 'provider_code: str  # Short code:')
apply(F, L, 7, 59, 59, ['_AI_PROVIDER_CODES = {"CUS"}'], '_AI_PROVIDER_CODES = {', '_AI_PROVIDER_CODES = {')
apply(F, L, 8, 32, 38, [], '"CL":  "#D97706"', '"OLL": "#555555"')

# ---------- modules/chat_view_widget.py ----------
MENU = [
    "    def _show_model_menu(self):",
    "        \"\"\"Show the active Custom profile/model and a link to AI Settings.",
    "",
    "        Batch #9.4: облачные провайдеры и Ollama удалены — чат использует",
    "        активный профиль Custom (OpenAI-Compatible) из AI Settings; модель",
    "        переключается там же, не из чата.\"\"\"",
    "        menu = QMenu(self)",
    "        menu.setStyleSheet(\"QMenu { font-size: 9pt; } QMenu::item { padding: 4px 16px; }\")",
    "",
    "        parent_app = getattr(self._backend, '_parent_app', None)",
    "        settings = None",
    "        if parent_app is not None and hasattr(parent_app, 'load_llm_settings'):",
    "            try:",
    "                settings = parent_app.load_llm_settings()",
    "            except Exception:",
    "                settings = None",
    "        profile = None",
    "        if parent_app is not None and hasattr(parent_app, '_get_active_custom_profile'):",
    "            try:",
    "                profile = parent_app._get_active_custom_profile(settings)",
    "            except Exception:",
    "                profile = None",
    "",
    "        if profile:",
    "            header = menu.addAction(",
    "                f\"🔌 {profile.get('name', 'Custom')} – {profile.get('model', '')}\")",
    "        else:",
    "            header = menu.addAction(\"🔌 Custom profile not configured\")",
    "        header.setEnabled(False)",
    "",
    "        menu.addSeparator()",
    "        act = menu.addAction(\"AI Settings…\")",
    "        act.triggered.connect(self._open_ai_settings)",
    "",
    "        pos = self._model_btn.mapToGlobal(self._model_btn.rect().topLeft())",
    "        pos.setY(pos.y() - menu.sizeHint().height())",
    "        menu.exec(pos)",
    "",
    "    def _open_ai_settings(self):",
    "        \"\"\"Navigate the main window to Settings → AI Settings.\"\"\"",
    "        parent_app = getattr(self._backend, '_parent_app', None)",
    "        if parent_app is not None and hasattr(parent_app, '_go_to_settings_tab'):",
    "            parent_app._go_to_settings_tab(\"AI Settings\")",
]
F, L = load("modules/chat_view_widget.py", 1024)
apply(F, L, 9, 603, 673, [], "def _on_model_selected", "self._backend.add_message(\"system\", f\"\\u26A0 Failed to switch model: {e}\")")
apply(F, L, 10, 540, 601, MENU, "def _show_model_menu", "menu.exec(pos)")

print("ALL 9.4d EDITS OK")
