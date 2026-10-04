# -*- coding: utf-8 -*-
"""
脚本模板渲染模块
根据规则配置生成可执行的 Python 脚本代码
"""

import textwrap
from parse_rule import RuleConfig, RuleItem


def render_python_code(cfg: RuleConfig) -> str:
    """根据规则配置生成 Python 脚本代码"""
    rules_code = []
    for i, rule in enumerate(cfg.rules):
        rules_code.append(_render_single_rule(rule, i))

    region_str = str(cfg.region) if cfg.region else "None"

    code = f'''# -*- coding: utf-8 -*-
"""
文字识别自动执行脚本
由 道码灵镜 自动生成
"""

import time
import sys
import os

# 确保能找到主程序模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import ImageGrab
import io
import base64
import requests

# ========== 配置 ==========
INTERVAL = {cfg.interval}        # 轮询间隔（秒）
COOLDOWN = {cfg.cooldown}        # 冷却时间（秒）
LOOP_MODE = "{cfg.loop_mode}"    # 循环模式
REGION = {region_str}            # 识别区域

# ========== OCR 配置 ==========
OCR_URL = "http://127.0.0.1:1224/api/ocr"

def ocr_screen(region=None):
    """调用 Umi-OCR 进行屏幕文字识别"""
    try:
        img = ImageGrab.grab(bbox=region) if region else ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        resp = requests.post(
            OCR_URL,
            json={{"base64": b64, "options": {{"data.format": "dict"}}}},
            timeout=15,
            proxies={{"http": None, "https": None}},
        )
        resp.raise_for_status()
        res = resp.json()
        items = res.get("data") if (res.get("code") == 100 and isinstance(res.get("data"), list)) else []
        return [(it.get("text") or "").strip() for it in items if (it.get("text") or "").strip()]
    except Exception as e:
        print(f"OCR 识别失败: {{e}}")
        return []


def match_text(texts, target, mode):
    """检查是否匹配目标文字"""
    for text in texts:
        if mode == "完全相等":
            if text == target:
                return True
        else:  # 包含该文字
            if target in text:
                return True
    return False


def execute_action(rule):
    """执行规则动作"""
    action = rule["action_type"]
    key = rule.get("key_name", "")
    hold = rule.get("hold_time", 0.5)
    
    print(f"  执行动作: {{action}} {{key}}")
    
    # 这里是动作执行的占位符
    # 实际运行时由主程序的脚本引擎处理
    pass


# ========== 规则定义 ==========
RULES = [
{chr(10).join("    " + r for r in rules_code)}
]

# ========== 主循环 ==========
def main():
    print("道码灵镜 - 文字识别自动执行")
    print(f"共 {{len(RULES)}} 条规则，间隔 {{INTERVAL}}s")
    
    last_trigger = 0
    
    while True:
        try:
            texts = ocr_screen(REGION)
            if not texts:
                time.sleep(INTERVAL)
                continue
            
            triggered = False
            for rule in RULES:
                if match_text(texts, rule["target_text"], rule["match_mode"]):
                    now = time.time()
                    if now - last_trigger < COOLDOWN:
                        continue
                    
                    print(f"匹配到: {{rule['target_text']}}")
                    execute_action(rule)
                    last_trigger = now
                    triggered = True
                    
                    if LOOP_MODE == "直接停止":
                        print("触发停止模式，脚本结束")
                        return
                    
                    break
            
            time.sleep(INTERVAL)
            
        except KeyboardInterrupt:
            print("\\n用户中断，脚本结束")
            return
        except Exception as e:
            print(f"运行错误: {{e}}")
            time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
'''
    return code


def _render_single_rule(rule: RuleItem, index: int) -> str:
    """渲染单条规则为字典定义"""
    return f'''{{
        "target_text": {repr(rule.target_text)},
        "match_mode": "{rule.match_mode}",
        "action_type": "{rule.action_type}",
        "key_name": {repr(rule.key_name)},
        "hold_time": {rule.hold_time},
    }},'''
