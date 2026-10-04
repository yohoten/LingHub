# -*- mode: python ; coding: utf-8 -*-
"""灵枢 LingHub —— PyInstaller 打包配置（onedir）

打包命令：
    pyinstaller build/lingshu.spec --noconfirm --distpath dist --workpath build/.tmp

产物：dist/LingHub/LingHub.exe + dist/LingHub/_internal/
配置文件会随包分发到 _internal/config/app_config.json，改它即可改授权/更新行为。
"""
from PyInstaller.utils.hooks import collect_submodules

APP_NAME = "LingHub"

# 主程序以源码形式随包分发，运行时由 pack_entry.py 用 runpy 执行
datas = [
    ("../src/lingshu/main.py", "lingshu_src"),
    ("../src/lingshu/parse_rule.py", "lingshu_src"),
    ("../src/lingshu/template_render.py", "lingshu_src"),
    ("../config/app_config.json", "config"),
]

hiddenimports = []
for _m in ("pynput", "pynput.keyboard", "pynput.mouse", "pyautogui", "mss"):
    try:
        hiddenimports += collect_submodules(_m)
    except Exception:
        pass
hiddenimports += [
    "cv2",
    "numpy",
    "PIL",
    "PIL.ImageGrab",
    "psutil",
    "requests",
    "urllib3",
    "certifi",
]

excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "pandas",
    "notebook",
    "jupyter",
    "pytest",
]

a = Analysis(
    ["../pack_entry.py"],
    pathex=["../src/lingshu"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # GUI 程序，不弹控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # 图标由 main.py 运行时动态生成（见 get_app_svg_icon）
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
