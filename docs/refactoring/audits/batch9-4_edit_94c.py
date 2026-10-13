# Batch 9.4c editor: status-bar _update_llm_indicator -> single Custom branch;
# Local LLM read-only note in the Custom profiles section. Bottom-up, py_compile
# after each edit.
import pathlib, subprocess, sys

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
PY = r"E:\Dev\python-embed\python.exe"
F = ROOT / "Supervertaler.py"

raw = F.read_bytes()
lines = raw.decode("utf-8").split("\r\n")
assert len(lines) == 55092, len(lines)

NOTE = [
    "        # Local LLM (read-only): local servers are reached through the Custom",
    "        # profiles above; management of the local server itself — future batch.",
    "        local_llm_note = QLabel(self.tr(",
    "            \"ℹ️ Local LLM: local servers are used via the Custom \"",
    "            \"(OpenAI-Compatible) profiles above. Local server management is \"",
    "            \"coming later.\"))",
    "        local_llm_note.setStyleSheet(\"font-size: 8pt; color: #666;\")",
    "        local_llm_note.setWordWrap(True)",
    "        model_layout.addWidget(local_llm_note)",
]

INDICATOR = [
    "    def _update_llm_indicator(self):",
    "        \"\"\"Обновить индикатор LLM в статусной строке.",
    "",
    "        После Batch #9.3 единственный рабочий провайдер — Custom",
    "        (OpenAI-Compatible): индикатор показывает активный профиль и его модель;",
    "        если профиль не настроен — сообщение о ненастроенности.\"\"\"",
    "        try:",
    "            settings = self.load_llm_settings()",
    "            profile = self._custom_llm_ready(settings)",
    "            if profile:",
    "                model = (profile.get('model') or '').strip()",
    "                display = f\"🔌 {profile.get('name', 'Custom')}: {model}\"",
    "                tip = (f\"Custom (OpenAI-Compatible): {profile.get('name', 'Custom')}\\n\"",
    "                       f\"Model: {model}\\nEndpoint: {profile.get('endpoint', '')}\")",
    "            else:",
    "                display = \"🔌 Custom profile not configured\"",
    "                tip = self.tr(\"Custom LLM profile is not configured — Settings → AI Settings\")",
    "            if hasattr(self, 'llm_indicator_label'):",
    "                self.llm_indicator_label.setText(display)",
    "                self.llm_indicator_label.setToolTip(tip)",
    "        except Exception:",
    "            if hasattr(self, 'llm_indicator_label'):",
    "                self.llm_indicator_label.setText(\"\")",
]

EDITS = [
    (19314, 19314, NOTE),          # insert after addWidget(custom_model_label)
    (7570, 7615, INDICATOR),       # replace whole _update_llm_indicator body
]

for i, (a, b, repl) in enumerate(EDITS, 1):
    anchor = lines[a-1].strip()
    if i == 1:
        assert anchor == "model_layout.addWidget(custom_model_label)", (i, anchor)
    else:
        assert anchor.startswith("def _update_llm_indicator"), (i, anchor)
        assert lines[b-1].strip() == 'self.llm_indicator_label.setText("")', (i, lines[b-1][:60])
    lines[a-1:b] = repl
    out = "\r\n".join(lines).encode("utf-8")
    F.write_bytes(out)
    r = subprocess.run([PY, "-m", "py_compile", str(F)], capture_output=True, text=True)
    crlf = out.count(b"\r\n"); lf = out.count(b"\n"); dcr = out.count(b"\r\r\n")
    print(f"edit {i} ({a}-{b} -> {len(repl)}): rc={r.returncode} lines={len(lines)} CRLF={crlf} LF={lf} dCR={dcr}")
    if r.returncode != 0:
        print(r.stderr); sys.exit(1)
    if lf != crlf or dcr != 0:
        print("EOL ANOMALY"); sys.exit(1)

print("ALL 9.4c EDITS OK; final line count:", len(lines))
