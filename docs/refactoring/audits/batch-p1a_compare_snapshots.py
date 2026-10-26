# -*- coding: utf-8 -*-
"""P1-A acceptance: compare pre vs post UI snapshots. Expected differences are
exactly the three removed UI surfaces; everything else must be identical."""
import json, pathlib, sys

iso_pre = pathlib.Path(sys.argv[1])
iso_post = pathlib.Path(sys.argv[2])
pre = json.loads((iso_pre / "snapshot_pre.json").read_text(encoding="utf-8"))
post = json.loads((iso_post / "snapshot_post.json").read_text(encoding="utf-8"))

def diff_list(name):
    a, b = pre[name], post[name]
    removed = [x for x in a if x not in b]
    added = [x for x in b if x not in a]
    return removed, added

print("tray_items removed:", diff_list("tray_items")[0], "added:", diff_list("tray_items")[1])
print("settings_groups removed:", diff_list("settings_groups")[0], "added:", diff_list("settings_groups")[1])
print("help_items removed:", diff_list("help_items")[0], "added:", diff_list("help_items")[1])
print("about removed buttons:", [x for x in pre["about"]["buttons"] if x not in post["about"]["buttons"]],
      "post buttons:", post["about"]["buttons"])
print("about labels identical:", pre["about"]["labels"] == post["about"]["labels"])
print("tray_available:", pre["tray_available"], post["tray_available"])
print("bytes_stable pre:", pre["bytes_stable"], "post:", post["bytes_stable"])
