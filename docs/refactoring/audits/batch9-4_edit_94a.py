# Batch 9.4a editor: AI Settings page + save functions.
# Bottom-up line-range replacements on the CRLF working copy; py_compile after each.
import pathlib, subprocess, sys

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
PY = r"E:\Dev\python-embed\python.exe"
F = ROOT / "Supervertaler.py"

raw = F.read_bytes()
text = raw.decode("utf-8")
lines = text.split("\r\n")
assert len(lines) == 55704, len(lines)

NEW_SAVE = r'''    def _save_ai_settings_from_ui(self,
                                  batch_size_spin, surrounding_spin, full_context_cb, context_slider,
                                  tm_no_check_rb, tm_fuzzy_rb, tm_exact_rb, auto_propagate_cb, delay_spin,
                                  llm_spin,
                                  quicklauncher_context_slider,
                                  custom_radio=None, custom_endpoint_input=None,
                                  custom_model_input=None, custom_enable_cb=None,
                                  custom_profile_combo=None, custom_key_input=None,
                                  custom_profiles_snapshot=None):
        """Сохраняет все настройки ИИ из единой вкладки AI Settings.

        Batch #9.4: удалённые провайдеры (OpenAI, Claude, Gemini, Mistral,
        DeepSeek, OpenRouter, Ollama) из UI убраны — провайдер один,
        custom_openai (активный профиль Custom). Ключи чужих провайдеров в
        settings.json не удаляются и не перезаписываются (merge из
        existing_settings и существующих состояний включённости)."""
        provider = 'custom_openai'

        # Собираем список профилей из ЖИВОГО снимка диалога (кнопки «+»/«−»
        # мутируют его всю сессию; см. _create_ai_settings_tab). Перечитывание
        # диска здесь теряло добавленные за сессию профили и воскрешало
        # удалённые (баг из R9 §1.3). Остальные ключи — как раньше, с диска.
        existing_settings = self.load_llm_settings()
        profiles = (custom_profiles_snapshot or existing_settings).get('custom_openai_profiles', [])
        active_profile_name = ''

        if custom_profile_combo and custom_profile_combo.count() > 0:
            # Sync current field values into the active profile
            idx = custom_profile_combo.currentIndex()
            if 0 <= idx < len(profiles):
                _raw_endpoint = custom_endpoint_input.text().strip() if custom_endpoint_input else ''
                _norm_endpoint = self._normalize_custom_endpoint(_raw_endpoint)
                profiles[idx]['endpoint'] = _norm_endpoint
                if custom_endpoint_input is not None and _norm_endpoint != _raw_endpoint:
                    custom_endpoint_input.setText(_norm_endpoint)  # показать нормализацию в поле
                profiles[idx]['model'] = custom_model_input.text().strip() if custom_model_input else ''
                profiles[idx]['api_key'] = custom_key_input.text().strip() if custom_key_input else ''
            active_profile_name = custom_profile_combo.currentText()
            # Активным может стать только существующий профиль: если имя из
            # комбо в списке не найдено, берём первый (пустой список — пусто).
            if not any(p.get('name') == active_profile_name for p in profiles):
                active_profile_name = profiles[0].get('name', '') if profiles else ''

        # For legacy compat, store flat fields from the ACTIVE profile of the
        # list (после синка выше это те же видимые поля; при нуле профилей —
        # пустые строки, зеркала больше не расходятся с профилями).
        active_profile = next((p for p in profiles if p.get('name') == active_profile_name), None)
        active_endpoint = (active_profile or {}).get('endpoint', '')
        active_model = (active_profile or {}).get('model', '')

        # Start from what is already saved: llm_settings also holds keys this
        # tab does not own (the QuickTrans custom MT profiles), and replacing
        # the whole dict used to delete them every time AI settings were saved.
        new_settings = dict(existing_settings)
        new_settings.update({
            'provider': provider,
            'custom_openai_model': active_model,
            'custom_openai_endpoint': active_endpoint,
            'custom_openai_profiles': profiles,
            'custom_openai_active_profile': active_profile_name
        })
        self.save_llm_settings(new_settings)

        # Update current provider and model attributes for AI Assistant
        self.current_provider = provider
        self.current_model = active_model

        # Save LLM provider enabled states: only the Custom flag is owned by
        # this page now; everything already on disk (mt_*, legacy llm_*) is
        # preserved untouched.
        existing_states = self.load_provider_enabled_states()
        existing_states['llm_custom_openai'] = custom_enable_cb.isChecked() if custom_enable_cb else True
        self.save_provider_enabled_states(existing_states)

        # Save all general settings including AI-related ones
        general_prefs = self.load_general_settings()
        general_prefs['batch_size'] = batch_size_spin.value()
        general_prefs['surrounding_segments'] = surrounding_spin.value()
        general_prefs['use_full_context'] = full_context_cb.isChecked()
        if getattr(self, '_usage_log_cb', None) is not None:
            general_prefs['persist_usage_log'] = self._usage_log_cb.isChecked()
        if getattr(self, '_budget_spin', None) is not None:
            general_prefs['monthly_budget_usd'] = float(self._budget_spin.value())
        try:
            from modules import usage_log as _ul
            _ul.set_enabled(general_prefs.get('persist_usage_log', True))
            self.monthly_budget_usd = float(general_prefs.get('monthly_budget_usd', 0.0) or 0.0)
        except Exception:
            pass
        general_prefs['context_window_size'] = context_slider.value()
        general_prefs['quicklauncher_context_percent'] = quicklauncher_context_slider.value()
        # Save TM check mode settings
        general_prefs['check_tm_before_api'] = not tm_no_check_rb.isChecked()
        general_prefs['check_tm_exact_only'] = tm_exact_rb.isChecked()
        # 'auto_propagate_100' is deprecated — auto-fill is now the single
        # 'auto_fill_100_matches' key owned by the General tab → TM settings.
        general_prefs['lookup_delay'] = delay_spin.value()
        # v1.10.155: auto_generate_markdown is now saved by the General tab,
        # not here — see _create_general_settings_tab → Document Import group.

        # Update LLM match limits
        if 'match_limits' not in general_prefs:
            general_prefs['match_limits'] = {}
        general_prefs['match_limits']['LLM'] = llm_spin.value()

        # Save FuzzyFixer thresholds (clamp so min <= max)
        if getattr(self, 'fuzzy_fixer_min_spin', None) is not None and getattr(self, 'fuzzy_fixer_max_spin', None) is not None:
            ff_min = self.fuzzy_fixer_min_spin.value()
            ff_max = self.fuzzy_fixer_max_spin.value()
            if ff_min > ff_max:
                ff_min, ff_max = ff_max, ff_min
            self.fuzzy_fixer_min_pct = ff_min
            self.fuzzy_fixer_max_pct = ff_max
            general_prefs['fuzzy_fixer_min_pct'] = ff_min
            general_prefs['fuzzy_fixer_max_pct'] = ff_max

        self.save_general_settings(general_prefs)

        # Apply LLM match limits to results panels
        if hasattr(self, 'results_panels'):
            for panel in self.results_panels:
                if hasattr(panel, 'match_limits'):
                    panel.match_limits['LLM'] = llm_spin.value()

        # Update LLM indicator in status bar
        self._update_llm_indicator()

        # Save API keys from inline fields
        self._save_api_keys_from_ui()

        # Save proxy settings
        if hasattr(self, 'proxy_enabled_cb'):
            proxy_settings = {
                'enabled': self.proxy_enabled_cb.isChecked(),
                'host': self.proxy_host_input.text().strip(),
                'port': self.proxy_port_spin.value(),
                'username': self.proxy_user_input.text().strip(),
                'password': self.proxy_pass_input.text().strip(),
            }
            self.save_proxy_settings(proxy_settings)
            # Re-apply Gemini env vars immediately
            self._apply_gemini_proxy()

        self.log(f"✓ AI settings saved: Provider={provider}, Model={self.current_model}")
        QMessageBox.information(self, "Settings Saved", "AI settings have been saved successfully.")'''.split("\n")

