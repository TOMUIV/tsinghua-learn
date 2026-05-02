# tsinghua-learn

清华网络学堂（learn.tsinghua.edu.cn）自动化 Skill。

## 功能

- 查看待办（公告、作业、课件、讨论）
- 提交作业（支持 PDF 直接提交或图片合并后提交）
- 下载课件
- 批量标记已读
- 工作区清理
- 图片→PDF 合并（支持 HEIC 格式）

## 安装

本 Skill 已上线 ClawHub，搜索 **"tsinghua-learn"** 即可一键安装。

手动安装：

```bash
pip install requests playwright beautifulsoup4 pillow pillow-heif
python scripts/install_playwright.py
python scripts/login_manager.py --init --learn-account=账号 --password=密码 --username=学号 --name=姓名
python scripts/login_manager.py --verify
python scripts/todos_api.py
```

## 依赖

- Python 3.10+
- requests, playwright, beautifulsoup4, pillow, pillow-heif

## 许可

MIT
