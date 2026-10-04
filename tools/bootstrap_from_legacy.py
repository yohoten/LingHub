# -*- coding: utf-8 -*-
"""灵枢 LingHub —— 旧版单体源码迁移工具

作用：把「道码灵镜/道码灵境」的单体源码（58k 行 main + parse_rule + template_render）
转换为可维护的工程源码，输出到 src/lingshu/。

设计原则：
1. 纯文本变换，不做语义改写 —— 保证行为与原版一致，便于 diff 回归。
2. 每个补丁都基于唯一锚点，锚点缺失时立即报错而不是静默跳过。
3. 可重复执行（幂等）：重复运行产出同样结果。

用法：
    python tools/bootstrap_from_legacy.py                      # 用默认源路径
    python tools/bootstrap_from_legacy.py --source <file>      # 指定源
    python tools/bootstrap_from_legacy.py --check              # 只校验锚点
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
SRC_PKG = os.path.join(PROJECT_ROOT, "src", "lingshu")

DEFAULT_SOURCE_DIR = r"F:\Download\Google download\道码灵镜2.6\道码灵境\_internal"
DEFAULT_SOURCE_MAIN = os.path.join(DEFAULT_SOURCE_DIR, "道码灵镜.txt")

# ---------------------------------------------------------------- 重命名映射
# 顺序敏感：先替换长词（复合品牌名），再替换短词。
RENAMES = [
    # 品牌名（中文）
    ("道码灵镜", "灵枢"),
    ("道码灵境", "灵枢"),
    # 数据目录 / 文件前缀
    (".daoma_spirit", ".lingshu"),
    ("_daoma_spirit_storage_v2_", "_lingshu_storage_v2_"),
    (".daoma_trial.dat", ".lingshu_trial.dat"),
    ('"daoma_spirit"', '"lingshu"'),
    ("daoma_fallback", "lingshu_fallback"),
    ("daoma_kminit_", "lingshu_kminit_"),
    ("daoma_audio_", "lingshu_audio_"),
    ("daoma_temp_", "lingshu_temp_"),
    ("daoma_result_", "lingshu_result_"),
    ("daoma_script_", "lingshu_script_"),
    # 常量 / 标识符
    ('APP_NAME = "dmlj"', 'APP_NAME = "lingshu"'),
    ('"app": "dmlj"', '"app": APP_NAME'),
    ("dmlj-storage-v2", "lingshu-storage-v2"),
    ("dmlj_runtime.exe", "lingshu_runtime.exe"),
    ("DaoMaLingJing_SingleInstance_", "LingHub_SingleInstance_"),
    ("ENCRYPT_KEY = \"TAICHI_AUTH_2026\"", "ENCRYPT_KEY = \"LINGSHU_AUTH_2026\""),
    ('MASTER_KEY = "TAICHI_2026_AUTH_MASTER_KEY_!@#$"',
     'MASTER_KEY = "LINGSHU_2026_AUTH_MASTER_KEY_!@#$"'),
    ('HASH_SALT = b"tai_chi_card_salt_2026"', 'HASH_SALT = b"lingshu_card_salt_2026"'),
    # 注册表清理关键词
    ('"Daoma"', '"LingHub"'),
    ('"DaomaLingjing"', '"LingHub"'),
    ('"DM_LJ"', '"LS_HUB"'),
]

# ---------------------------------------------------------------- 补丁定义
CONFIG_BLOCK = '''
# ============================================================
#  灵枢 LingHub —— 外部化配置（授权 / 更新 / 公告 / 购买链接）
# ============================================================
# 配置按下列顺序查找，第一个命中的生效：
#   1) 环境变量 LINGSHU_CONFIG 指向的文件
#   2) <程序目录>/config/app_config.json     （打包后的推荐位置）
#   3) <用户数据目录>/app_config.json
#   4) 内置默认值 DEFAULT_APP_CONFIG
#
# 默认 license.enabled = False —— 离线开发模式：
#   启动不弹授权窗、不发心跳、不访问任何外部地址。
DEFAULT_APP_CONFIG = {
    "license": {
        "enabled": False,
        "api_base": "",            # 例：https://your-domain.com/kami/qqXXXXXX
        "backup_api_base": "",
        "ping_endpoint": "/kami/ping",
        "ping_root": "",           # 留空则按 api_base 推导为 scheme://host
        "backup_ping_root": "",
        "app_id": "lingshu",
    },
    "update": {
        "enabled": False,
        "download_url": "",
    },
    "notice": {
        "enabled": False,
    },
    "buy_url": "",
    "community": {
        "group_url": "",        # 用户交流群链接，留空则不显示跳转行为
    },
}


def open_community_group():
    """打开用户交流群；未配置时静默跳过"""
    url = (APP_CONFIG.get("community") or {}).get("group_url") or ""
    if not url:
        return
    try:
        import webbrowser as _wb
        _wb.open(url)
    except Exception:
        pass


def _candidate_config_paths():
    """返回配置文件候选路径（按优先级）"""
    paths = []
    env_path = os.environ.get("LINGSHU_CONFIG")
    if env_path:
        paths.append(env_path)
    paths.append(os.path.join(APP_BASE_DIR, "config", "app_config.json"))
    # 冻结模式下 PyInstaller 把数据文件收进 _internal/，需一并查找
    try:
        if INTERNAL_RESOURCE_DIR and INTERNAL_RESOURCE_DIR != APP_BASE_DIR:
            paths.append(os.path.join(INTERNAL_RESOURCE_DIR, "config", "app_config.json"))
    except NameError:
        pass
    paths.append(os.path.join(BASE_DATA_DIR, "app_config.json"))
    return paths


def _deep_merge(base, override):
    """递归合并配置字典，override 优先"""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_app_config():
    """加载外部配置，返回 (config_dict, used_path_or_None)"""
    import json as _cfg_json
    for p in _candidate_config_paths():
        try:
            if p and os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as _f:
                    return _deep_merge(DEFAULT_APP_CONFIG, _cfg_json.load(_f)), p
        except Exception as _e:
            print(f"[灵枢] 配置文件读取失败，已忽略: {p} -> {_e}")
    return dict(DEFAULT_APP_CONFIG), None


APP_CONFIG, APP_CONFIG_PATH = load_app_config()
LICENSE_ENABLED = bool((APP_CONFIG.get("license") or {}).get("enabled", False))
'''

URL_BLOCK = '''# ========== 网络验证配置（灵枢：改为外部配置驱动） ==========
# 旧版把授权接口地址以 Base64 硬编码在源码里，导致「换品牌 = 改代码」。
# 灵枢改为从 config/app_config.json 读取；默认为空 + license.enabled=false，
# 即完全离线运行，不会访问任何第三方发卡平台。
_LICENSE_CFG = APP_CONFIG.get("license") or {}


def _cfg_str(key, default=""):
    v = _LICENSE_CFG.get(key, default)
    return (str(v) if v else default).strip().rstrip("/")


_PRIMARY_BASE = _cfg_str("api_base")
_BACKUP_BASE = _cfg_str("backup_api_base")
_PING_ENDPOINT = _LICENSE_CFG.get("ping_endpoint") or "/kami/ping"


def _root_of(url, cfg_key):
    """取 ping 探测根地址：配置显式给出时优先，否则由 api_base 推导 scheme://host"""
    explicit = _LICENSE_CFG.get(cfg_key) or ""
    if explicit:
        return str(explicit).strip().rstrip("/")
    if not url:
        return ""
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    except Exception:
        pass
    return ""


