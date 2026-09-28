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
(``spellcheck_manager``, ``theme_manager`` и др.), — поэтому смена каталога
данных не оставляет делегатов на устаревшем пути (``user_data_path``
переприсваивается в трёх местах монолита, все три ведут в этот метод).
С ``recent_projects_file`` дело теперь обстоит иначе: с S2.5 его читает не
только окно — путь к ``recent_projects.json`` передаётся в
``load_recent_projects`` / ``save_recent_projects`` этого сервиса
АРГУМЕНТОМ при каждом вызове (сервис его нигде не хранит), поэтому и здесь
устаревших путей после смены каталога данных не остаётся.

СЕМАНТИКА, КОТОРУЮ НЕЛЬЗЯ МЕНЯТЬ (Batch #7 Stage 1, §1.9): ни один метод не
кэширует прочитанный JSON между вызовами — файл открывается заново на КАЖДЫЙ
вызов. Никаких ``lru_cache``/«прочитал один раз в __init__ сервиса»/поля-кэша.

SupervertalerQt сохраняет 6 тонких одноимённых делегатов (``_get_settings_dir``,
``_get_unified_settings_path``, ``_load_unified_settings``,
``_save_unified_settings``, ``_load_settings_section``,
``_save_settings_section``), поэтому все call sites продолжают работать без
изменений — включая строковые (getattr) обращения из ``modules/``
(``voice_tab.py``, ``clipboard_manager_widget.py``) и безусловный вызов
``window._load_settings_section("ui")`` из ``main()`` монолита. Оставшиеся
в монолите методы (``_migrate_settings_to_unified``,
``_migrate_to_workbench_layout``, ``_migrate_voice_dictation_default_off`` —
по решению координатора в S2.5 не переносятся, см. итог Step 7 в
``EXTRACTION_PLAN.md``) ходят через эти делегаты.

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

Под-батч S2.4 (тот же Stage 2) добавил языковую пару и спеллчек-IO:
``_load_language_pair_from_disk`` (в сервисе читает файл и возвращает пару
источник/перевод, запись атрибутов окна делает одноимённый делегат),
``save_language_settings`` (ВЕРБАТИМ), ``_save_spellcheck_settings`` (в
сервисе принимает ``enabled`` аргументом, делегат передаёт
``self.spellcheck_enabled``; тело иначе ВЕРБАТИМ) и
``_load_spellcheck_settings`` (ВЕРБАТИМ).

Под-батч S2.5 (последний в Stage 2) добавил недавние проекты:
``load_recent_projects`` и ``save_recent_projects`` (тела ВЕРБАТИМ). Это
единственные методы сервиса, которые НЕ ходят через ``settings.json``: они
работают с отдельным файлом ``recent_projects.json``, поэтому путь к нему (и
``user_data_path`` для ``mkdir``) приходит аргументом от делегата окна при
каждом вызове, а сервис его не хранит и не кэширует.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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

    # ------------------------------------------------------------------
    # Языковая пара + спеллчек (Batch #7 Stage 2, под-батч S2.4)
    # ------------------------------------------------------------------
    # Из четырёх перенесённых тел два ушли ВЕРБАТИМ (save_language_settings,
    # _load_spellcheck_settings), два потребовали SPLIT по состоянию окна:
    #   * _load_language_pair_from_disk больше НЕ пишет
    #     self.source_language / self.target_language — метод возвращает пару
    #     (src, tgt), а на исключении None; запись атрибутов делает делегат
    #     окна и только при не-None результате (иначе атрибуты остаются
    #     нетронутыми, как и в исходном теле);
    #   * _save_spellcheck_settings больше НЕ читает self.spellcheck_enabled —
    #     значение приходит аргументом enabled, делегат окна передаёт туда
    #     свой self.spellcheck_enabled.
    # Внутренние вызовы self._load_settings_section, self._load_unified_settings,
    # self._save_unified_settings и self.log резолвятся в методы ЭТОГО класса
    # (в монолите те же выражения шли через его одноимённые делегаты), поэтому
    # наблюдаемое поведение то же — включая отсутствие кэша (файл открывается
    # заново на каждый вызов, см. докстринг модуля).
    # Асимметрия API сохранена КАК ЕСТЬ (не унифицируется по инициативе
    # переноса): save_language_settings и _save_spellcheck_settings пишут через
    # whole-file API (_load_unified_settings / _save_unified_settings), а
    # _load_language_pair_from_disk и _load_spellcheck_settings читают через
    # секционный _load_settings_section("ui").

    def _load_language_pair_from_disk(self) -> Optional[Tuple[str, str]]:
        """Читает только языковую пару источник/перевод из settings.json.
        
                Должно выполняться ДО построения UI вкладки Language Pair, иначе
                комбобоксы заполняются устаревшими жёстко заданными дефолтами
                (English / Dutch). Вызывается рано в __init__, где spellcheck
                и log могут ещё не существовать, поэтому здесь их не трогаем."""
        defaults = ('English', 'Dutch')
        try:
            prefs = self._load_settings_section("ui")
            lang_settings = prefs.get('language_settings', {}) or {}
            src = lang_settings.get('source_language') or defaults[0]
            tgt = lang_settings.get('target_language') or defaults[1]
            print(f"[LangSettings] Loaded from settings.json: {src} → {tgt}")
            return src, tgt
        except Exception as e:
            print(f"[LangSettings] Load failed, keeping defaults: {e!r}")
            return None

    def save_language_settings(self, source_lang: str, target_lang: str):
        """Сохраняет языковые настройки в предпочтения."""
        try:
            all_settings = self._load_unified_settings()
            all_settings.setdefault("ui", {})['language_settings'] = {
                'source_language': source_lang,
                'target_language': target_lang
            }
            self._save_unified_settings(all_settings)
        except Exception as e:
            self.log(f"⚠ Could not save language settings: {str(e)}")

    def _save_spellcheck_settings(self, enabled: bool):
        """Сохраняет настройки проверки орфографии в предпочтения."""
        try:
            all_settings = self._load_unified_settings()
            all_settings.setdefault("ui", {})['spellcheck_settings'] = {
                'enabled': enabled
            }
            self._save_unified_settings(all_settings)
        except Exception as e:
            self.log(f"⚠ Could not save spellcheck settings: {e}")

    def _load_spellcheck_settings(self):
        """Загружает настройки проверки орфографии из предпочтений."""
        try:
            prefs = self._load_settings_section("ui")
            settings = prefs.get('spellcheck_settings', {})
            return settings.get('enabled', False)
        except:
            return False

    # ------------------------------------------------------------------
    # Недавние проекты (Batch #7 Stage 2, под-батч S2.5)
    # ------------------------------------------------------------------
    # Два последних метода Stage 2; тела перенесены из SupervertalerQt
    # ВЕРБАТИМ. ОТЛИЧИЕ ОТ S2.1–S2.4: эти методы НЕ работают через
    # settings.json и не используют _load_settings_section /
    # _load_unified_settings — они открывают отдельный файл
    # recent_projects.json, поэтому пути передаются АРГУМЕНТАМИ (решение
    # координатора): делегат окна читает свой self.recent_projects_file при
    # КАЖДОМ вызове и передаёт его в load; в save добавляется
    # self.user_data_path (нужен для mkdir(parents=True, exist_ok=True)
    # перед записью). Сервис эти пути НЕ хранит — ни в конструкторе, ни в
    # полях, — поэтому кэша нет (см. докстринг модуля) и
    # переприсваивание self.recent_projects_file / self.user_data_path в
    # _reinitialize_with_new_data_path() сразу видно новым вызовам.
    # Единственная правка тел — замена self.recent_projects_file /
    # self.user_data_path на одноимённые параметры (3 и 2 места); строка
    # def в save разделена на две. Обработка исключений и все ветви
    # сохранены КАК ЕСТЬ: UnicodeDecodeError → повтор в latin-1 с
    # предупреждением self.log, старый dict-формат, новый list-формат с
    # фильтром os.path.exists + .svproj, отсутствующий файл → [], битый
    # JSON → [] с self.log.

    def load_recent_projects(self, recent_projects_file: Path) -> List[Dict[str, str]]:
        """Загружает недавние проекты из файла."""
        if not recent_projects_file.exists():
            return []
        
        try:
            # Try UTF-8 first, fall back to latin-1 if it fails
            try:
                with open(recent_projects_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except UnicodeDecodeError:
                self.log(f"⚠ UTF-8 decoding failed for recent projects, trying latin-1...")
                with open(recent_projects_file, 'r', encoding='latin-1') as f:
                    data = json.load(f)
            
            # Handle both old dict format and new list format
            if isinstance(data, dict):
                # Old format: convert to list
                recent = []
                for key, value in data.items():
                    if isinstance(value, list):
                        # Extract path and name from old list format
                        for item in value:
                            if isinstance(item, dict):
                                recent.append(item)
                            else:
                                # String path
                                recent.append({
                                    'path': str(item),
                                    'name': Path(str(item)).stem,
                                    'last_opened': datetime.now().isoformat()
                                })
                    elif isinstance(value, str):
                        recent.append({
                            'path': value,
                            'name': Path(value).stem,
                            'last_opened': datetime.now().isoformat()
                        })
                return recent
            elif isinstance(data, list):
                # New format: already a list
                # Ensure all entries have required fields
                normalized = []
                for item in data:
                    if isinstance(item, dict) and 'path' in item:
                        # Ensure all required fields exist
                        if 'name' not in item:
                            item['name'] = Path(item['path']).stem
                        if 'last_opened' not in item:
                            item['last_opened'] = datetime.now().isoformat()
                        # Only include if the file still exists AND is an actual
                        # project file – this auto-purges any stray non-.svproj
                        # entries (e.g. source documents) left by older builds.
                        if (os.path.exists(item['path'])
                                and str(item['path']).lower().endswith('.svproj')):
                            normalized.append(item)
                return normalized
            
            return []
        
        except Exception as e:
            self.log(f"Error loading recent projects: {e}")
            return []

    def save_recent_projects(self, recent_projects: List[Dict[str, str]],
                             recent_projects_file: Path, user_data_path: Path):
        """Сохраняет недавние проекты в файл."""
        try:
            # Ensure directory exists
            user_data_path.mkdir(parents=True, exist_ok=True)
            
            with open(recent_projects_file, 'w', encoding='utf-8') as f:
                json.dump(recent_projects, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            self.log(f"Error saving recent projects: {e}")
