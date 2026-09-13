# -*- coding: utf-8 -*-
"""Two-process project smoke test (Batch #3b/#3c practice).

save: instantiate SupervertalerQt offscreen, create a programmatic Project with
      N segments, save to <svproj>, print SAVE_OK <bytes>.
load: instantiate SupervertalerQt offscreen, load <svproj>, verify name and
      segment count, print LOAD_OK <name> <segments> <first source>.

NOTE: the save path writes into the shared production user-data directory
(versioned backups) regardless of cwd — see AGENTS.md user-data isolation.

Usage: python smoke_project.py save|load <svproj_path> [project_name] [segment_count]
"""
import faulthandler, os, sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
mode, svproj = sys.argv[1], sys.argv[2]
proj_name = sys.argv[3] if len(sys.argv) > 3 else "smoke"
n_segments = int(sys.argv[4]) if len(sys.argv) > 4 else 2
sys.path.insert(0, r"E:\Dev\SupervertalerPortable")
faulthandler.dump_traceback_later(90, repeat=True, file=sys.stderr)

from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)

from modules.models import Project, Segment
from Supervertaler import SupervertalerQt

w = SupervertalerQt()
faulthandler.cancel_dump_traceback_later()

if mode == "save":
    p = Project(name=proj_name, source_lang="en", target_lang="nl",
                segments=[Segment(id=i + 1, source=f"Segment {i + 1} source", target="")
                          for i in range(n_segments)])
    w.current_project = p
    w.project_file_path = svproj
    w.save_project_to_file(svproj)
    assert os.path.exists(svproj) and os.path.getsize(svproj) > 0
    print("SAVE_OK", os.path.getsize(svproj))
else:
    w.load_project(svproj)
    proj = w.current_project
    assert proj is not None, "project not loaded"
    assert proj.name == proj_name, proj.name
    assert len(proj.segments) == n_segments, len(proj.segments)
    print("LOAD_OK", proj.name, len(proj.segments), proj.segments[0].source)
