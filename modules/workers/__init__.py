# modules.workers — QThread-воркеры, извлечённые из Supervertaler.py (Batch #4, Step 4 EXTRACTION_PLAN.md). Каждый файл — ровно один класс, перенесённый вербатим.

from .tm_search import TMSearchWorker
from .proofread import ProofreadWorker
from .glossary import GlossaryExtractionWorker

__all__ = ["TMSearchWorker", "ProofreadWorker", "GlossaryExtractionWorker"]
