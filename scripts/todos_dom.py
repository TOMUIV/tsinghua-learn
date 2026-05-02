#!/usr/bin/env python3
"""
todos_dom.py
清华网络学堂代办总览 — DOM 解析版（备用）
============================================
课程列表从 API 动态获取，DOM 解析使用课程名作边界。
"""
import json, requests, sys, time, shutil, tempfile, re, os
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import get_state_file, get_profile_dir, get_fp_file
from learn_api import LearnAPI

STATE_FILE = get_state_file()
PROFILE_DIR = get_profile_dir()
FINGERPRINT_FILE = get_fp_file()


def check_session(state):
    if not state.get("learn_jsession") or not state.get("csrf"):
        return False
    h = {
        "Accept": "application/json, */*",
        "Referer": "https://learn.tsinghua.edu.cn/f/wlxt/index/course/student/",
        "X-XSRF-TOKEN": state["csrf"],
        "Cookie": f"JSESSIONID={state['learn_jsession']}; XSRF-TOKEN={state['csrf']}",
    }
    try:
        r = requests.get(
            "https://learn.tsinghua.edu.cn/b/wlxt/kczy/zy/student/index/zyListWj?wlkcid=&size=1",
            headers=h, timeout=10
        )
        return not ("location.href" in r.text and r.status_code == 200)
    except:
        return False


def auto_relogin():
    """调 login_auto.py 续期 Session"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    auto_script = os.path.join(script_dir, "login_auto.py")
    print("Session 失效，自动续期中...")
    import subprocess
    result = subprocess.run([sys.executable, auto_script],
                             capture_output=True)
    stdout = result.stdout.decode('utf-8', errors='replace')
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')
        print("auto login 失败:", stderr)
        sys.exit(1)
    print(stdout)
    return json.load(open(STATE_FILE, encoding="utf-8"))


def api_get(path, csrf, learn_j):
    url = f"https://learn.tsinghua.edu.cn{path}&_csrf={csrf}" if "?" in path \
          else f"https://learn.tsinghua.edu.cn{path}?_csrf={csrf}"
    return requests.get(url, headers={
        "Accept": "application/json, */*",
        "Referer": "https://learn.tsinghua.edu.cn/f/wlxt/index/course/student/",
        "X-XSRF-TOKEN": csrf,
        "Cookie": f"JSESSIONID={learn_j}; XSRF-TOKEN={csrf}",
    }, timeout=15).json()


# ====== 主流程 ======
state = json.load(open(STATE_FILE, encoding="utf-8"))
age_h = (time.time() - state.get("timestamp", 0)) / 3600
print(f"Session age={age_h:.1f}h")

if not check_session(state):
    print("⚠️ Session 无效")
    state = auto_relogin()
else:
    print("✅ Session 有效")

csrf = state["csrf"]
learn_j = state["learn_jsession"]

# 动态获取课程列表
api = LearnAPI(session_file=STATE_FILE)
api.reload_session()
courses = api.get_courses()
# 按名称排序保证边界查找稳定
course_names = sorted([c.get("kcm", "?") for c in courses])

# Playwright 读主页 DOM
TMP = tempfile.mkdtemp(prefix="todos_")
PROFILE_TMP = os.path.join(TMP, "profile")
os.makedirs(PROFILE_TMP)

pw = sync_playwright().start()
ctx = None
try:
    ctx = pw.chromium.launch_persistent_context(
        PROFILE_TMP, headless=True,
        viewport={"width": 1280, "height": 900},
        ignore_https_errors=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    ctx.add_cookies([
        {"name": "JSESSIONID", "value": learn_j, "domain": ".learn.tsinghua.edu.cn", "path": "/"},
        {"name": "XSRF-TOKEN", "value": csrf, "domain": ".learn.tsinghua.edu.cn", "path": "/"},
    ])
    page.goto(
        "https://learn.tsinghua.edu.cn/f/wlxt/index/course/student/",
        timeout=30000, wait_until="networkidle"
    )
    time.sleep(3)
    body_text = page.inner_text("body")
finally:
    if ctx: ctx.close()
    pw.stop()
    shutil.rmtree(TMP, ignore_errors=True)

# 用课程名列表作边界解析 DOM
def parse_courses(text, names):
    results = {}
    for i, cname in enumerate(names):
        idx = text.find(cname)
        if idx < 0:
            results[cname] = {"gg": 0, "kj": 0, "zy": 0, "tl": 0, "dy": 0, "wj": 0}
            continue
        # 用下一门课名作边界（不存在则到文本末尾）
        if i + 1 < len(names):
            next_idx = text.find(names[i + 1], idx + len(cname))
            end = next_idx if next_idx > idx else len(text)
        else:
            end = len(text)
        chunk = text[idx:end]
        def get_count(pat):
            m = re.search(pat, chunk)
            return int(m.group(1)) if m else 0
        results[cname] = {
            "gg": get_count(r"公告\s*(\d+)"),
            "kj": get_count(r"课件\s*(\d+)"),
            "zy": get_count(r"作业\s*(\d+)"),
            "tl": get_count(r"讨论\s*(\d+)\s*我参与"),
            "dy": get_count(r"答疑\s*(\d+)"),
            "wj": get_count(r"问卷\s*(\d+)"),
        }
    return results

course_todos = parse_courses(body_text, course_names)

# API 获取作业详情
def fetch_all_homework():
    results = []
    for c in courses:
        wlkcid = c["wlkcid"]
        d = api_get(f"/b/wlxt/kczy/zy/student/index/zyListWj?wlkcid={wlkcid}&size=100", csrf, learn_j)
        items = d.get("object", {}).get("aaData", [])
        for x in items:
            if x.get("zt") == "未交":
                results.append({
                    "course_name": c.get("kcm", "?"),
                    "bt": x.get("bt", ""),
                    "jzsjStr": x.get("jzsjStr", ""),
                })
    return results

# 汇总输出
print("\n=== 网络学堂代办总览（DOM）===\n")
total = 0
for cname, todos in course_todos.items():
    print(f"【{cname}】")
    has_todo = False
    for cat, label in [
        ("zy", "作业未提交"), ("gg", "公告未浏览"), ("kj", "课件未浏览"),
        ("tl", "讨论我参与"), ("dy", "答疑已回答"), ("wj", "问卷未提交"),
    ]:
        count = todos[cat]
        if count > 0:
            print(f"  ⚠️ {label}: {count} 项")
            total += count
            has_todo = True
    if not has_todo:
        print(f"  ✅ 无待处理")

has_zy = any(todos["zy"] > 0 for todos in course_todos.values())
if has_zy:
    print("\n--- 作业详情 ---")
    hw_list = fetch_all_homework()
    for x in sorted(hw_list, key=lambda x: x.get("jzsjStr", "")):
        print(f"  {x['course_name']} | {x['bt']} | 截止:{x['jzsjStr']}")

print(f"\n待办总计: {total} 项")
