# -*- coding: utf-8 -*-
"""灵枢 LingHub —— 开发模式启动器

用法：
    python run.py

说明：
    主程序 main.py 是一个 58k 行的单体模块，顶部有大量模块级初始化代码，
    且依赖 `if __name__ == "__main__"` 分支启动。因此这里用 runpy 以
    "__main__" 身份执行它，等价于 `python src/lingshu/main.py`，
    但额外把项目根目录的 config/app_config.json 注入为配置来源。
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT, "src", "lingshu")
CONFIG = os.path.join(ROOT, "config", "app_config.json")

# 让主程序优先读到工程内的配置文件
os.environ.setdefault("LINGSHU_CONFIG", CONFIG)

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

runpy.run_path(os.path.join(SRC_DIR, "main.py"), run_name="__main__")
