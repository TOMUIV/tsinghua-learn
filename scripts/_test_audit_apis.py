#!/usr/bin/env python3
"""
API 审计：逐一验证 learn_api.py 中每个 API 端点是否正确。
"""
import sys, os, json, traceback
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.filterwarnings('ignore')
from learn_api import LearnAPI, LEARN_BASE

api = LearnAPI()
ok = api.reload_session()
assert ok, "session invalid"

results = {"pass": 0, "fail": [], "skip": []}

def check(name, fn):
    try:
        fn()
        results["pass"] += 1
        print(f"  ✅ {name}")
    except Exception as e:
        results["fail"].append({"name": name, "error": str(e), "trace": traceback.format_exc()})
        print(f"  ❌ {name}: {e}")

courses = api.get_courses()
target = None
for c in courses:
    if "\u5fae\u79ef\u5206" in c.get("kcm", ""):
        target = c
        break
if not target:
    target = courses[0]
wlkcid = target["wlkcid"]

# ── 1. 学期 ──
print("\n=== 学期 ===")
def t_sem():
    s = api.get_current_semester()
    assert s, "empty semester"
check("get_current_semester", t_sem)

def t_sems():
    s = api.get_semesters()
    assert isinstance(s, list)
check("get_semesters", t_sems)

# ── 2. 课程 ──
print("\n=== 课程 ===")
def t_courses():
    c = api.get_courses()
    assert len(c) > 0
check("get_courses", t_courses)

# ── 3. 公告 ──
print("\n=== 公告 ===")
ggs = api.get_announcements(wlkcid)

def t_ggs():
    assert isinstance(ggs, list)
check("get_announcements", t_ggs)

if ggs:
    gid = ggs[0].get("ggid") or ggs[0].get("id", "")
    def t_gg_detail():
        d = api.get_announcement_detail(wlkcid, gid)
        assert d.get("title")
    check("get_announcement_detail", t_gg_detail)

    def t_mark_gg():
        assert api.mark_announcement_read(wlkcid, gid)
    check("mark_announcement_read", t_mark_gg)

# ── 4. 课件文件 ──
print("\n=== 课件文件 ===")
files = api.get_files(wlkcid)

def t_files():
    assert isinstance(files, list)
check("get_files", t_files)

def t_cats():
    c = api.get_file_categories(wlkcid)
    assert isinstance(c, list)
check("get_file_categories", t_cats)

if files:
    def t_dl():
        # GET 前 1 字节验证端点可访问（HEAD 被服务器拒绝）
        h = {"X-XSRF-TOKEN": api.xsrf_token, "Range": "bytes=0-1"} if api.xsrf_token else {"Range": "bytes=0-1"}
        r = api.session.get(
            LEARN_BASE + "/b/wlxt/kj/wlkc_kjxxb/student/downloadFile",
            params={"sfgk": 0, "wjid": files[0]["wjid"]},
            headers=h,
            verify=False, timeout=10
        )
        assert r.status_code in (200, 206, 302), f"download endpoint returned {r.status_code}"
    check("download_file endpoint", t_dl)

    unread = [f for f in files if str(f.get("isNew", "")) == "1"]
    if unread:
        def t_mark_f():
            assert api.mark_file_read(unread[0]["wjid"])
        check("mark_file_read", t_mark_f)

# ── 5. 作业 ──
print("\n=== 作业 ===")
hws = api.get_homeworks(wlkcid)

def t_hws():
    assert isinstance(hws, list)
check("get_homeworks", t_hws)

# 验证作业数据来自正确的端点
if hws:
    h = hws[0]
    print(f"     样本: [{h.get('zt','')}] {h.get('bt','')} wlkcid={h.get('wlkcid','?')}")

if hws:
    h = hws[0]
    for field in ["zyid", "bt", "zt"]:
        def t_hw_field(f=field):
            assert h.get(f) is not None, f + " missing in homework data"
        check("homework field: " + field, t_hw_field)

    def t_hw_detail():
        d = api.get_homework_detail(wlkcid, h.get("zyid",""), h.get("xszyid",""))
        assert d.get("title")
    check("get_homework_detail", t_hw_detail)

    def t_hw_full():
        d = api.get_homework_full_detail(wlkcid, h.get("zyid",""), h.get("xszyid",""))
        assert d.get("title")
    check("get_homework_full_detail", t_hw_full)

    for hw in hws:
        if hw.get("zt") == "\u5df2\u6279\u6539":
            def t_hw_graded():
                d = api.get_homework_full_detail(wlkcid, hw.get("zyid",""), hw.get("xszyid",""))
                assert d.get("title")
            check("已批改 homework detail", t_hw_graded)
            break

# ── 6. 讨论 ──
print("\n=== 讨论 ===")
def t_tl():
    t = api.get_discussions(wlkcid)
    assert isinstance(t, list)
check("get_discussions", t_tl)

tl = api.get_discussions(wlkcid)
if tl:
    def t_tl_detail():
        d = api.get_discussion_detail(wlkcid, tl[0].get("id",""), tl[0].get("bqid",""))
        assert isinstance(d, str)
    check("get_discussion_detail", t_tl_detail)

# ── 7. 问卷 ──
print("\n=== 问卷 ===")
def t_wj():
    w = api.get_questionnaires(wlkcid)
    assert isinstance(w, list)
check("get_questionnaires", t_wj)

def t_wj_all():
    w = api.get_all_unanswered_questionnaires()
    assert isinstance(w, list)
check("get_all_unanswered_questionnaires", t_wj_all)

# ── 8. 聚合 ──
print("\n=== 聚合查询 ===")
def t_agg():
    d = api.get_course_detail(wlkcid)
    for k in ("announcements", "files", "homeworks", "discussions"):
        assert k in d, f"aggregated missing {k}"
check("get_course_detail", t_agg)

# ── 9. 批量标已读 ──
print("\n=== 批量标已读 ===")
def t_mark_all_gg():
    m = api.mark_all_announcements_read(wlkcid)
    assert isinstance(m, tuple) and len(m) == 2
check("mark_all_announcements_read", t_mark_all_gg)

def t_mark_all_kj():
    m = api.mark_all_files_read(wlkcid)
    assert isinstance(m, tuple) and len(m) == 2
check("mark_all_files_read", t_mark_all_kj)

# ── 汇总 ──
print(f"\n{'='*40}")
total = results["pass"] + len(results["fail"])
print(f"Total tests: {total}")
print(f"Passed: {results['pass']}")
print(f"Failed: {len(results['fail'])}")
for f in results["fail"]:
    print(f"  ❌ {f['name']}: {f['error']}")
sys.exit(0 if not results["fail"] else 1)
