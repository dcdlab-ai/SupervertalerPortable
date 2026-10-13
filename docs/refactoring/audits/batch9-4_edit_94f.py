# Batch 9.4f editor: per-profile Custom chips in QuickTrans.
#  1. _get_active_custom_profile(settings, profile_name=None) — optional name.
#  2. _custom_llm_ready(settings, profile_name=None) — pass-through.
#  3. create_llm_client(..., profile_name=None) — pass-through.
#  4. QuickTrans tab: per-profile enable checkboxes under the Custom row.
#  5. _save_mt_quick_lookup_settings: persist mtql_llm_profiles.
#  6. quicktrans.py _add_llm_providers: chip per enabled profile (code CUS).
#  7. quicktrans.py _call_llm_translation: profile_name plumbing.
# Anchored by exact strings; py_compile after each edit.
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

def find_first(lines, needle, start=0):
    for i in range(start, len(lines)):
        if needle in lines[i]:
            return i
    raise AssertionError(needle)

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

# ================= Supervertaler.py (CRLF) =================
F, L, NL = load("Supervertaler.py")

# --- 1: _get_active_custom_profile signature + name lookup ---
if any("def _get_active_custom_profile(self, settings=None, profile_name=None):" in x for x in L):
    print("edit 1: already applied, skip")
else:
    a = find(L, "def _get_active_custom_profile(self, settings=None):")
    b = find(L, "active_name = settings.get('custom_openai_active_profile', '')")
    SIG = ["    def _get_active_custom_profile(self, settings=None, profile_name=None):",
           "        \"\"\"Возвращает словарь профиля custom_openai (endpoint, model, api_key).",
           "",
           "        profile_name (Batch #9.4f) — имя конкретного профиля для чипа QuickTrans;",
           "        без него — активный профиль (активный по имени -> первый -> легаси-конфиг).",
           "        Возвращает словарь с ключами name, endpoint, model, api_key — или None.\"\"\"",
           "        if settings is None:",
           "            settings = self.load_llm_settings()",
           "        profiles = settings.get('custom_openai_profiles', [])",
           "        active_name = profile_name if profile_name else settings.get('custom_openai_active_profile', '')"]
    apply(F, L, NL, 1, a+1, b+1, SIG, "def _get_active_custom_profile(self, settings=None):", "active_name = settings.get('custom_openai_active_profile', '')")

# --- 2: _custom_llm_ready pass-through ---
a = find(L, "def _custom_llm_ready(self, settings=None):")
b = find_first(L, "profile = self._get_active_custom_profile(settings)", a)
READY = ["    def _custom_llm_ready(self, settings=None, profile_name=None):",
         "        \"\"\"Профиль Custom с непустым endpoint — единственная рабочая",
         "        конфигурация LLM после Batch #9.3 (провайдер custom_openai).",
         "",
         "        Возвращает словарь профиля или None. Читатели «не настроено» дают",
         "        единое сообщение \"Custom LLM profile is not configured — Settings →",
         "        AI Settings\" вместо сетевой ошибки на api.openai.com с ключом-",
         "        заглушкой. profile_name (Batch #9.4f) — конкретный профиль чипа.",
         "        \"\"\"",
         "        if settings is None:",
         "            settings = self.load_llm_settings()",
         "        profile = self._get_active_custom_profile(settings, profile_name)"]
apply(F, L, NL, 2, a+1, b+1, READY, "def _custom_llm_ready(self, settings=None):", "profile = self._get_active_custom_profile(settings)")

# --- 3: create_llm_client pass-through ---
a = find(L, "def create_llm_client(self, provider, model, api_keys, settings=None):")
b = find_first(L, "profile = self._get_active_custom_profile(settings)", a)
apply(F, L, NL, 3, a+1, a+1,
      ["    def create_llm_client(self, provider, model, api_keys, settings=None, profile_name=None):"],
      "def create_llm_client(self, provider, model, api_keys, settings=None):",
      "def create_llm_client(self, provider, model, api_keys, settings=None):")
apply(F, L, NL, 4, b+1, b+1,
      ["        profile = self._get_active_custom_profile(settings, profile_name)"],
      "profile = self._get_active_custom_profile(settings)",
      "profile = self._get_active_custom_profile(settings)")

# --- 4: QuickTrans tab per-profile checkboxes ---
a = find(L, "llm_layout.addLayout(custom_row)")
PROF = ["",
        "        # Batch #9.4f: чип на каждый включённый профиль Custom (pattern of",
        "        # Custom MT above). Master checkbox mtql_custom_openai gates the group;",
        "        # mtql_llm_profiles stores the enabled profile names.",
        "        self._mtql_llm_profile_cbs = {}",
        "        _llm_profiles = llm_settings.get('custom_openai_profiles') or []",
        "        _enabled_names = mt_quick_settings.get('mtql_llm_profiles')",
        "        if _enabled_names is None:",
        "            _enabled_names = [p.get('name') for p in _llm_profiles if p.get('name')]",
        "        for _p in _llm_profiles:",
        "            _pname = _p.get('name')",
        "            if not _pname:",
        "                continue",
        "            _row = QHBoxLayout()",
        "            _row.setContentsMargins(24, 0, 0, 0)",
        "            _cb = CheckmarkCheckBox(f\"{_pname} – {_p.get('model', '')}\")",
        "            _cb.setChecked(_pname in _enabled_names)",
        "            _cb.setToolTip(self.tr(\"Query this Custom profile in QuickTrans\"))",
        "            self._mtql_llm_profile_cbs[_pname] = _cb",
        "            _row.addWidget(_cb)",
        "            _row.addStretch()",
        "            llm_layout.addLayout(_row)"]
