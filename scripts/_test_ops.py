#!/usr/bin/env python3
"""Test ops and active course APIs."""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from learn_api import LearnAPI
from ops import list_course_files, download_file, cleanup

api = LearnAPI()
api.reload_session()
courses = api.get_courses()

# Find 微积分
target = None
for c in courses:
    if '微积分' in c.get('kcm', ''):
        target = c
        break

if not target:
    print("微积分 not found")
    sys.exit(1)

wlkcid = target["wlkcid"]
print("=== " + target["kcm"] + " (wlkcid=" + wlkcid + ") ===")

gg = api.get_announcements(wlkcid)
print("公告: " + str(len(gg)))
for a in gg[:3]:
    print("  [" + str(a.get("sfyd","?")) + "] " + a.get("bt","?"))

files = api.get_files(wlkcid)
print("课件: " + str(len(files)))
for f in files[:5]:
    print("  [isNew=" + str(f.get("isNew","?")) + "] " + f.get("bt","?") + "." + f.get("wjlx","?"))

hws = api.get_homeworks(wlkcid)
print("作业: " + str(len(hws)))
for h in hws[:5]:
    print("  [" + h.get("zt","?") + "] " + h.get("bt","?"))

# Homework full detail
if hws:
    h = hws[0]
    detail = api.get_homework_full_detail(wlkcid, h.get("zyid",""), h.get("xszyid",""))
    print("\n作业详情:")
    for k, v in detail.items():
        if k not in ("attachments", "raw_html_len"):
            print("  " + k + ": " + str(v))
    if detail.get("attachments"):
        print("  附件:")
        for a in detail["attachments"]:
            print("    " + a["name"])

# Test ops list_course_files
print("\n=== ops.list_course_files ===")
listed = list_course_files(wlkcid)
print("Files: " + str(len(listed)))
for f in listed[:3]:
    print("  " + f["name"])

# Test cleanup preview
print("\n=== ops.cleanup(dry_run=True) ===")
cleanup(dry_run=True)
