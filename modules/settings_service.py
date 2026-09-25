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
