# ============================================================================
# modules/models.py — модели данных проекта Supervertaler.
#
# Содержимое перенесено ВЕРБАТИМ из монолита Supervertaler.py (Batch #1,
# Step 1 of EXTRACTION_PLAN.md): strip_invisible_markers (Supervertaler.py:1735,
# обнаруженная pre-flight зависимость Segment.from_dict), Comment (1774),
# Segment (1937), Project (2123). Тела не изменялись.
# ============================================================================

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from modules.statuses import DEFAULT_STATUS


def strip_invisible_markers(text: str) -> str:
    """Удаляет все отображаемые маркеры «показать невидимые» из строки.

    Эти маркеры вставляются apply_invisible_replacements() только для
    показа на экране и никогда не должны попадать в segment.target или на диск.

    Обрабатывает:
      · + U+200B  -> обычный пробел        (маркер пробела)
      ·           -> обычный пробел        (запасной вариант, одиночная точка)
      → + U+200B  -> табуляция             (маркер табуляции)
      →           -> табуляция             (запасной вариант, одиночная стрелка)
      ↵ + \\n     -> \\n                    (маркер разрыва строки перед переводом строки)
      ↵           -> (удаляется)           (одиночный маркер разрыва строки)
      U+200B      -> (удаляется)           (случайный zero-width space)

    ПРИМЕЧАНИЕ: знак градуса ° намеренно НЕ разворачивается, потому что ° —
    легитимный символ Unicode, встречающийся в обычном тексте перевода.
    Замена NBSP обрабатывается отдельно методом главного окна, у которого
    есть контекст проекта.
    """
    if not text:
        return text
    result = text
    result = result.replace('\u00B7\u200B', ' ')   # middle-dot + ZWSP → space
    result = result.replace('\u00B7', ' ')          # lone middle-dot → space
    result = result.replace('\u2192\u200B', '\t')   # arrow + ZWSP → tab
    result = result.replace('\u2192', '\t')          # lone arrow → tab
    result = result.replace('\u21B5\n', '\n')        # ↵ + newline → newline (current marker)
    result = result.replace('\u21B5', '')            # bare ↵ → nothing
    result = result.replace('\u00B6\n', '\n')        # pilcrow + newline → newline (legacy, keep for old files)
    result = result.replace('\u00B6', '')            # bare pilcrow → nothing (legacy)
    result = result.replace('\u200B', '')            # stray ZWSP → nothing
    return result


