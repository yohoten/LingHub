# -*- coding: utf-8 -*-
"""灵枢 LingHub —— PyInstaller 打包入口

PyInstaller 只能接受单一脚本作为入口，而主程序是必须整体执行的单体模块，
故这里用 runpy 以 "__main__" 身份运行随包分发的 main.py。

- 非冻结环境：从 src/lingshu 读取源码
- 冻结环境：  从 _MEIPASS/lingshu_src 读取（由 build/lingshu.spec 打包进去）
"""
import os
import runpy
import sys

if getattr(sys, "frozen", False):
    _BASE = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    SRC_DIR = os.path.join(_BASE, "lingshu_src")
else:
    SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "lingshu")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

runpy.run_path(os.path.join(SRC_DIR, "main.py"), run_name="__main__")
