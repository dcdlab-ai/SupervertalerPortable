"""
Сервис единого файла настроек, извлечённый из Supervertaler.SupervertalerQt
(Batch #7 Stage 2, под-батч S2.1 «Ядро API», Step 7 of EXTRACTION_PLAN.md).

Владелец формата ``<settings_dir>/settings.json`` с четырьмя верхнеуровневыми
секциями: ``"api_keys"``, ``"general"``, ``"ui"``, ``"features"``.

Архитектура (решение владельца V1 по отчёту Batch #7 Stage 1): класс
конструируется ЯВНЫМ каталогом настроек и НЕ резолвит путь к user_data сам — ни
через ``ConfigManager`` (его указатель user_data другой:
``~/.supervertaler_config.json`` против ``%APPDATA%/Supervertaler/config.json``
монолита), ни через какой-либо иной источник. Каталог передаётся ровно тем же
выражением, что было в ``SupervertalerQt._get_settings_dir``:
``self.user_data_path / "workbench" / "settings"``. Окно пересоздаёт сервис в
``SupervertalerQt._reinitialize_with_new_data_path()`` — там же, где
пересоздаются остальные зависящие от каталога данных менеджеры
(``spellcheck_manager``, ``theme_manager``, ``recent_projects_file`` и др.), —
поэтому смена каталога данных не оставляет делегатов на устаревшем пути
(``user_data_path`` переприсваивается в трёх местах монолита, все три ведут в
этот метод).

СЕМАНТИКА, КОТОРУЮ НЕЛЬЗЯ МЕНЯТЬ (Batch #7 Stage 1, §1.9): ни один метод не
кэширует прочитанный JSON между вызовами — файл открывается заново на КАЖДЫЙ
вызов. Никаких ``lru_cache``/«прочитал один раз в __init__ сервиса»/поля-кэша.

SupervertalerQt сохраняет 6 тонких одноимённых делегатов (``_get_settings_dir``,
``_get_unified_settings_path``, ``_load_unified_settings``,
``_save_unified_settings``, ``_load_settings_section``,
``_save_settings_section``), поэтому все call sites продолжают работать без
изменений — включая строковые (getattr) обращения из ``modules/``
(``voice_tab.py``, ``clipboard_manager_widget.py``) и безусловный вызов
``window._load_settings_section("ui")`` из ``main()`` монолита. Ещё не
перенесённые методы монолита (``_migrate_settings_to_unified``,
``_migrate_voice_dictation_default_off`` — уходят в S2.5) тоже ходят через
делегаты.

Тела методов перенесены из монолита ВЕРБАТИМ. Единственная правка —
``_get_settings_dir`` возвращает ``self.settings_dir`` вместо
``self.user_data_path / "workbench" / "settings"`` (инъекция зависимости,
значение то же).

Под-батч S2.2 (тот же Stage 2) добавил сюда три метода общего слоя:
``load_clipboard_privacy_settings``, ``_load_general_settings_from_file`` и
``save_general_settings``; их тела — тоже ВЕРБАТИМ-перенос, вызовы
``self._load_settings_section``/``self._save_settings_section``/``self.log``
внутри них теперь резолвятся в методы этого класса, а не в делегаты монолита.
``load_general_settings`` (97 строк: применение ~35 атрибутов окна) остаётся в
монолите, как и ``save_clipboard_privacy_settings`` — но его внутренний вызов
``self._load_general_settings_from_file()`` идёт через одноимённый делегат и не
менялся.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

__all__ = ["SettingsService"]


class SettingsService:
    """Чтение/запись единого ``settings.json`` (см. докстринг модуля)."""

    def __init__(self, settings_dir: Path,
                 log: Optional[Callable[[str], None]] = None):
        """Запомнить каталог настроек и опциональный лог-колбэк.

        Args:
            settings_dir: каталог настроек
                (``<user_data>/workbench/settings``); путь НЕ резолвится внутри
                сервиса — его передаёт владелец (главное окно).
            log: колбэк окна для сообщений (используется в
                ``_save_unified_settings``); при отсутствии — no-op, чтобы
                перенесённое тело не отличалось от исходного.
        """
        self.settings_dir = Path(settings_dir)
        self.log: Callable[[str], None] = (
            log if callable(log) else (lambda message: None)
        )

    def _get_settings_dir(self) -> Path:
        """Возвращает путь к под-папке настроек."""
        return self.settings_dir

    def _get_unified_settings_path(self) -> Path:
        """Возвращает путь к единому файлу settings.json."""
        return self._get_settings_dir() / "settings.json"

    def _load_unified_settings(self) -> Dict[str, Any]:
        """Загружает весь единый файл настроек."""
        settings_file = self._get_unified_settings_path()
        if not settings_file.exists():
            return {"api_keys": {}, "general": {}, "ui": {}, "features": {}}
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Ensure all sections exist
            for section in ("api_keys", "general", "ui", "features"):
                if section not in data:
                    data[section] = {}
            return data
        except Exception:
            return {"api_keys": {}, "general": {}, "ui": {}, "features": {}}

    def _save_unified_settings(self, data: Dict[str, Any]):
        """Сохраняет весь единый файл настроек."""
        settings_dir = self._get_settings_dir()
        settings_dir.mkdir(parents=True, exist_ok=True)
        settings_file = settings_dir / "settings.json"
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"⚠ Could not save settings: {str(e)}")

    def _load_settings_section(self, section: str) -> Dict[str, Any]:
        """Загружает конкретную секцию из единого файла настроек."""
        return self._load_unified_settings().get(section, {})

    def _save_settings_section(self, section: str, section_data: Dict[str, Any]):
        """Сохраняет конкретную секцию в единый файл настроек (сохраняя остальные секции)."""
        all_settings = self._load_unified_settings()
        all_settings[section] = section_data
        self._save_unified_settings(all_settings)

    # ------------------------------------------------------------------
    # Общие настройки (Batch #7 Stage 2, под-батч S2.2)
    # ------------------------------------------------------------------
    # Тела перенесены из SupervertalerQt ВЕРБАТИМ (единственная правка — их
    # новый адрес). Внутренние вызовы self._load_settings_section /
    # self._save_settings_section / self.log резолвятся в методы ЭТОГО класса
    # (в монолите те же выражения шли через его одноимённые делегаты), поэтому
    # наблюдаемое поведение то же — включая отсутствие кэша (файл открывается
    # заново на каждый вызов, см. докстринг модуля).
    # save_general_settings сохраняет ОБЯЗАТЕЛЬНЫЙ позиционный аргумент settings
    # без default: вызов без аргумента обязан и дальше падать TypeError-ом
    # (предсуществующие сайты SuperlookupTab 66780/66823 — не чинятся здесь).
    # save_clipboard_privacy_settings в сервис НЕ переносится (решение V3: живому
    # refresh нужны Qt-объекты; в монолите остаётся целиком).

    def load_clipboard_privacy_settings(self) -> Dict[str, Any]:
        """Сохранённые настройки захвата/хранения/исключений буфера обмена.
                Возвращает {} при отсутствии сохранённого, поэтому применяются
                собственные дефолты виджета (захват включён — поведение
                как до v1.10.369)."""
        try:
            return self._load_settings_section("features").get('clipboard_privacy', {}) or {}
        except Exception as e:
            self.log(f"⚠ Could not load clipboard privacy settings: {e}")
            return {}

    def _load_general_settings_from_file(self) -> Dict[str, Any]:
        """Загружает общие настройки из единого settings.json (секция general)."""

        defaults = {
            'restore_last_project': False,
            'auto_propagate_exact_matches': True,
            'auto_center_active_segment': True,  # Default to True (like memoQ/Trados)
            'enable_sound_effects': False,
            'sound_effects_map': {
                'glossary_term_added': 'asterisk',
                'glossary_created': 'asterisk',
                'match_inserted': 'ok',
                'glossary_term_duplicate': 'exclamation',
                'glossary_term_error': 'hand'
            },
            'grid_font_size': 11,
            'results_match_font_size': 9,
            'results_compare_font_size': 9
        }

        settings = self._load_settings_section("general")
        if not settings:
            return defaults

        # Merge with defaults to ensure all keys exist
        result = defaults.copy()
        result.update(settings)

        # Migrate termview_* → termlens_* settings keys (v1.9.347+)
        _tv_migrations = {
            'termview_under_grid_visible': 'termlens_under_grid_visible',
            'termview_font_family': 'termlens_font_family',
            'termview_font_size': 'termlens_font_size',
            'termview_font_bold': 'termlens_font_bold',
        }
        for old_key, new_key in _tv_migrations.items():
            if old_key in result and new_key not in result:
                result[new_key] = result.pop(old_key)

        return result

    def save_general_settings(self, settings: Dict[str, Any]):
        """Сохраняет общие настройки в единый settings.json (секция general)."""
        try:
            self._save_settings_section("general", settings)
        except Exception as e:
            self.log(f"⚠ Could not save general settings: {str(e)}")

    # ------------------------------------------------------------------
    # LLM / proxy / provider-state / API keys (Batch #7 Stage 2, S2.3)
    # ------------------------------------------------------------------
    # Тела перенесены из SupervertalerQt ВЕРБАТИМ (единственная правка —
    # адрес). Внутренние вызовы self._load_settings_section,
    # self._save_settings_section, self._load_unified_settings,
    # self._save_unified_settings, self.log, self.load_api_keys,
    # self.load_proxy_settings и self._get_proxy_url резолвятся в методы
    # ЭТОГО класса (в монолите те же выражения шли через его делегаты),
    # поэтому наблюдаемое поведение то же (см. докстринг модуля: кэша нет).

    def load_llm_settings(self) -> Dict[str, str]:
        """Загружает настройки LLM из предпочтений пользователя."""
        defaults = {
            'provider': 'openai',
            'openai_model': 'gpt-5.5',
            'claude_model': 'claude-sonnet-5',
            'gemini_model': 'gemini-3.1-flash-lite',
            'ollama_model': 'translategemma:12b',
            'custom_openai_model': '',
            'custom_openai_endpoint': '',
            'custom_openai_profiles': [],
            'custom_openai_active_profile': '',
            # Custom MT endpoint(s): a dedicated, separate set of OpenAI-compatible
            # endpoints used as MT engines (e.g. a local MT proxy), independent of
            # the AI custom endpoint above so MT and AI can point at different
            # services at the same time.
            'custom_mt_profiles': [],
            'custom_mt_active_profile': ''
        }

        try:
            prefs = self._load_settings_section("ui")
            saved = prefs.get('llm_settings', defaults)
            # Ensure new keys exist for older configs
            for k, v in defaults.items():
                saved.setdefault(k, v)
            # Auto-migrate: old single-field config → profiles
            if not saved.get('custom_openai_profiles') and saved.get('custom_openai_endpoint'):
                api_keys = self.load_api_keys() if hasattr(self, 'load_api_keys') else {}
                saved['custom_openai_profiles'] = [{
                    'name': 'Custom Endpoint',
                    'endpoint': saved['custom_openai_endpoint'],
                    'model': saved.get('custom_openai_model', ''),
                    'api_key': api_keys.get('custom_openai', '')
                }]
                saved['custom_openai_active_profile'] = 'Custom Endpoint'
            return saved
        except:
            return defaults

    def save_llm_settings(self, settings: Dict[str, str]):
        """Сохраняет настройки LLM в предпочтения пользователя."""
        try:
            all_settings = self._load_unified_settings()
            all_settings.setdefault("ui", {})['llm_settings'] = settings
            self._save_unified_settings(all_settings)
        except Exception as e:
            self.log(f"⚠ Could not save LLM settings: {str(e)}")

    def load_proxy_settings(self) -> Dict[str, Any]:
        """Загружает настройки HTTP-прокси из единого хранилища настроек."""
        defaults = {
            'enabled': False,
            'host': '',
            'port': 8080,
            'username': '',
            'password': '',
        }
        try:
            ui = self._load_settings_section("ui")
            saved = ui.get('proxy_settings', defaults)
            for k, v in defaults.items():
                saved.setdefault(k, v)
            return saved
        except Exception:
            return defaults

    def save_proxy_settings(self, proxy_settings: Dict[str, Any]):
        """Сохраняет настройки HTTP-прокси в единое хранилище настроек."""
        try:
            all_settings = self._load_unified_settings()
            all_settings.setdefault("ui", {})['proxy_settings'] = proxy_settings
            self._save_unified_settings(all_settings)
        except Exception as e:
            self.log(f"⚠ Could not save proxy settings: {str(e)}")

    def _get_proxy_url(self) -> Optional[str]:
        """Возвращает полностью сформированную строку URL прокси для requests/
                httpx или None, если прокси выключен или не настроен.
        
                Формат:  http://[user:pass@]host:port"""
        try:
            ps = self.load_proxy_settings()
            if not ps.get('enabled'):
                return None
            host = ps.get('host', '').strip()
            port = ps.get('port', 8080)
            if not host:
                return None
            username = ps.get('username', '').strip()
            password = ps.get('password', '').strip()
            if username:
                from urllib.parse import quote
                creds = f"{quote(username, safe='')}:{quote(password, safe='')}@"
            else:
                creds = ''
            return f"http://{creds}{host}:{port}"
        except Exception:
            return None

    def _get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Возвращает словарь прокси в стиле requests {"http": ...,
                "https": ...} или None. Используется вызовами MT-сервисов
                на библиотеке requests."""
        url = self._get_proxy_url()
        if not url:
            return None
        return {"http": url, "https": url}

    def load_provider_enabled_states(self) -> Dict[str, bool]:
        """Загружает состояния включённости провайдеров из предпочтений пользователя."""
        defaults = {
            'llm_openai': True,
            'llm_claude': True,
            'llm_gemini': True,
            'llm_mistral': True,
            'llm_openrouter': True,
            'llm_ollama': True,
            'llm_custom_openai': True,
            'mt_google_translate': True,
            'mt_deepl': True,
            'mt_microsoft': True,
            'mt_amazon': True,
            'mt_modernmt': True,
            'mt_mymemory': True
        }

        try:
            prefs = self._load_settings_section("ui")
            saved = prefs.get('provider_enabled_states', defaults)
            # Ensure new keys exist for older configs
            for k, v in defaults.items():
                saved.setdefault(k, v)
            return saved
        except:
            return defaults

    def save_provider_enabled_states(self, states: Dict[str, bool]):
        """Сохраняет состояния включённости провайдеров в предпочтения пользователя."""
        try:
            all_settings = self._load_unified_settings()
            all_settings.setdefault("ui", {})['provider_enabled_states'] = states
            self._save_unified_settings(all_settings)
        except Exception as e:
            self.log(f"⚠ Could not save provider enabled states: {str(e)}")

    def load_api_keys(self) -> Dict[str, str]:
        """Загружает API-ключи из единого файла настроек."""
        api_keys = self._load_settings_section("api_keys")

        # Migrate legacy 'google' key to canonical 'gemini' key
        if api_keys.get('google') and not api_keys.get('gemini'):
            api_keys['gemini'] = api_keys['google']

        return api_keys

    def save_api_keys(self, api_keys: Dict[str, str]):
        """Сохраняет API-ключи в единый файл настроек."""
        self._save_settings_section("api_keys", api_keys)
