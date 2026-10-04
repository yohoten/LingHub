# -*- coding: utf-8 -*-
"""灵枢 LingHub —— 冒烟测试

在无显示器的环境（CI / 远程会话）下也能跑：
    QT_QPA_PLATFORM=offscreen python tools/smoke_test.py

校验分三层：
    L1 模块可导入   —— 语法、依赖、模块级初始化不炸
    L2 品牌与配置   —— 重命名与配置外部化生效
    L3 主窗口可构造 —— Qt 对象树能建起来（离屏，不显示）

退出码 0 = 全部通过；非 0 = 失败。
"""
from __future__ import annotations

import importlib.util
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src", "lingshu")
CONFIG = os.path.join(PROJECT_ROOT, "config", "app_config.json")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("LINGSHU_CONFIG", CONFIG)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

results: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append((name, bool(cond), detail))


def load_main():
    spec = importlib.util.spec_from_file_location(
        "lingshu_main", os.path.join(SRC_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    # ---------------- L1 模块可导入 ----------------
    try:
        m = load_main()
        check("L1 主模块导入", True)
    except Exception as e:
        check("L1 主模块导入", False, f"{type(e).__name__}: {e}")
        report()
        return 1

    # ---------------- L2 品牌与配置 ----------------
    check("L2 SOFTWARE_NAME == 灵枢",
          getattr(m, "SOFTWARE_NAME", None) == "灵枢",
          f"实际={getattr(m, 'SOFTWARE_NAME', None)!r}")
    check("L2 APP_NAME == lingshu",
          getattr(m, "APP_NAME", None) == "lingshu",
          f"实际={getattr(m, 'APP_NAME', None)!r}")
    check("L2 数据目录为 ~/.lingshu",
          os.path.basename(str(getattr(m, "BASE_DATA_DIR", ""))) == ".lingshu",
          f"实际={getattr(m, 'BASE_DATA_DIR', None)!r}")
    check("L2 授权默认关闭",
          getattr(m, "LICENSE_ENABLED", None) is False,
          f"实际={getattr(m, 'LICENSE_ENABLED', None)!r}")
    check("L2 授权接口默认为空",
          getattr(m, "_PRIMARY_BASE", "?") == "" and getattr(m, "_BACKUP_BASE", "?") == "",
          f"primary={getattr(m, '_PRIMARY_BASE', None)!r}")
    check("L2 配置文件已加载",
          getattr(m, "APP_CONFIG_PATH", None) == CONFIG,
          f"实际={getattr(m, 'APP_CONFIG_PATH', None)!r}")
    check("L2 无旧品牌残留",
          not any(t in open(os.path.join(SRC_DIR, "main.py"), encoding="utf-8").read()
                  for t in ("道码灵镜", "道码灵境", "daoma", "dmlj", "TAICHI")))

    # ---------------- L3 主窗口可构造 ----------------
    # 注意：主窗口构造时会拉起 pynput 全局键鼠监听线程（非 daemon），
    # 因此不能走正常解释器退出流程，也不能调 close()（closeEvent 会弹确认框）。
    # 校验完标题后直接用 os._exit 结束进程。
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        win = m.MainWindow()
        title = win.windowTitle()
        check("L3 主窗口构造", "灵枢" in title, f"title={title!r}")
    except Exception as e:
        check("L3 主窗口构造", False, f"{type(e).__name__}: {e}")

    report()
    code = 0 if all(ok for _, ok, _ in results) else 1
    sys.stdout.flush()
    os._exit(code)


def report() -> None:
    print("\n== 冒烟测试结果 ==")
    for name, ok, detail in results:
        flag = "PASS" if ok else "FAIL"
        line = f"  [{flag}] {name}"
        if detail and not ok:
            line += f"  -> {detail}"
        elif detail:
            line += f"  ({detail})"
        print(line)
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n合计 {len(results) - len(failed)}/{len(results)} 通过")
    if failed:
        print("失败项：" + "、".join(failed))


if __name__ == "__main__":
    raise SystemExit(main())