@dataclass
class Comment:
    """Пользовательский комментарий, привязанный к сегменту.

    Введён в v1.10.57 при переходе от однострочных примечаний к сегменту
    (``segment.notes``) к списку структурированных комментариев
    (``segment.comments``). Структурированная форма поддерживает:

    * Несколько комментариев на сегмент.
    * Собственных автора и метку времени у каждого комментария.
    * Необязательную привязку (anchor) к диапазону символов внутри
      source/target сегмента. Когда ``anchor_field`` равен ``"source"``
      или ``"target"`` и ``anchor_end > anchor_start``, комментарий
      привязан к этому диапазону символов (семантика срезов Python:
      начало включительно, конец исключительно). Экспорт в DOCX
      использует это, чтобы получить комментарии Word, выделяющие
      только указанный текст — как в Trados и memoQ. Если
      ``anchor_field`` пуст, комментарий относится ко всему сегменту
      (при экспорте привязывается к целому абзацу).

    Обратная совместимость: старые файлы ``.svproj`` хранят примечания
    одной строкой в ``segment.notes``; ``Segment.from_dict`` переносит
    их в один сегментный Comment с прежним текстом.
    """
    id: str = ""             # UUID hex; назначается в __post_init__, если пусто
    text: str = ""           # Текст комментария
    author: str = ""         # Автор (имя переводчика, "AI" и т.п.)
    created: str = ""        # Метка времени ISO; ставится в __post_init__, если пусто
    anchor_field: str = ""   # "source", "target" или "" (уровень сегмента)
    anchor_start: int = 0    # Смещение символа (включительно)
    anchor_end: int = 0      # Смещение символа (не включительно)
    imported: bool = False   # True = прочитан из исходного документа (например,
                             # комментарий Word при рецензировании). Показывается
                             # для контекста, но НЕ реэкспортируется: оригинал
                             # остаётся в исходном файле (круговая передача Okapi
                             # сохраняет его).

    def __post_init__(self):
        if not self.id:
            import uuid as _uuid
            self.id = _uuid.uuid4().hex
        if not self.created:
            self.created = datetime.now().isoformat()

    @property
    def is_anchored(self) -> bool:
        """True, если комментарий привязан к конкретному диапазону текста."""
        return bool(self.anchor_field) and self.anchor_end > self.anchor_start

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Comment':
        """Строит Comment из словаря, отбрасывая неизвестные ключи."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class Segment:
    """Сегмент перевода (формат совпадает с tkinter-версией)."""
    id: int
    source: str
    target: str = ""
    status: str = DEFAULT_STATUS.key
    type: str = "para"  # para, heading, list_item, table_cell
    notes: str = ""  # УСТАРЕЛО: прежнее однострочное примечание. Новый код должен
                     # использовать comments[]. Оставлено для совместимости с
                     # .svproj (и для ещё не мигрированных участков кода).
                     # Синхронизируется с comments[] через _sync_notes_from_comments()
                     # и методы-помощники ниже.
    comments: List['Comment'] = field(default_factory=list)  # v1.10.57: структурированные комментарии
    proofreading_notes: Dict[str, str] = field(default_factory=dict)  # имя LLM-модели -> текст замечания вычитки
    match_percent: Optional[int] = None  # процент совпадения memoQ, если известен
    memoQ_status: str = ""  # «сырой» текст статуса memoQ
    locked: bool = False  # Для совместимости с tkinter-версией
    paragraph_id: int = 0  # Группировка сегментов по абзацу для потока документа
    style: str = "Normal"  # Heading 1, Heading 2, Title, Subtitle, Normal и т.д.
    document_position: int = 0  # Позиция в исходном документе
    is_table_cell: bool = False  # Находится ли сегмент в таблице
    table_info: Optional[tuple] = None  # (индекс_таблицы, строка, ячейка), если is_table_cell
    modified: bool = False  # Признак того, что сегмент редактировался
    created_at: str = ""  # Метка времени создания
    modified_at: str = ""  # Метка времени последнего изменения
    list_number: Optional[int] = None  # Для нумерованных списков: 1, 2, 3 и т.д.; None для маркеров и вне списков
    list_type: str = ""  # "numbered", "bullet" или "" для элементов вне списков
    file_id: Optional[int] = None  # ID файла, которому принадлежит сегмент (для многофайловых проектов)
    file_name: str = ""  # Имя файла, которому принадлежит сегмент (для многофайловых проектов)
    dejavu_segment_id: str = ""  # ID сегмента Déjà Vu для экспорта с круговой передачей
    dejavu_row_index: Optional[int] = None  # индекс строки Déjà Vu для сопоставления при экспорте
    sdl_segment_id: str = ""  # ID сегмента SDLXLIFF для экспорта с круговой передачей
    okapi_tu_id: str = ""  # ID текстовой единицы Okapi для обратного слияния
    okapi_segment_index: int = -1  # индекс сегмента внутри единицы Okapi (-1 = не из Okapi)
    category: str = ""  # категория под-документа Okapi: "" (основной текст) / "comment" / "header" / "footer" / "property" / "notes"

    def __post_init__(self):
        """Инициализирует метки времени и согласует comments[] ↔ notes."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = datetime.now().isoformat()
        # v1.10.57: приводим comments[] и notes к согласованному состоянию.
        # - Есть notes, но нет comments -> миграция: создаём один
        #   сегментный Comment из строки notes.
        # - Есть comments, но нет notes -> выводим notes для любых старых
        #   участков кода, всё ещё читающих segment.notes напрямую.
        # - Есть оба -> доверяем comments[] (новый источник истины);
        #   перегенерируем notes из него, чтобы данные совпадали.
        if self.notes and not self.comments:
            self.comments = [Comment(
                text=self.notes,
                author='',  # автор неизвестен для мигрированных старых примечаний
                created=self.modified_at,
                anchor_field='',
                anchor_start=0,
                anchor_end=0,
            )]
        elif self.comments:
            self.notes = self._joined_comment_text()

    # ── Помощники комментариев (v1.10.57) ──
    def _joined_comment_text(self) -> str:
        """Объединённый текст всех комментариев (поддерживает синхронизацию
        устаревшего segment.notes с новым списком comments[])."""
        return '\n\n'.join(c.text for c in self.comments if c.text)

    def add_comment(self, text: str, author: str = '',
                    anchor_field: str = '', anchor_start: int = 0,
                    anchor_end: int = 0) -> 'Comment':
        """Добавляет новый Comment, синхронизирует устаревшие notes, возвращает Comment.

        Используйте этот метод вместо прямой мутации ``segment.comments``,
        чтобы «зеркало» ``segment.notes`` оставалось согласованным для всех
        участков кода, которые его всё ещё читают (двуязычный экспорт memoQ,
        подсказки в столбце статуса сетки, виджет списка всех комментариев и т.д.).
        """
        comment = Comment(
            text=text,
            author=author,
            anchor_field=anchor_field,
            anchor_start=anchor_start,
            anchor_end=anchor_end,
        )
        self.comments.append(comment)
        self.notes = self._joined_comment_text()
        return comment

    def update_comment(self, comment_id: str, text: str) -> bool:
        """Обновляет текст существующего комментария. Возвращает True, если найден."""
        for c in self.comments:
            if c.id == comment_id:
                c.text = text
                self.notes = self._joined_comment_text()
                return True
        return False

    def remove_comment(self, comment_id: str) -> bool:
        """Удаляет комментарий по id. Возвращает True, если найден."""
        before = len(self.comments)
        self.comments = [c for c in self.comments if c.id != comment_id]
        if len(self.comments) < before:
            self.notes = self._joined_comment_text()
            return True
        return False

    def get_comment(self, comment_id: str) -> Optional['Comment']:
        for c in self.comments:
            if c.id == comment_id:
                return c
        return None

    def replace_all_comments_with_text(self, text: str, author: str = '') -> None:
        """Мост для старого кода: заменяет весь список комментариев одним
        сегментным Comment с текстом ``text``. Пустой текст оставляет список
        пустым. Используется прежним однострочным редактором
        (``_on_bottom_notes_changed``), который пишет в segment.notes как
        в одну строку."""
        if text and text.strip():
            # По возможности сохраняем автора/якорь прежнего одиночного
            # комментария — пустая правка не должна перетасовывать метаданные.
            if (len(self.comments) == 1
                    and not self.comments[0].is_anchored):
                self.comments[0].text = text
            else:
                self.comments = [Comment(
                    text=text,
                    author=author,
                    anchor_field='',
                    anchor_start=0,
                    anchor_end=0,
                )]
        else:
            self.comments = []
        self.notes = self._joined_comment_text()

    def to_dict(self) -> Dict[str, Any]:
        """Словарь для JSON-сериализации"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Segment':
        """Строит Segment из словаря, игнорируя неизвестные поля."""
        # Используем только поля, известные дата-классу
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        # Защитно снимаем маркеры «показать невидимые», которые могли попасть
        # на диск из более ранней ошибочной версии приложения.
        if 'target' in filtered_data and isinstance(filtered_data['target'], str):
            filtered_data['target'] = strip_invisible_markers(filtered_data['target'])
        if 'source' in filtered_data and isinstance(filtered_data['source'], str):
            filtered_data['source'] = strip_invisible_markers(filtered_data['source'])
        # Миграция: переносим прежний текст "⚠️ PROOFREAD:" из notes в словарь proofreading_notes
        notes_val = filtered_data.get('notes', '')
        if notes_val and "⚠️ PROOFREAD:" in notes_val and not filtered_data.get('proofreading_notes'):
            parts = notes_val.split("⚠️ PROOFREAD:", 1)
            before = parts[0].strip()
            proofread_and_rest = parts[1] if len(parts) > 1 else ""
            separator_parts = proofread_and_rest.split("---", 1)
            proofread_text = separator_parts[0].strip()
            after = separator_parts[1].strip() if len(separator_parts) > 1 else ""
            # Восстанавливаем «чистые» notes (только пользовательские примечания)
            clean_notes = before
            if after:
                clean_notes = (clean_notes + "\n" + after).strip() if clean_notes else after
            filtered_data['notes'] = clean_notes
            # Текст вычитки храним под ключом "legacy" (оригинальная LLM неизвестна)
            if proofread_text:
                filtered_data['proofreading_notes'] = {"legacy": proofread_text}
        # v1.10.57: при загрузке превращаем вложенные словари Comment в объекты
        # Comment. asdict() при сохранении даёт простые словари; это обратная
        # операция при загрузке.
        raw_comments = filtered_data.get('comments')
        if raw_comments:
            filtered_data['comments'] = [
                Comment.from_dict(c) if isinstance(c, dict) else c
                for c in raw_comments
            ]
        return cls(**filtered_data)


@dataclass
class Project:
    """Проект перевода: сегменты, файлы, представления и снимки настроек.

    Подсловари *_settings заполняются в save_project_to_file снимками
    живого состояния менеджеров (активные TM/терминостраницы, промпты и т.д.),
    поэтому файл проекта — самодостаточный снимок рабочего окружения.
    """
    name: str
    source_lang: str = "en"
    target_lang: str = "nl"
    segments: List[Segment] = None
    created: str = ""
    modified: str = ""
    prompt_settings: Dict[str, Any] = None  # Настройки активных промптов
    tm_settings: Dict[str, Any] = None  # Настройки активированных TM
    termbase_settings: Dict[str, Any] = None  # Настройки активированных терминостраниц
    nt_settings: Dict[str, Any] = None  # Настройки активированных непереводимых элементов
    spellcheck_settings: Dict[str, Any] = None  # Настройки орфографии {enabled, language}
    ui_settings: Dict[str, Any] = None  # Настройки UI (масштаб панели результатов и т.д.)
    general_settings_overrides: Dict[str, Any] = None  # Перекрытия общих настроек для проекта
    id: int = None  # Уникальный ID проекта для отслеживания активации TM
    original_docx_path: str = None  # Путь к исходному DOCX для экспорта с сохранением структуры
    trados_source_path: str = None  # Путь к исходному двуязычному DOCX Trados для обратного экспорта
    memoq_source_path: str = None  # Путь к исходному двуязычному DOCX memoQ для обратного экспорта
    mqxliff_source_path: str = None  # Путь к исходному memoQ XLIFF для обратного экспорта
    cafetran_source_path: str = None  # Путь к исходному двуязычному DOCX CafeTran для обратного экспорта
    sdlppx_source_path: str = None  # Путь к исходному пакету Trados SDLPPX для экспорта SDLRPX
    sdlxliff_source_paths: list = None  # Пути к отдельным .sdlxliff для обратного экспорта
    original_txt_path: str = None  # Путь к исходному простому текстовому файлу для обратного экспорта
    dejavu_source_path: str = None  # Путь к исходному двуязычному RTF Déjà Vu для обратного экспорта
    po_source_path: str = None  # Путь к исходному GNU gettext .po / .pot для обратного экспорта
    concordance_geometry: Dict[str, int] = None  # Геометрия окна Concordance Search {x, y, width, height}
    # Поддержка многофайловых проектов
    files: List[Dict[str, Any]] = None  # Файлы проекта: [{id, name, path, type, segment_count, ...}]
    is_multifile: bool = False  # True, если это многофайловый проект
    views: List[Dict[str, Any]] = None  # Сохранённые представления: [{"name": "...", "file_ids": [1, 3]}]
    # Блокнот для личных заметок переводчика (хранится только в .svproj,
    # никогда не экспортируется в CAT-инструменты)
    scratchpad_notes: str = ""
    import_engine: str = ""  # "okapi" или "" (стандартный/встроенный)
    import_options: Optional[Dict[str, Any]] = None  # переключатели импорта Okapi по типам файлов; переиспользуются при экспорте/слиянии

    def __post_init__(self):
        if self.segments is None:
            self.segments = []
        if self.files is None:
            self.files = []
        if self.views is None:
            self.views = []
        if not self.created:
            self.created = datetime.now().isoformat()
        if not self.modified:
            self.modified = datetime.now().isoformat()
        if self.prompt_settings is None:
            self.prompt_settings = {}
        if self.tm_settings is None:
            self.tm_settings = {}
        if self.termbase_settings is None:
            self.termbase_settings = {}
        if self.nt_settings is None:
            self.nt_settings = {}
        if self.spellcheck_settings is None:
            self.spellcheck_settings = {}
        if self.ui_settings is None:
            self.ui_settings = {}
        if self.general_settings_overrides is None:
            self.general_settings_overrides = {}
        # Генерируем ID, если не задан (для совместимости со старыми проектами)
        if self.id is None:
            import hashlib
            # Стабильный ID из имени проекта + метки времени создания:
            # одинаков у всех, кто открывает один и тот же проект.
            id_source = f"{self.name}_{self.created}"
            self.id = int(hashlib.md5(id_source.encode()).hexdigest()[:8], 16)

    def to_dict(self) -> Dict[str, Any]:
        """Словарь для JSON-сериализации.

        Структура организована для удобного чтения в текстовом редакторе:
        1. Идентификация проекта (имя, языки, даты, id)
        2. Настройки (промпты, TM, терминостраницы, орфография и т.д.)
        3. Пути к исходным файлам
        4. Состояние UI (геометрия конкорданса)
        5. Сегменты (в конце — сам переводимый контент)
        """
        # Начинаем с основных метаданных проекта
        result = {
            'name': self.name,
            'source_lang': self.source_lang,
            'target_lang': self.target_lang,
            'created': self.created,
            'modified': self.modified,
            'id': self.id  # Сохраняем ID проекта
        }

        # Добавляем настройки (промпты, TM, терминостраницы и т.д.)
        if hasattr(self, 'prompt_settings'):
            result['prompt_settings'] = self.prompt_settings
        if self.tm_settings:
            result['tm_settings'] = self.tm_settings
        if self.termbase_settings:
            result['termbase_settings'] = self.termbase_settings
        if self.nt_settings:
            result['nt_settings'] = self.nt_settings
        if self.spellcheck_settings:
            result['spellcheck_settings'] = self.spellcheck_settings
        if self.ui_settings:
            result['ui_settings'] = self.ui_settings

        # Добавляем пути к исходным файлам
        if self.original_docx_path:
            result['original_docx_path'] = self.original_docx_path
        if self.trados_source_path:
            result['trados_source_path'] = self.trados_source_path
        if self.memoq_source_path:
            result['memoq_source_path'] = self.memoq_source_path
        if self.mqxliff_source_path:
            result['mqxliff_source_path'] = self.mqxliff_source_path
        if self.cafetran_source_path:
            result['cafetran_source_path'] = self.cafetran_source_path
        if self.sdlppx_source_path:
            result['sdlppx_source_path'] = self.sdlppx_source_path
        if self.sdlxliff_source_paths:
            result['sdlxliff_source_paths'] = self.sdlxliff_source_paths
        if self.original_txt_path:
            result['original_txt_path'] = self.original_txt_path
        if self.dejavu_source_path:
            result['dejavu_source_path'] = self.dejavu_source_path
        if self.po_source_path:
            result['po_source_path'] = self.po_source_path

        # Добавляем состояние UI
        if self.concordance_geometry:
            result['concordance_geometry'] = self.concordance_geometry

        # Добавляем данные многофайлового проекта
        if self.is_multifile:
            result['is_multifile'] = self.is_multifile
        if self.files:
            result['files'] = self.files

        # Добавляем заметки блокнота (личные заметки переводчика,
        # никогда не экспортируются в CAT-инструменты)
        if self.scratchpad_notes:
            result['scratchpad_notes'] = self.scratchpad_notes

        # Добавляем сохранённые представления для многофайловых проектов
        if self.views:
            result['views'] = self.views

        # Добавляем признак движка импорта (для обратного экспорта Okapi)
        if self.import_engine:
            result['import_engine'] = self.import_engine
        # Сохраняем параметры импорта, чтобы экспорт/слияние повторно
        # применил фильтр с ТЕМИ ЖЕ переключателями, с которыми документ
        # был извлечён.
        if self.import_options:
            result['import_options'] = self.import_options

        # Сегменты добавляем ПОСЛЕДНИМИ (чтобы они оказались в конце файла)
        result['segments'] = [seg.to_dict() for seg in self.segments]

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Строит Project из словаря."""
        segments = [Segment.from_dict(seg) for seg in data.get('segments', [])]

        # Обрабатываем отсутствующее поле name (используем имя файла или значение по умолчанию)
        name = data.get('name', 'Untitled Project')

        project = cls(
            name=name,
            source_lang=data.get('source_lang', 'en'),
            target_lang=data.get('target_lang', 'nl'),
            segments=segments,
            created=data.get('created', ''),
            modified=data.get('modified', ''),
            id=data.get('id', None)  # Загружаем ID проекта (при отсутствии сгенерируется)
        )
        # Сохраняем настройки промптов, если есть
        if 'prompt_settings' in data:
            project.prompt_settings = data['prompt_settings']
        # Сохраняем настройки TM, если есть
        if 'tm_settings' in data:
            project.tm_settings = data['tm_settings']
        # Сохраняем настройки терминостраниц, если есть
        if 'termbase_settings' in data:
            project.termbase_settings = data['termbase_settings']
        # Сохраняем настройки непереводимых элементов, если есть
        if 'nt_settings' in data:
            project.nt_settings = data['nt_settings']
        # Сохраняем настройки орфографии, если есть
        if 'spellcheck_settings' in data:
            project.spellcheck_settings = data['spellcheck_settings']
        # Сохраняем настройки UI, если есть
        if 'ui_settings' in data:
            project.ui_settings = data['ui_settings']
        # Сохраняем путь к исходному DOCX, если есть
        if 'original_docx_path' in data:
            project.original_docx_path = data['original_docx_path']
        # Сохраняем путь исходника Trados, если есть
        if 'trados_source_path' in data:
            project.trados_source_path = data['trados_source_path']
        # Сохраняем путь исходника memoQ, если есть
        if 'memoq_source_path' in data:
            project.memoq_source_path = data['memoq_source_path']
        # Сохраняем путь исходника memoQ XLIFF, если есть
        if 'mqxliff_source_path' in data:
            project.mqxliff_source_path = data['mqxliff_source_path']
        # Сохраняем путь исходника CafeTran, если есть
        if 'cafetran_source_path' in data:
            project.cafetran_source_path = data['cafetran_source_path']
        # Сохраняем путь исходника SDLPPX, если есть
        if 'sdlppx_source_path' in data:
            project.sdlppx_source_path = data['sdlppx_source_path']
        # Сохраняем пути к отдельным SDLXLIFF, если есть
        if 'sdlxliff_source_paths' in data:
            project.sdlxliff_source_paths = data['sdlxliff_source_paths']
        # Сохраняем путь к исходному TXT, если есть
        if 'original_txt_path' in data:
            project.original_txt_path = data['original_txt_path']
        # Сохраняем путь исходника Déjà Vu, если есть
        if 'dejavu_source_path' in data:
            project.dejavu_source_path = data['dejavu_source_path']
        # Сохраняем путь исходника .po / .pot, если есть
        if 'po_source_path' in data:
            project.po_source_path = data['po_source_path']
        # Сохраняем геометрию окна конкорданса, если есть
        if 'concordance_geometry' in data:
            project.concordance_geometry = data['concordance_geometry']
        # Сохраняем данные многофайлового проекта, если есть
        if 'is_multifile' in data:
            project.is_multifile = data['is_multifile']
        if 'files' in data:
            project.files = data['files']
        # Сохраняем заметки блокнота, если есть
        if 'scratchpad_notes' in data:
            project.scratchpad_notes = data['scratchpad_notes']
        # Сохраняем сохранённые представления, если есть
        if 'views' in data:
            project.views = data['views']
        # Сохраняем признак движка импорта (для обратного экспорта Okapi)
        if 'import_engine' in data:
            project.import_engine = data['import_engine']
        if 'import_options' in data:
            project.import_options = data['import_options']
        return project
