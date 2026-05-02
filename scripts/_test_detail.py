#!/usr/bin/env python3
"""Test graded homework detail and announcement operations."""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from learn_api import LearnAPI

api = LearnAPI()
api.reload_session()
courses = api.get_courses()

# 微积分
target = None
for c in courses:
    if '微积分' in c.get('kcm', ''):
        target = c
        break
if not target:
    print("微积分 not found")
    sys.exit(1)

wlkcid = target["wlkcid"]

# 1. Test announcement detail and mark read
gg = api.get_announcements(wlkcid)
print("=== 公告测试 ===")
for a in gg[:2]:
    aid = a.get("id", a.get("ggid", ""))
    print("\n公告: " + a.get("bt", "?"))
    print("  未读: " + str(a.get("sfyd") == "否"))
    detail = api.get_announcement_detail(wlkcid, aid)
    print("  内容[:100]: " + detail["content"][:100])
    if a.get("sfyd") == "否":
        ok = api.mark_announcement_read(wlkcid, aid)
        print("  标已读: " + ("OK" if ok else "FAIL"))
        if not ok:
            print("  (可能API不同,需DOM探索确认)")

# 2. Test graded homework detail
hws = api.get_homeworks(wlkcid)
print("\n=== 作业详情测试 ===")
graded = [h for h in hws if h.get("zt") in ("已交", "已批改")]
if graded:
    h = graded[0]
    print("测试: " + h.get("bt", "?") + " (status=" + h.get("zt", "?") + ")")
    detail = api.get_homework_full_detail(wlkcid, h.get("zyid",""), h.get("xszyid",""))
    for k, v in detail.items():
        if k not in ("attachments", "raw_html_len"):
            print("  " + k + ": " + str(v))
else:
    print("没有已交/已批改的作业, 试试其他课程...")
    # Try 概率论
    for c in courses:
        if '概率' in c.get('kcm', ''):
            hws2 = api.get_homeworks(c["wlkcid"])
            graded2 = [h for h in hws2 if h.get("zt") in ("已交", "已批改")]
            if graded2:
                h = graded2[0]
                print("\n概率论作业: " + h.get("bt", "?") + " (status=" + h.get("zt", "?") + ")")
                detail = api.get_homework_full_detail(c["wlkcid"], h.get("zyid",""), h.get("xszyid",""))
                for k, v in detail.items():
                    if k not in ("attachments", "raw_html_len"):
                        print("  " + k + ": " + str(v))
            break

# 3. Test mark_file_read
files = api.get_files(wlkcid)
unread = [f for f in files if str(f.get("isNew", "")) == "1"]
print("\n=== 课件标已读测试 ===")
if unread:
    f = unread[0]
    ok = api.mark_file_read(f["wjid"])
    print("标记 " + f.get("bt","?") + ": " + ("OK" if ok else "FAIL"))
else:
    print("无未读课件")

# 4. Test mark_all_announcements_read
print("\n=== 批量标公告已读 ===")
marked, total = api.mark_all_announcements_read(wlkcid)
print("标记 " + str(marked) + "/" + str(total) + " 项")
