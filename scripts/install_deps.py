#!/usr/bin/env python3
"""
install_deps.py — 检查 Python 版本并安装所需依赖。
AI 使用，无阻塞逻辑。
"""
import sys, os, json, subprocess, importlib

sys.stdout.reconfigure(encoding='utf-8')

REQUIRED_VERSION = (3, 10)
REQUIRED_PACKAGES = [
    "requests==2.32.3",
    "playwright==1.52.0",
    "beautifulsoup4==4.13.4",
    "pillow==11.2.1",
    "pillow-heif==0.21.0",
    "cryptography",
]

# pip 包名 → import 模块名对照
_IMPORT_NAMES = {
    "beautifulsoup4": "bs4",
    "pillow": "PIL",
    "pillow-heif": "pillow_heif",
}


def check_python():
    v = sys.version_info
    if v < REQUIRED_VERSION:
        return {"status": "error", "message": f"Python {REQUIRED_VERSION[0]}.{REQUIRED_VERSION[1]}+ 必须，当前: {v.major}.{v.minor}"}
    return {"status": "ok", "version": f"{v.major}.{v.minor}.{v.micro}"}


def check_package(name):
    mod = _IMPORT_NAMES.get(name, name.replace("-", "_"))
    try:
        importlib.import_module(mod)
        return True
    except ImportError:
        return False


def install(package):
    cmd = [sys.executable, "-m", "pip", "install"]
    # 小内存服务器上，cryptography 源码编译容易 OOM；强制使用 wheel。
    if package.split("==")[0] == "cryptography":
        cmd.extend(["--only-binary=:all:"])
    cmd.append(package)
    try:
        # 云服务器网络和镜像波动较大，适当放宽超时时间。
        r = subprocess.run(cmd, capture_output=True, timeout=600)
        if r.returncode == 0:
            return True, ""
        err = r.stderr.decode("utf-8", errors="replace").strip()
        return False, err[-300:] if err else "pip install 失败"
    except subprocess.TimeoutExpired:
        return False, "安装超时（600s）"


if __name__ == "__main__":
    py_result = check_python()
    if py_result["status"] == "error":
        print(json.dumps(py_result, ensure_ascii=False))
        sys.exit(1)

    missing = [p for p in REQUIRED_PACKAGES if not check_package(p)]
    if not missing:
        print(json.dumps({"status": "ok", "message": "\u6240\u6709\u4f9d\u8d56\u5df2\u5b89\u88c5", "python": py_result["version"]}, ensure_ascii=False))
        sys.exit(0)

    results = {}
    errors = {}
    all_ok = True
    for pkg in missing:
        ok, err = install(pkg)
        results[pkg] = ok
        if not ok:
            all_ok = False
            errors[pkg] = err

    if all_ok:
        print(json.dumps({"status": "ok", "message": "\u4f9d\u8d56\u5b89\u88c5\u5b8c\u6210", "python": py_result["version"], "installed": missing}, ensure_ascii=False))
    else:
        failed = [p for p, ok in results.items() if not ok]
        print(json.dumps({
            "status": "error",
            "message": f"\u4f9d\u8d56\u5b89\u88c5\u5931\u8d25: {failed}",
            "errors": errors,
        }, ensure_ascii=False))
        sys.exit(1)
