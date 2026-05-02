#!/usr/bin/env python3
"""
login_supervised.py
清华网络学堂 - 有人值守登录脚本（双脚本方案·第一套）
======================================================
【什么时候用】
  首次配置 / Profile 丢失 / Session 彻底失效时。
  需要人工完成二次验证（2FA），只需跑这一次。

【工作流程】
  1. 从 credentials.json 读取账号密码
  2. 使用固定 profile 目录（cookies 持久化，避免每次触发 2FA）
  3. 弹出浏览器窗口，可视化完成登录 + 2FA
  4. 登录成功后保存 Session 到 sessions/learn_session.json
  5. 下次直接用 login_auto.py 无人值守自动续期

【重要原则】
  固定 profile 路径：profiles/learn_profile/（永不重建）
  不管脚本跑多少次，都用同一个 profile → cookies 复用 → 不触发 2FA
"""
import sys, os, json, time, re
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

# ====== 账号密码（从 credentials.json 统一加载）=======
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_credentials, get_state_file, get_fp_file, get_profile_dir

STATE_FILE       = get_state_file()
FINGERPRINT_FILE = get_fp_file()
PROFILE_DIR      = get_profile_dir()

try:
    _creds = load_credentials()
    USER = _creds.get("username", "")
    PASS = _creds.get("password", "")
    if not USER or not PASS:
        raise ValueError("username 或 password 为空")
except Exception as e:
    print(e)
    raise SystemExit(1)

CAS_URL = "https://id.tsinghua.edu.cn/do/off/ui/auth/login/form/bb5df85216504820be7bba2b0ae1535b/0"

# ====== 正文 ======
fp = json.load(open(FINGERPRINT_FILE, encoding="utf-8"))
os.makedirs(PROFILE_DIR, exist_ok=True)


def save_state(ctx, page_url, csrf):
    """提取并保存完整 Session"""
    learn_jsession = None
    learn_token    = None
    for c in ctx.cookies():
        if "learn.tsinghua" in c["domain"]:
            if c["name"] == "JSESSIONID": learn_jsession = c["value"]
            elif c["name"] == "XSRF-TOKEN": learn_token = c["value"]

    state = {
        "learn_jsession": learn_jsession,
        "learn_token":    learn_token,
        "csrf":           csrf,
        "timestamp":      time.time(),
        "url":            page_url,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"✅ Session 已保存: {STATE_FILE}")
    return state


pw = sync_playwright().start()
ctx = None
try:
    ctx = pw.chromium.launch_persistent_context(
        PROFILE_DIR,
        headless=False,                    # 可视化，可做 2FA
        viewport={"width": 1280, "height": 900},
        args=["--no-sandbox", "--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled"],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print(f"打开登录页: {CAS_URL}")
    page.goto(CAS_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)

    page.evaluate(
        "localStorage.setItem('fingerPrint', '" + fp["fingerPrint"] + "');"
        "localStorage.setItem('fingerGenPrint', '" + fp.get("fingerGenPrint","") + "');"
        "localStorage.setItem('fingerGenPrint3', '" + fp.get("fingerGenPrint3","") + "');"
    )
    time.sleep(1)

    page.fill("#i_user", USER)
    page.fill("#i_pass", PASS)
    print(f"凭据已填入: {USER}")
    print("触发 doLogin()，请在浏览器中完成二次验证（如有）...")

    page.evaluate("doLogin()")
    time.sleep(3)

    title = page.title()
    body  = page.inner_text("body")[:300]

    if "二次认证" in title or "二次验证" in body:
        print()
        print("=" * 40)
        print("⚠️  检测到二次验证！")
        print("   请在浏览器窗口中完成验证（企业微信/短信）")
        print("   完成后脚本自动继续...")
        print("=" * 40)
        page.wait_for_url("**://learn.tsinghua.edu.cn/**", timeout=120000)
        print("✅ 验证完成")
    else:
        try:
            page.wait_for_url("**://learn.tsinghua.edu.cn/**", timeout=60000)
            print("✅ 登录成功")
        except Exception:
            print(f"⚠️ 未检测到跳转，当前URL: {page.url}")

    time.sleep(2)

    csrf = None
    if "_csrf" in page.url:
        for p2 in page.url.split("?")[1].split("&"):
            if p2.startswith("_csrf="): csrf = p2.split("=")[1]
    if not csrf:
        m = re.search(r'_csrf=([a-f0-9\-]{32,})', page.content())
        if m: csrf = m.group(1)

    state = save_state(ctx, page.url, csrf)
    print(f"\nJSESSIONID: {state.get('learn_jsession','?')[:10]}...")
    print("\n🎉 完成！以后运行 login_auto.py 即可无人值守登录。")

finally:
    if ctx: ctx.close()
    pw.stop()