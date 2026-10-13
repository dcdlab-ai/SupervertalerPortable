# Batch 9.4 — ЭТАП 1 recon (no edits)

## п.1 AI Settings page `_create_ai_settings_tab` (AST 19340–20415)
| element | key(s) | readers | verdict |
|---|---|---|---|
| Section 1 radios openai/claude/gemini/mistral/deepseek/openrouter/ollama (19374–19408) | provider | save chain 23671–23688 | DELETE (custom radio 19410–19414 KEEP) |
| Section 2 model combos openai/claude/gemini/mistral/deepseek/openrouter (19426–19596) | *_model | save 23737–23742 | DELETE |
| Ollama label + LocalLLMStatusWidget try-import (19598–19620) | ollama_model | save 23690–23695 | DELETE (importers of local_llm_setup die here) |
| Custom profiles section (19622–19789) | custom_openai_* | 9.1 logic | KEEP (inviolable) |
| `_friendly_model_name`/`_update_provider_label` + connects + initial labels (19791–19833) | — | remote radios only | DELETE |
| `update_combo_states` (19836–19851) | — | remote widgets | REDUCE to custom-only |
| `on_ollama_selected` (19853–19881) | — | ollama radio | DELETE (2nd local_llm_setup importer) |
| radio toggled connects (19883–19891) | — | — | REDUCE to custom only |
| API Keys section (19896–19941), llm_key_fields 7 remote keys, NO custom field | openai/claude/gemini/mistral/deepseek/openrouter/ollama_endpoint | `_api_key_inputs` → `_save_api_keys_from_ui` | DELETE whole group (custom key lives in profile fields; save guard `if not self._api_key_inputs: return` handles empty) |
| Enable checkboxes 6 remote (19954–19976) | llm_openai/claude/gemini/mistral/openrouter/ollama | save 23760–23768 | DELETE (custom 19978–19980 KEEP) |
| Proxy section (19985–20050) | proxy | live | KEEP; proxy_note text 20042–20047 names deleted providers → text fix 9.4e |
| Section 4 Ollama Advanced (20052–20093) | ollama_keepwarm, ollama_timeout_minutes | keepwarm cluster, save | DELETE |
| Section 5 Preferences (20095–20312) | batch_size, surrounding_segments, use_full_context, context_window_size, persist_usage_log, monthly_budget_usd, check_tm_*, lookup_delay, quicklauncher_context_percent | live | KEEP |
| Section 6: llm_matching_cb (20318–20327) | enable_llm_matching | INERT: prefetch stub 28655 `pass`, dead 52429/52563 | DELETE UI (dead methods untouched, 8.18) |
| llm_spin, FuzzyFixer (20334–20381) | match_limits.LLM, fuzzy_fixer_* | live | KEEP |
| Save lambda (20390–20410) | — | — | REDUCE |

## п.2 save functions
- `_save_ai_settings_from_ui` (23650–23859): provider chain → 'custom_openai'; ollama_model block DELETE; profiles/9.1 snapshot KEEP; new_settings: remote `*_model` + `ollama_model` writes DELETE, custom_* KEEP; ollama_timeout write + `_apply_ollama_timeout_setting` DELETE; enabled_states → preserve existing + set llm_custom_openai only; enable_llm_matching + ollama_keepwarm writes DELETE; keepwarm timer calls DELETE; `_update_llm_indicator` KEEP; `_save_api_keys_from_ui` KEEP; proxy KEEP; `_apply_gemini_proxy` DELETE in 9.4b.
- `_save_api_keys_from_ui` (23861–23872): KEEP verbatim (guard handles empty `_api_key_inputs`; google→gemini migration KEEP — pdf_rescue_Qt.py:88 live reader).

## п.3 Ollama tails
- keepwarm cluster `_setup_ollama_keepwarm` 7623–7632, `_apply_ollama_timeout_setting` 7634–7643, `_start_/_stop_ollama_keepwarm_timer` 7645–7661, `_ping_ollama_keepwarm` 7663–7696 → DELETE.
- calls: init 7554–7557; Save 23827–23831 + 23752; `_apply_gemini_proxy` 48173–48184 calls 6363 (startup) + 23856 (Save) → DELETE cluster+calls in 9.4b. closeEvent: no keepwarm calls (verified 27001–27047, 49218–49245).

## п.4 local_llm_setup.py
Importers ONLY Supervertaler.py 19604 + 19857 (both die in 9.4a) → `git rm` in 9.4b.

## п.5 Local LLM
NO separate Settings page exists — Local LLM was a section inside AI Settings (Ollama radio + embedded widget + Advanced group). After 9.4a it's gone. Minimal plan (9.4c): Custom profiles section in AI Settings gets a read-only note "local server management coming later"; NO second profile editor.

