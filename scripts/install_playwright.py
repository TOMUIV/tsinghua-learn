#!/usr/bin/env python3
"""
install_playwright.py
下载并安装 Playwright Chromium 浏览器
======================================
【用途】
  运行任何需要 Playwright 的脚本前，先跑一次这个
  如果遇到 "Executable not found" 错误，运行这个即可修复

【用法】
  python install_playwright.py
"""
import sys, subprocess

def run():
    print("正在安装 Playwright Chromium（只会执行一次）...")
    print("这可能需要几分钟，请耐心等待...\n")

    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=False
    )

    if result.returncode == 0:
        print("\n✅ Chromium 安装成功！")
        print("   现在可以运行 login_supervised.py 等脚本了。")
    else:
        print("\n❌ 安装失败，请检查网络连接后重试")
        print("   或手动运行: python -m playwright install chromium")


if __name__ == "__main__":
    run()