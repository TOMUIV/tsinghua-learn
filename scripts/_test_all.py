#!/usr/bin/env python3
"""
_test_all.py — 全功能综合测试
测试所有脚本的所有主要功能，输出 JSON 结果。
"""
import sys, os, json, subprocess
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.filterwarnings('ignore')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
PASS = 0; FAIL = 0; TESTS = []

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        TESTS.append({"name": name, "status": "PASS"})
        PASS += 1
        print(f"  ✅ {name}")
    except Exception as e:
        TESTS.append({"name": name, "status": "FAIL", "error": str(e)})
        FAIL += 1
        print(f"  ❌ {name}: {e}")

def run_script(script, *args):
    cmd = [PY, os.path.join(SCRIPTS_DIR, script)] + list(args)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(cmd, capture_output=True, env=env)
    out = r.stdout.decode("utf-8", errors="replace")
    err = r.stderr.decode("utf-8", errors="replace")
    return r.returncode, out, err

# ─── 定义所有测试函数 ─────────────────────────
from learn_api import LearnAPI, LEARN_BASE

# 全局 API 实例
_api = LearnAPI()
_ok = _api.reload_session()
_courses = _api.get_courses() if _ok else []
_active = None
for c in _courses:
    if "微积分" in c.get("kcm", "") or "概率" in c.get("kcm", ""):
        _active = c; break
_active = _active or (_courses[0] if _courses else None)
_wlkcid = _active["wlkcid"] if _active else None
_ggs = _api.get_announcements(_wlkcid) if _wlkcid else []
_files = _api.get_files(_wlkcid) if _wlkcid else []
_hws = _api.get_homeworks(_wlkcid) if _wlkcid else []
_unread_files = [f for f in _files if str(f.get("isNew","")) == "1"] if _files else []

# ── 1. login_manager ──
def t_login_check():
    rc, out, err = run_script("login_manager.py", "--check")
    assert rc == 0, f"exit code {rc}: {err[:200]}"
    data = json.loads(out.strip())
    assert data.get("valid") == True

# ── 2. learn_api 基础 ──
def t_courses():
    assert _ok, "reload_session failed"
    assert len(_courses) > 0

def t_announcements():
    items = _api.get_announcements(_wlkcid)
    assert isinstance(items, list)

def t_files():
    items = _api.get_files(_wlkcid)
    assert isinstance(items, list)

def t_homeworks():
    items = _api.get_homeworks(_wlkcid)
    assert isinstance(items, list)

def t_discussions():
    items = _api.get_discussions(_wlkcid)
    assert isinstance(items, list)

def t_questionnaires():
    items = _api.get_questionnaires(_wlkcid)
    assert isinstance(items, list)

def t_aggregated():
    detail = _api.get_course_detail(_wlkcid)
    for k in ("announcements", "files", "homeworks", "discussions"):
        assert k in detail

# ── 3. learn_api 详情 ──
def t_announcement_detail():
    if not _ggs: return
    g = _ggs[0]
    gid = g.get("id") or g.get("ggid") or ""
    detail = _api.get_announcement_detail(_wlkcid, gid)
    assert "title" in detail

def t_hw_detail():
    if not _hws: return
    h = _hws[0]
    detail = _api.get_homework_detail(_wlkcid, h.get("zyid",""), h.get("xszyid",""))
    assert "title" in detail

def t_hw_full():
    if not _hws: return
    h = _hws[0]
    detail = _api.get_homework_full_detail(_wlkcid, h.get("zyid",""), h.get("xszyid",""))
    assert "title" in detail

def t_hw_graded():
    for h in _hws:
        if h.get("zt") == "已批改":
            detail = _api.get_homework_full_detail(_wlkcid, h.get("zyid",""), h.get("xszyid",""))
            assert "title" in detail
            break

# ── 4. learn_api 标已读 ──
def t_mark_gg():
    if not _ggs: return
    g = _ggs[0]
    gid = g.get("id") or g.get("ggid") or ""
    ok = _api.mark_announcement_read(_wlkcid, gid)
    assert ok

def t_mark_file():
    if not _unread_files: return
    ok = _api.mark_file_read(_unread_files[0]["wjid"])
    assert ok

def t_mark_all_gg():
    marked, total = _api.mark_all_announcements_read(_wlkcid)
    assert isinstance(marked, int) and isinstance(total, int)

def t_mark_all_kj():
    marked, total = _api.mark_all_files_read(_wlkcid)
    assert isinstance(marked, int) and isinstance(total, int)

# ── 5. ops.py ──
from ops import list_course_files, download_file, cleanup

def t_ops_list():
    files = list_course_files(_wlkcid)
    assert isinstance(files, list)

def t_ops_download():
    if not _files: return
    path = download_file(_wlkcid, _files[0].get("wjid",""))
    assert path is None or os.path.exists(path)

def t_ops_cleanup_dry():
    result = cleanup(dry_run=True)
    assert result["status"] == "preview"
    assert "total_files" in result

# ── 6. todos_api.py ──
def t_todos_summary():
    rc, out, err = run_script("todos_api.py")
    assert rc == 0, f"exit {rc}: {err[:200]}"
    assert "courses" in out, "JSON output missing 'courses' key"

def t_todos_mark_read():
    rc, out, err = run_script("todos_api.py", "--mark-read")
    assert rc == 0

def t_todos_cleanup():
    rc, out, err = run_script("todos_api.py", "--cleanup-preview")
    assert rc == 0

# ─── 执行所有测试 ─────────────────────────────
print("\n=== 1. login_manager ===")
test("login_manager --check", t_login_check)

print("\n=== 2. learn_api 基础查询 ===")
test("get_courses", t_courses)
test("get_announcements", t_announcements)
test("get_files", t_files)
test("get_homeworks", t_homeworks)
test("get_discussions", t_discussions)
test("get_questionnaires", t_questionnaires)
test("get_course_detail (aggregated)", t_aggregated)

print("\n=== 3. learn_api 详情查询 ===")
test("get_announcement_detail", t_announcement_detail)
test("get_homework_detail", t_hw_detail)
test("get_homework_full_detail", t_hw_full)
test("已批改 homework detail", t_hw_graded)

print("\n=== 4. learn_api 标已读 ===")
test("mark_announcement_read", t_mark_gg)
test("mark_file_read", t_mark_file)
test("mark_all_announcements_read", t_mark_all_gg)
test("mark_all_files_read", t_mark_all_kj)

print("\n=== 5. ops.py ===")
test("list_course_files", t_ops_list)
test("download_file", t_ops_download)
test("cleanup (dry-run)", t_ops_cleanup_dry)

print("\n=== 6. todos_api.py ===")
test("todos summary", t_todos_summary)
test("todos --mark-read", t_todos_mark_read)
test("todos --cleanup-preview", t_todos_cleanup)

# ─── 汇总 ─────────────────────────────────────
total = PASS + FAIL
print(f"\n{'='*40}")
print(f"Total: {total} tests")
print(f"Passed: {PASS}")
print(f"Failed: {FAIL}")
print(json.dumps({"passed": PASS, "failed": FAIL, "tests": TESTS}, ensure_ascii=False, indent=2))
sys.exit(0 if FAIL == 0 else 1)
