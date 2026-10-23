import sys, os, json
sys.path.insert(0, r"E:\Dev\SupervertalerPortable")
from modules.bilingual_markdown_handler import is_image_links_only
CASES = [
    ("lead_space_period", " ![Image](x)."),
    ("clean_period", "![Image](x)."),
    ("clean", "![Image](x)"),
    ("link_space_period", "![Image](x) ."),
    ("link_bang", "![Image](x)!"),
    ("link_nbsp_period", "![Image](x)\u00a0."),
    ("two_links_period", "![A](x)![B](y)."),
    ("link_words", "![Image](x) Figure 1 shows"),
    ("words_link", "Text ![Image](x)"),
    ("empty_alt", "![](x)"),
    ("plain_md_link", "[t](u)"),
    ("empty", ""),
    ("dot_only", "."),
    ("words_period", "Figure 2."),
]
out = {name: is_image_links_only(txt) for name, txt in CASES}
EXPECT = {"lead_space_period": True, "clean_period": True, "clean": True,
          "link_space_period": True, "link_bang": True, "link_nbsp_period": True,
          "two_links_period": True, "link_words": False, "words_link": False,
          "empty_alt": True, "plain_md_link": False, "empty": False,
          "dot_only": False, "words_period": False}
verdict = "PASS" if out == EXPECT else "FAIL"
extra = {"zwsp_link_period": is_image_links_only("![Image](x)\u200b."),
         "underscore_link": is_image_links_only("![Image](x)_"),
         "digit_link": is_image_links_only("![Image](x)1"),
         "cyrillic_link": is_image_links_only("![Image](x)рисунок"),
         "multiline_links": is_image_links_only("![a](p1)\n![b](p2)."),
         "fullwidth_digit": is_image_links_only("![Image](x)１")}
print(json.dumps({"matrix": out, "expect": EXPECT, "verdict": verdict, "extra": extra}, ensure_ascii=False, indent=1))
with open(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-m1\m1e-run-001\m1e_detector_matrix.json", "w", encoding="utf-8") as f:
    json.dump({"matrix": out, "expect": EXPECT, "verdict": verdict, "extra": extra}, f, ensure_ascii=False, indent=1)