## п.6 status bar `_update_llm_indicator` (7576–7621)
8 provider branches → single custom: "🔌 {profile}: {model}"; not-configured → "🔌 Custom profile not configured" (via `_custom_llm_ready`). Update points: startup 7507, live save 23840 (KEEP), dead 23645 (untouched).

## п.7 QuickTrans tab (20426–20818)
- LLM group: popup_ai_cb KEEP; `llm_providers` list + loop (20637–20719) DELETE; custom row (20721–20746) KEEP (checkbox mtql_custom_openai + read-only active-profile model); ollama row (20748–20765) DELETE.
- `_save_mt_quick_lookup_settings` (20780–20818): generic registry loops — no change.
- quicktrans.py: PROVIDER_COLORS delete CL/GPT/GEM/MIS/DS/OR/OLL (keep CMT/CUS); `_AI_PROVIDER_CODES` → {"CUS"}; `_add_llm_providers` has_key branch: delete gemini/ollama branches.

## п.8 9.4f evaluation (profile selection in QuickTrans)
Pattern = Custom MT: master checkbox + per-profile `enabled` flag + per-profile chip (quicktrans.py 332–346).
Design: master "Custom (OpenAI-Compatible)" checkbox (existing mtql_custom_openai) + per-profile enable checkboxes in tab; storage `mtql_llm_profiles` (list of names) in mt_quick_settings; `_add_llm_providers` loops custom_openai_profiles → chip per enabled profile (name label, code CUS); execution: `create_llm_client(..., profile_name=None)` optional param (Supervertaler.py factory, NOT LLMClient) + `_get_active_custom_profile(settings, profile_name=None)`; default behavior unchanged.
Estimate: tab ~35 + quicktrans ~30 + factory/profile-resolver optional param ~15 + save ~10 ≈ 90 net lines. No LLMClient edits. No change to global custom_openai_active_profile.
Risks: parallel requests to one local server (llama-server handles parallel; noted); deleted/renamed profile → stale name skipped by filter; empty list → no chips. Compatible with variant (a) (master checkbox = variant (a) checkbox).
DECISION: gate satisfied (≤100, no LLMClient, no global profile change) → IMPLEMENT as 9.4f.

## п.9 chat menu (chat_view_widget 540–673)
`_show_model_menu` → active profile+model info (read-only, no global change) + "AI Settings…" → `_go_to_settings_tab`; `_on_model_selected` DELETE.

## п.10 llm_clients.py tails
`set_ollama_timeout`/`_ollama_timeout_override` (124–134) DELETE; MISTRAL/OPENROUTER/OLLAMA/CLAUDE_MODELS DELETE (sole readers = chat menu, dies 9.4d); load_api_keys ollama_endpoint env block (117–119) DELETE (readers local_llm_setup:172 + Supervertaler 7675 die in 9.4b); google→gemini KEEP.

## п.11 llm_pricing
`_FREE_PROVIDERS = ("ollama",)` → `()`; readers 147/177 handle empty; historical provider=ollama cost → None "unknown" (acceptable).

## п.12 texts (user-facing → fix 9.4e; code comments → 8.16)
- show_about 49190 "Supports OpenAI, Claude, Gemini & Ollama"
- batch dialog checkbox 50639 "(GPT, Claude, Gemini)"
- proxy_note 20042–20047 "Applies to: OpenAI, Claude, Gemini, Mistral, Ollama, …"
- setup.py 80–83 keywords
- help_system.py:87 AI_OLLAMA — NO readers → delete line
- `_create_ai_settings_tab` docstring 19341 mentions Ollama
- KEEP: custom_info 19783–84 (OpenAI-compatible examples), "Add a Custom profile" messages, pdf_rescue_Qt (PROTECTED), vision texts (9.5), translation_results_panel (8.18), code comments (ai_actions 79, autocorrect 473, chat_message_delegate 443–446, platform_helpers 108, chat_backend 113–136, superlookup TODO) → 8.16.

## п.13 compatibility
Old settings.json with cloud keys/flags/mtql_*/ollama_*/enable_llm_matching: merge-from-existing logic preserves all keys; load defaults custom-only; silent 9.3 migration keeps provider='custom_openai'.

## Extra verified
- `_clean_provider_prefix` (52613–52618): NO callers → dead cluster 8.18, untouched.
- `_strip_provider_prefix`: does not exist (name in prompt = `_clean_provider_prefix`).
- chat_backend legacy path 151–160: provider always custom_openai after 118 → legacy branch unreachable; KEEP (chat_backend not in 9.4 scope; note in report).