_PRIMARY_ROOT = _root_of(_PRIMARY_BASE, "ping_root")
_BACKUP_ROOT = _root_of(_BACKUP_BASE, "backup_ping_root")

# 当前生效的基础 URL（运行时可被切换到备用线路）
_current_api_base = _PRIMARY_BASE or _BACKUP_BASE
_dns_fallback_triggered = False  # 是否已触发切换（本次运行内只切一次）
_ping_probe_done = False  # 是否已完成启动探测
'''

SYS_PATH_BLOCK = '''
# [灵枢] 保证同目录模块（parse_rule / template_render）在源码运行模式下可导入
try:
    _LINGSHU_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:  # 某些冻结环境下 __file__ 不可用
    _LINGSHU_SRC_DIR = os.getcwd()
if _LINGSHU_SRC_DIR and _LINGSHU_SRC_DIR not in sys.path:
    sys.path.insert(0, _LINGSHU_SRC_DIR)
'''

SELF_IMPORT_COMMENT = "# [灵枢] SystemCamouflage 已在本模块定义，直接引用，避免自引用重复执行整个模块"

ANCHORS = {
    "sys.path": "os.environ['PYTHONUTF8'] = '1'",
    "config": 'EXPORT_HISTORY_FILE = os.path.join(BASE_DATA_DIR, "export_history.json")',
    "url_start": "# ========== 网络验证配置 ==========",
    "url_end": "_ping_probe_done = False  # 是否已完成启动探测",
    "heartbeat": "        if self._saved_card:\n"
                 "            self._heartbeat_timer.start(LICENSE_CHECK_INTERVAL * 1000)",
    "auth_gate": "    # 先显示卡密验证窗口\n"
                 "    auth_win = AuthWindow()\n"
                 "    if auth_win.exec() != QDialog.DialogCode.Accepted:\n"
                 "        sys.exit(0)",
    "update_url": 'UPDATE_DOWNLOAD_URL = "https://share.weiyun.com/nEKvbwQ3"',
    "buy_url": '_DEFAULT_BUY_URL = "https://m.tb.cn/h.Ru4DyVq?tk=T9v1g9Risvq"',
    "self_import": "from 灵枢 import SystemCamouflage",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """唯一锚点替换：出现次数不为 1 时报错"""
    cnt = text.count(old)
    if cnt != 1:
        raise RuntimeError(f"锚点[{label}]命中 {cnt} 次（期望 1 次），请检查源码版本: {old[:60]!r}")
    return text.replace(old, new)


def splice_block(text: str, start_marker: str, end_marker: str, new_block: str, label: str) -> str:
    """用 new_block 替换 [start_marker 所在行, end_marker 所在行] 之间的整段"""
    si = text.find(start_marker)
    if si < 0:
        raise RuntimeError(f"锚点[{label}]起始标记未找到: {start_marker!r}")
    line_start = text.rfind("\n", 0, si) + 1
    ei = text.find(end_marker, si)
    if ei < 0:
        raise RuntimeError(f"锚点[{label}]结束标记未找到: {end_marker!r}")
    line_end = text.find("\n", ei)
    if line_end < 0:
        line_end = len(text)
    else:
        line_end += 1
    return text[:line_start] + new_block + text[line_end:]


def transform(src_text: str) -> str:
    """执行全部重命名与补丁"""
    stats = {}

    # 1) 重命名
    for old, new in RENAMES:
        n = src_text.count(old)
        if n:
            src_text = src_text.replace(old, new)
            stats[f"rename:{old}"] = n

    # 2) sys.path 自举（保证源码模式可导入同目录模块）
    src_text = replace_once(
        src_text, ANCHORS["sys.path"], ANCHORS["sys.path"] + SYS_PATH_BLOCK, "sys.path")

    # 3) 注入外部配置加载器
    src_text = replace_once(
        src_text, ANCHORS["config"], ANCHORS["config"] + CONFIG_BLOCK, "config")

    # 4) 授权接口地址外部化
    src_text = splice_block(
        src_text, ANCHORS["url_start"], ANCHORS["url_end"], URL_BLOCK, "url")

    # 5) 心跳：关闭授权时不再发起
    src_text = replace_once(
        src_text,
        ANCHORS["heartbeat"],
        "        if LICENSE_ENABLED and self._saved_card:\n"
        "            self._heartbeat_timer.start(LICENSE_CHECK_INTERVAL * 1000)",
        "heartbeat")

    # 6) 启动门控：关闭授权时跳过授权窗
    src_text = replace_once(
        src_text,
        ANCHORS["auth_gate"],
        "    # 授权校验：由 config/app_config.json 的 license.enabled 控制\n"
        "    # 默认关闭（离线开发模式），直接进主界面；开启时走原版卡密验证流程。\n"
        "    if LICENSE_ENABLED:\n"
        "        auth_win = AuthWindow()\n"
        "        if auth_win.exec() != QDialog.DialogCode.Accepted:\n"
        "            sys.exit(0)\n"
        "    else:\n"
        "        print(\"[灵枢] 授权校验已关闭（license.enabled=false），直接进入主界面\")",
        "auth_gate")

    # 7) 更新/购买链接外部化
    src_text = replace_once(
        src_text,
        ANCHORS["update_url"],
        'UPDATE_DOWNLOAD_URL = (APP_CONFIG.get("update") or {}).get("download_url") or ""',
        "update_url")
    src_text = replace_once(
        src_text,
        ANCHORS["buy_url"],
        '_DEFAULT_BUY_URL = APP_CONFIG.get("buy_url") or ""',
        "buy_url")

    # 8) 社群链接外部化（旧版硬编码指向原产品 QQ 群）
    for _old in ('webbrowser.open("https://qm.qq.com/q/ZKhOhAF0cY")',
                 'webbrowser.open("https://qm.qq.com/q/cq2W5ZhNsI")'):
        if _old in src_text:
            src_text = src_text.replace(_old, "open_community_group()")
            stats[f"patch:{_old[:40]}"] = src_text.count("open_community_group()")

    # 9) 消除「自己 import 自己」：旧版在 __main__ 里 `from 道码灵境 import SystemCamouflage`，
    #    会把整个 58k 行模块二次执行一遍。改成直接引用模块级符号。
    n = src_text.count(ANCHORS["self_import"])
    if n < 1:
        raise RuntimeError("锚点[self_import]未找到")
    src_text = src_text.replace(ANCHORS["self_import"], SELF_IMPORT_COMMENT)
    stats["fix:self_import"] = n

    return src_text, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="把旧版单体源码迁移为灵枢工程源码")
    ap.add_argument("--source", default=DEFAULT_SOURCE_MAIN, help="旧版主源码路径")
    ap.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR, help="旧版辅助模块所在目录")
    ap.add_argument("--check", action="store_true", help="只校验锚点，不写出文件")
    args = ap.parse_args()

    with open(args.source, "r", encoding="utf-8") as f:
        src_text = f.read()

    out_text, stats = transform(src_text)

    print("== 迁移统计 ==")
    for k, v in sorted(stats.items()):
        print(f"  {k:<52} x{v}")
    print(f"  输出行数: {out_text.count(chr(10)) + 1}")

    if args.check:
        print("\n锚点校验通过，未写出文件（--check）。")
        return 0

    os.makedirs(SRC_PKG, exist_ok=True)
    main_out = os.path.join(SRC_PKG, "main.py")
    with open(main_out, "w", encoding="utf-8", newline="\n") as f:
        f.write(out_text)
    print(f"\n[写出] {main_out}")

    for mod in ("parse_rule.py", "template_render.py"):
        s = os.path.join(args.source_dir, mod)
        d = os.path.join(SRC_PKG, mod)
        if os.path.isfile(s):
            shutil.copyfile(s, d)
            print(f"[拷贝] {d}")
        else:
            print(f"[警告] 未找到辅助模块: {s}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
