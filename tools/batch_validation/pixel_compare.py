# -*- coding: utf-8 -*-
"""Offscreen pixel comparison of PyQt6 widgets (Batch #3c gate practice).

Import from a per-batch driver script, e.g.:

    sys.path.insert(0, r"E:\\Dev\\SupervertalerPortable\\tools\\batch_validation")
    from pixel_compare import render, images_identical

    img1 = render(widget_a, "evidence/name_a.png")
    img2 = render(widget_b, "evidence/name_b.png")
    ok, why = images_identical(img1, img2)

The offscreen platform is forced at import time; a QApplication must be created
by the caller BEFORE instantiating widgets. Use for "identical except color"
proofs: compare monolith widget vs parameterized replacement across scenarios
(unchecked / checked / checked+resize / disabled+checked). A FAIL may be a
harness bug (e.g. stylesheet not applied to the counterpart) — verify the
harness before diagnosing a regression.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def render(widget, out_png=None):
    """Grab the widget to a QImage; optionally save PNG evidence. Returns QImage."""
    img = widget.grab().toImage()
    if out_png:
        os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
        img.save(out_png)
    return img


def images_identical(a, b):
    """Pixel-by-pixel comparison. Returns (identical, reason)."""
    if a.size() != b.size():
        return False, f"size {a.width()}x{a.height()} vs {b.width()}x{b.height()}"
    for y in range(a.height()):
        for x in range(a.width()):
            if a.pixel(x, y) != b.pixel(x, y):
                return False, f"first pixel diff at {x},{y}"
    return True, "pixel-identical"
