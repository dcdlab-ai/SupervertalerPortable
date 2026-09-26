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
