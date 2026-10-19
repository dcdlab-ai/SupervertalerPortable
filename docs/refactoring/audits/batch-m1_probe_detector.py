# -*- coding: utf-8 -*-
"""M1a probe: detector matrix for is_image_links_only (modules/bilingual_markdown_handler.py).

Every case is an exact string from the batch prompt (task item 1 + probe list).
PASS criterion: all matrix rows match expected. JSON verdict file is the evidence.
"""
import json, os, sys

sys.path.insert(0, r"E:\Dev\SupervertalerPortable")
from modules.bilingual_markdown_handler import is_image_links_only

CASES = [
    # (label, text, expected)
    ("plain text", "The army marched north.", False),
    ("link only", "![Image](/path/file.png)", True),
    ("link only, windows path", r"![Image](D:\Temp\x.png)", True),
    ("two links in a row", "![Image](a.png) ![Image](b.png)", True),
    ("two links separated by line break", "![Image](a.png)\n![Image](b.png)", True),
    ("alt keyword", "![Figure 1](x.png)", True),
    ("cyrillic alt + cyrillic path with spaces",
     "![Рисунок 1](D:\\Мои файлы\\рисунок 1.png)", True),
    ("empty alt", "![](x.png)", True),
    ("link + text after", "![Image](x.png) Figure 1 shows", False),
    ("link + trailing period", "![Image](x.png).", False),
    ("plain md link (no !)", "[t](u)", False),
    ("plain md link + text", "see [the chart](u)", False),
    ("text before links", "Figure: ![Image](x.png)", False),
    ("text after links (newline)", "![Image](x.png)\nSome text", False),
    ("link then plain link", "![Image](x.png) [t](u)", False),
    ("empty segment", "", False),
    ("whitespace only", "   \n\t ", False),
    ("link with trailing spaces", "![Image](x.png)   \n", True),
    ("link with title in parens", '![Image](x.png "Fig. 1")', True),
    ("link url with parentheses inside", "![Image](im(1).png)", False),
    ("image ext jpg + spaces in url", "![Figure 12A](figures/troops detail 1.jpg)", True),
    ("html img tag (not md)", "<img src='x.png'>", False),
    ("bbcode img (not md)", "[img]x.png[/img]", False),
]

results = []
fail = 0
for label, text, expected in CASES:
    got = is_image_links_only(text)
    ok = got == expected
    if not ok:
        fail += 1
    results.append({"label": label, "text": text, "expected": expected, "got": got, "ok": ok})

verdict = {"probe": "M1a detector matrix", "n_cases": len(CASES),
           "n_fail": fail, "verdict": "PASS" if fail == 0 else "FAIL",
           "cases": results}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_m1a_detector_verdict.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(verdict, f, ensure_ascii=False, indent=1)
print(json.dumps({"n_cases": len(CASES), "n_fail": fail, "verdict": verdict["verdict"]}))
for r in results:
    print(("PASS" if r["ok"] else "FAIL"), "|", r["label"], "| expected", r["expected"], "got", r["got"])
