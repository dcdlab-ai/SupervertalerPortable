# -*- coding: utf-8 -*-
"""Compile every .py under a repo root. Usage: python py_compile_all.py <repo_root>"""
import compileall, sys

ok = compileall.compile_dir(sys.argv[1], quiet=2, force=True)
print("COMPILE_OK" if ok else "COMPILE_FAIL")
sys.exit(0 if ok else 1)
