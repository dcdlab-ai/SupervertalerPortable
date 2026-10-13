# -*- coding: utf-8 -*-
"""Гейт батча: QMessageBox -> локальный квалифицированный импорт (в translate_batch
ниже есть локальный `from PyQt6.QtWidgets import QMessageBox` (бюджет-блок),
который затеняет имя для ВСЕЙ функции — обращение до той строки даёт
UnboundLocalError)."""
import hashlib, pathlib

p = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py")
d = p.read_bytes()
NL = b"\r\n"
BS_N = b"\x5c\x6e"

old = (b"                # " + BS_N + BS_N + b"\r\n" is False and None)  # placeholder
old = (
    b"                if not self._custom_llm_ready(settings):\r\n"
    b"                    QMessageBox.warning(\r\n"
    b"                        self, \"Custom LLM profile is not configured\",\r\n"
    b"                        \"Custom LLM profile is not configured \xe2\x80\x94 Settings \xe2\x86\x92 AI Settings." + BS_N + BS_N + b"\"\r\n"
    b"                        \"Add a Custom (OpenAI-compatible) profile with an endpoint and a model.\")\r\n"
    b"                    return\r\n")
new = (
    b"                if not self._custom_llm_ready(settings):\r\n"
    b"                    # \xd0\xbb\xd0\xbe\xd0\xba\xd0\xb0\xd0\xbb\xd1\x8c\xd0\xbd\xd1\x8b\xd0\xb9 \xd0\xb8\xd0\xbc\xd0\xbf\xd0\xbe\xd1\x80\xd1\x82: \xd0\xb2 translate_batch \xd0\xbd\xd0\xb8\xd0\xb6\xd0\xb5 \xd0\xb1\xd1\x83\xd0\xb4\xd0\xb5\xd1\x82 \xd0\xbb\xd0\xbe\xd0\xba\xd0\xb0\xd0\xbb\xd1\x8c\xd0\xbd\xd1\x8b\xd0\xb9\r\n"
    b"                    # from PyQt6.QtWidgets import QMessageBox (\xd0\xb1\xd1\x8e\xd0\xb4\xd0\xb6\xd0\xb5\xd1\x82-\xd0\xb1\xd0\xbb\xd0\xbe\xd0\xba) \xe2\x80\x94 \xd0\xbe\xd0\xbd \xd0\xb7\xd0\xb0\xd1\x82\xd0\xb5\xd0\xbd\xd1\x8f\xd0\xb5\xd1\x82\r\n"
    b"                    # \xd0\xb8\xd0\xbc\xd1\x8f \xd0\xb4\xd0\xbb\xd1\x8f \xd0\xb2\xd1\x81\xd0\xb5\xd0\xb9 \xd1\x84\xd1\x83\xd0\xbd\xd0\xba\xd1\x86\xd0\xb8\xd0\xb8\r\n"
    b"                    from PyQt6.QtWidgets import QMessageBox as _QMessageBox\r\n"
    b"                    _QMessageBox.warning(\r\n"
    b"                        self, \"Custom LLM profile is not configured\",\r\n"
    b"                        \"Custom LLM profile is not configured \xe2\x80\x94 Settings \xe2\x86\x92 AI Settings." + BS_N + BS_N + b"\"\r\n"
    b"                        \"Add a Custom (OpenAI-compatible) profile with an endpoint and a model.\")\r\n"
    b"                    return\r\n")
assert d.count(old) == 1, d.count(old)
d = d.replace(old, new, 1)
assert d.count(b"\r\r\n") == 0 and d.count(b"\r\n") == d.count(b"\n")
p.write_bytes(d)
print("batch gate QMessageBox fixed, sha", hashlib.sha256(d).hexdigest()[:16])