NEW_LAMBDA = r'''        save_btn.clicked.connect(lambda: self._save_ai_settings_from_ui(
            batch_size_spin, surrounding_spin, full_context_cb, context_slider,
            tm_no_check_rb, tm_fuzzy_rb, tm_exact_rb, None, delay_spin,
            llm_spin,
            quicklauncher_context_slider,
            custom_radio=custom_radio, custom_endpoint_input=custom_endpoint_input,
            custom_model_input=custom_model_input, custom_enable_cb=custom_enable_cb,
            custom_profile_combo=custom_profile_combo, custom_key_input=custom_key_input,
            custom_profiles_snapshot=settings
        ))'''.split("\n")

NEW_COMBO_STATES = r'''        def update_combo_states():
            _custom_enabled = custom_radio.isChecked()
            custom_profile_combo.setEnabled(_custom_enabled)
            add_profile_btn.setEnabled(_custom_enabled)
            remove_profile_btn.setEnabled(_custom_enabled and custom_profile_combo.count() > 0)
            custom_endpoint_input.setEnabled(_custom_enabled)
            custom_model_input.setEnabled(_custom_enabled)
            custom_key_input.setEnabled(_custom_enabled)'''.split("\n")

NEW_CONNECTS = r'''        custom_radio.toggled.connect(update_combo_states)'''.split("\n")

# (start, end, replacement) — 1-based inclusive, applied bottom-up
EDITS = [
    (23650, 23859, NEW_SAVE),
    (20390, 20410, NEW_LAMBDA),
    (20318, 20327, []),
    (20052, 20093, []),
    (19954, 19976, []),
    (19896, 19941, []),
    (19853, 19891, NEW_CONNECTS),
    (19836, 19851, NEW_COMBO_STATES),
    (19791, 19833, []),
    (19426, 19620, []),
    (19374, 19408, []),
]

for i, (a, b, repl) in enumerate(EDITS, 1):
    # sanity anchors
    assert lines[a-1].strip().startswith(("openai_radio = CustomRadioButton", "# OpenAI models",
        "# Helper to extract", "def update_combo_states", "# Handler to show",
        "# ========== SECTION 2c", "openai_enable_cb = CheckmarkCheckBox",
        "# ========== SECTION 4", "# LLM matching toggle",
        "save_btn.clicked.connect", "def _save_ai_settings_from_ui")), (i, lines[a-1][:60])
    lines[a-1:b] = repl
    out = "\r\n".join(lines).encode("utf-8")
    F.write_bytes(out)
    r = subprocess.run([PY, "-m", "py_compile", str(F)], capture_output=True, text=True)
    crlf = out.count(b"\r\n"); lf = out.count(b"\n"); dcr = out.count(b"\r\r\n")
    print(f"edit {i} ({a}-{b} -> {len(repl)} lines): py_compile rc={r.returncode} "
          f"lines={len(lines)} CRLF={crlf} LF={lf} dCR={dcr}")
    if r.returncode != 0:
        print(r.stderr); sys.exit(1)
    if lf != crlf or dcr != 0:
        print("EOL ANOMALY"); sys.exit(1)

print("ALL EDITS OK; final line count:", len(lines))