apply(F, L, NL, 5, a+1, a+1, PROF, "llm_layout.addLayout(custom_row)", "llm_layout.addLayout(custom_row)")

# --- 5: save mtql_llm_profiles ---
a = find(L, "general_settings['mt_quick_lookup'] = mt_quick_settings")
SAVE = ["        # Batch #9.4f: enabled Custom profile names for QuickTrans chips.",
        "        if getattr(self, '_mtql_llm_profile_cbs', None):",
        "            mt_quick_settings['mtql_llm_profiles'] = [",
        "                name for name, cb in self._mtql_llm_profile_cbs.items() if cb.isChecked()]",
        "",
        "        general_settings['mt_quick_lookup'] = mt_quick_settings"]
apply(F, L, NL, 6, a+1, a+1, SAVE, "general_settings['mt_quick_lookup'] = mt_quick_settings",
      "general_settings['mt_quick_lookup'] = mt_quick_settings")

# ================= modules/quicktrans.py (LF) =================
F, L, NL = load("modules/quicktrans.py")

# --- 6: _add_llm_providers per-profile chips ---
a = find(L, "        # LLM provider definitions: (name, code, api_key_name, settings_key)")
b = find(L, "            providers.append((name, code, make_llm_caller(name, api_key_name, model)))")
CHIPS = ["        # Batch #9.4f: master checkbox mtql_custom_openai gates the group;",
         "        # mtql_llm_profiles (list of profile names) selects which profiles get",
         "        # their own CUS chip. Empty/missing list = every profile with an",
         "        # endpoint gets a chip (pre-9.4f settings keep working).",
         "        if not mt_quick_settings.get('mtql_custom_openai', False):",
         "            return",
         "",
         "        llm_settings = {}",
         "        if hasattr(self, 'parent_app') and self.parent_app and hasattr(self.parent_app, 'load_llm_settings'):",
         "            try:",
         "                llm_settings = self.parent_app.load_llm_settings() or {}",
         "            except Exception:",
         "                llm_settings = {}",
         "        profiles = llm_settings.get('custom_openai_profiles') or []",
         "        enabled = mt_quick_settings.get('mtql_llm_profiles')",
         "        _added = 0",
         "",
         "        def make_llm_caller(provider_model, profile_name):",
         "            def call_llm(text, src_lang, tgt_lang):",
         "                return self._call_llm_translation('custom_openai', text, src_lang, tgt_lang,",
         "                                                 provider_model, profile_name)",
         "            return call_llm",
         "",
         "        for prof in profiles:",
         "            pname = prof.get('name')",
         "            if not pname:",
         "                continue",
         "            if not (prof.get('endpoint') or '').strip():",
         "                continue",
         "            if enabled is not None and pname not in enabled:",
         "                continue",
         "            providers.append((pname, \"CUS\",",
         "                              make_llm_caller((prof.get('model') or '').strip(), pname)))",
         "            _added += 1",
         "",
         "        if profiles:",
         "            return",
         "",
         "        # No profiles configured: legacy single-field endpoint (pre-profiles",
         "        # settings.json) keeps the single 'Custom' chip.",
         "        model = mt_quick_settings.get('mtql_custom_openai_model', None)",
         "        providers.append((\"Custom\", \"CUS\", make_llm_caller(model, None)))"]
apply(F, L, NL, 7, a+1, b+1, CHIPS, "# LLM provider definitions: (name, code, api_key_name, settings_key)",
      "providers.append((name, code, make_llm_caller(name, api_key_name, model)))")

# --- 7: _call_llm_translation profile_name plumbing ---
a = find(L, "def _call_llm_translation(self, provider: str, text: str, source_lang: str, target_lang: str, model: str = None) -> str:")
b = find(L, "client = self.parent_app.create_llm_client(provider, resolved_model, api_keys, settings=llm_settings)")
apply(F, L, NL, 8, a+1, a+1,
      ["    def _call_llm_translation(self, provider: str, text: str, source_lang: str, target_lang: str, model: str = None, profile_name: str = None) -> str:"],
      "def _call_llm_translation(self, provider: str, text: str, source_lang: str, target_lang: str, model: str = None) -> str:",
      "def _call_llm_translation(self, provider: str, text: str, source_lang: str, target_lang: str, model: str = None) -> str:")
apply(F, L, NL, 9, b+1, b+1,
      ["                client = self.parent_app.create_llm_client(provider, resolved_model, api_keys,",
       "                                                 settings=llm_settings, profile_name=profile_name)"],
      "client = self.parent_app.create_llm_client(provider, resolved_model, api_keys, settings=llm_settings)",
      "client = self.parent_app.create_llm_client(provider, resolved_model, api_keys, settings=llm_settings)")

print("ALL 9.4f EDITS OK")
