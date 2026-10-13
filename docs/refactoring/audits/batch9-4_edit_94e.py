# Batch 9.4e editor: llm_clients tails (set_ollama_timeout, *_MODELS,
# OLLAMA_ENDPOINT env), llm_pricing _FREE_PROVIDERS, user-facing texts
# (show_about, batch dialog checkbox, proxy_note, setup.py keywords,
# help_system AI_OLLAMA, AI tab docstring). Anchored by exact strings.
import pathlib, subprocess, sys

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
PY = r"E:\Dev\python-embed\python.exe"

def load(rel):
    F = ROOT / rel
    raw = F.read_bytes().decode("utf-8")
    nl = "\r\n" if raw.count("\r\n") >= raw.count("\n") / 2 else "\n"
    return F, raw.split(nl), nl

def find(lines, needle, start=0):
    hits = [i for i in range(start, len(lines)) if needle in lines[i]]
    assert len(hits) == 1, (needle, hits)
    return hits[0]

def find_exact(lines, text, start=0):
    hits = [i for i in range(start, len(lines)) if lines[i] == text]
    assert len(hits) >= 1, (text, hits)
    return hits[0]

def apply(F, lines, nl, i, a, b, repl, anchor_start, anchor_end):
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
    if dcr != 0:
        print("EOL ANOMALY"); sys.exit(1)

# ---------- modules/llm_clients.py (LF) ----------
F, L, NL = load("modules/llm_clients.py")
# 1: OLLAMA_ENDPOINT env block (comment + if + assign)
a = find(L, "# Set environment variable for Ollama endpoint if configured")
b = find(L, "os.environ['OLLAMA_ENDPOINT']")
apply(F, L, NL, 1, a+1, b+1, [], "# Set environment variable for Ollama endpoint", "os.environ['OLLAMA_ENDPOINT']")
# 2: _ollama_timeout_override comment+var+blank+def
a = find(L, "# User-chosen Ollama request timeout in seconds")
b = find(L, "_ollama_timeout_override = int(seconds) if seconds and int(seconds) > 0 else None")
apply(F, L, NL, 2, a+1, b+1, [], "# User-chosen Ollama request timeout", "_ollama_timeout_override = int(seconds)")
# 3: MISTRAL_MODELS comment+dict
a = find(L, "# Available Mistral models with descriptions")
b = find_exact(L, "    }", a)  # dict closing brace at indent 4
apply(F, L, NL, 3, a+1, b+1, [], "# Available Mistral models", "}")
# 4: OPENROUTER_MODELS comment+dict
a = find(L, "# Available OpenRouter models (curated selection)")
b = find_exact(L, "    }", a)
apply(F, L, NL, 4, a+1, b+1, [], "# Available OpenRouter models", "}")
# 5: OLLAMA_MODELS comment+dict
a = find(L, "# Available Ollama models with descriptions (for UI display)")
b = find_exact(L, "    }", a)
apply(F, L, NL, 5, a+1, b+1, [], "# Available Ollama models", "}")
# 6: CLAUDE_MODELS comment+dict
a = find(L, "# Available Claude models with descriptions - the chat's model menu.")
b = find_exact(L, "    }", a)
apply(F, L, NL, 6, a+1, b+1, [], "# Available Claude models", "}")

# ---------- modules/llm_pricing.py (LF) ----------
F, L, NL = load("modules/llm_pricing.py")
FREE = ["# Batch #9.4: Ollama удалён — бесплатных провайдеров нет;",
        "# custom_openai falls through to the price list, so a custom model gains",
        "# a cost figure as soon as its id + rate are added to pricing.json —",
        "# otherwise its cost is reported as unknown (None), not free.",
        "_FREE_PROVIDERS = ()"]
a = find(L, "# Ollama is unconditionally free.")
b = find(L, '_FREE_PROVIDERS = ("ollama",)')
apply(F, L, NL, 7, a+1, b+1, FREE, "# Ollama is unconditionally free.", '_FREE_PROVIDERS = ("ollama",)')

# ---------- modules/help_system.py (LF) ----------
F, L, NL = load("modules/help_system.py")
a = find(L, "AI_OLLAMA")
apply(F, L, NL, 8, a+1, a+1, [], "AI_OLLAMA", "AI_OLLAMA")

# ---------- setup.py (LF) ----------
F, L, NL = load("setup.py")
a = find(L, '"GPT",')
apply(F, L, NL, 9, a+1, a+4, [], '"GPT",', '"Ollama",')

# ---------- Supervertaler.py (CRLF) ----------
F, L, NL = load("Supervertaler.py")
# 10: proxy_note text
a = find(L, "Applies to: OpenAI, Claude, Gemini, Mistral, Ollama, Google Translate, DeepL,")
NEW_NOTE = ['            "ⓘ  Applies to: Custom (OpenAI-Compatible), Google Translate, DeepL,"',
            '            "    Microsoft Translator, ModernMT, and MyMemory."']
apply(F, L, NL, 10, a+1, a+2, NEW_NOTE, '"ⓘ  Applies to: OpenAI', '"    Microsoft Translator, ModernMT, and MyMemory."')
# 11: show_about text
a = find(L, "Built with PyQt6 • Supports OpenAI, Claude, Gemini & Ollama")
apply(F, L, NL, 11, a+1, a+1,
      ['            "Built with PyQt6 • Supports Custom (OpenAI-Compatible) LLMs"'],
      '"Built with PyQt6 • Supports OpenAI', '"Built with PyQt6 • Supports OpenAI')
# 12: batch dialog checkbox
a = find(L, "🤖 LLM (AI) - Use configured LLM provider (GPT, Claude, Gemini)")
apply(F, L, NL, 12, a+1, a+1,
      ['            llm_checkbox = CheckmarkCheckBox(self.tr("🤖 LLM (AI) - Use configured LLM provider (Custom OpenAI-Compatible)"))'],
      'llm_checkbox = CheckmarkCheckBox(self.tr("🤖 LLM (AI)', 'llm_checkbox = CheckmarkCheckBox(self.tr("🤖 LLM (AI)')
# 13: AI tab docstring
a = find(L, "Создаёт единую вкладку AI Settings — объединяет настройки LLM, Ollama и AI Assistant.")
apply(F, L, NL, 13, a+1, a+1,
      ['        """Создаёт единую вкладку AI Settings — настройки Custom (OpenAI-Compatible) LLM и AI Assistant."""'],
      '"""Создаёт единую вкладку AI Settings', '"""Создаёт единую вкладку AI Settings')

print("ALL 9.4e EDITS OK")
