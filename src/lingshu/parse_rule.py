# -*- coding: utf-8 -*-
"""
自然语言规则解析模块
解析自然语言描述的自动化规则，转换为结构化配置
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ============ 所有动作类型 ============
ALL_ACTIONS = [
    # 鼠标动作
    "左键点击",
    "左键双击",
    "左键按下",
    "左键抬起",
    "右键点击",
    "右键双击",
    "右键按下",
    "右键抬起",
    "中键单击",
    "中键双击",
    "中键按下",
    "中键抬起",
    # 键盘动作
    "按按键",
    "按下按键",
    "释放按键",
    "长按按键",
    "输入文字",
    # 其他
    "无操作",
]

# 需要按键名称的动作
KEY_ACTIONS = [
    "按按键",
    "按下按键",
    "释放按键",
    "长按按键",
]


@dataclass
class RuleItem:
    """单条规则项"""
    target_text: str = ""           # 目标文字
    match_mode: str = "包含该文字"   # 匹配模式: 包含该文字 / 完全相等
    action_type: str = "左键点击"    # 动作类型
    key_name: str = ""              # 按键名称（键盘动作时使用）
    hold_time: float = 0.5          # 长按时间（秒）


@dataclass
class RuleConfig:
    """规则配置"""
    rules: List[RuleItem] = field(default_factory=list)
    interval: float = 1.0           # 轮询间隔（秒）
    cooldown: float = 0.0           # 冷却时间（秒）
    loop_mode: str = "继续循环"      # 循环模式: 继续循环 / 直接停止
    region: Optional[Tuple[int, int, int, int]] = None  # 识别区域 (x1, y1, x2, y2)


def parse_natural_language(text: str) -> Tuple[Optional[RuleConfig], Optional[str]]:
    """
    解析自然语言规则
    返回 (配置对象, 错误信息)
    """
    if not text or not text.strip():
        return None, "规则文本不能为空"

    cfg = RuleConfig()
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]

    for line in lines:
        rule, err = _parse_single_line(line)
        if err:
            return None, f"第「{line}」行解析失败: {err}"
        if rule:
            cfg.rules.append(rule)

    if not cfg.rules:
        return None, "未能解析出任何有效规则"

    return cfg, None


def _parse_single_line(line: str) -> Tuple[Optional[RuleItem], Optional[str]]:
    """解析单行规则"""
    item = RuleItem()

    # 尝试匹配常见模式："当出现XXX时，执行YYY"
    pattern = r'当[出现看到有]*(.+?)[时，,]*(?:则|就|执行|点击|按|按下|长按)?(.+)'
    match = re.search(pattern, line)
    if match:
        item.target_text = match.group(1).strip()
        action_str = match.group(2).strip()
        item.action_type, item.key_name, item.hold_time = _parse_action(action_str)
        item.match_mode = _detect_match_mode(item.target_text)
        return item, None

    # 尝试匹配："XXX -> YYY"
    pattern2 = r'(.+?)\s*[-=]>\s*(.+)'
    match2 = re.search(pattern2, line)
    if match2:
        item.target_text = match2.group(1).strip()
        action_str = match2.group(2).strip()
        item.action_type, item.key_name, item.hold_time = _parse_action(action_str)
        item.match_mode = _detect_match_mode(item.target_text)
        return item, None

    # 简化模式：只给文字，默认左键点击
    if line and not any(kw in line for kw in ['时', '则', '就', '执行']):
        item.target_text = line.strip()
        item.action_type = "左键点击"
        item.match_mode = "包含该文字"
        return item, None

    return None, "无法识别的规则格式"


def _parse_action(action_str: str) -> Tuple[str, str, float]:
    """解析动作描述，返回 (动作类型, 按键名, 长按时间)"""
    action_str = action_str.strip()
    hold_time = 0.5

    # 长按按键
    m = re.search(r'长按(?:按键)?\s*(\S+)(?:\s*(\d+(?:\.\d+)?)\s*秒?)?', action_str)
    if m:
        key = m.group(1)
        if m.group(2):
            hold_time = float(m.group(2))
        return "长按按键", key, hold_time

    # 按下按键
    m = re.search(r'按下(?:按键)?\s*(\S+)', action_str)
    if m:
        return "按下按键", m.group(1), hold_time

    # 释放按键
    m = re.search(r'释放(?:按键)?\s*(\S+)', action_str)
    if m:
        return "释放按键", m.group(1), hold_time

    # 按按键
    m = re.search(r'按(?:键)?\s*(\S+)', action_str)
    if m:
        return "按按键", m.group(1), hold_time

    # 输入文字
    m = re.search(r'输入(?:文字)?\s*["「](.+)["」]', action_str)
    if m:
        return "输入文字", m.group(1), hold_time

    # 鼠标动作
    if '左键双击' in action_str or '左双击' in action_str:
        return "左键双击", "", hold_time
    if '左键点击' in action_str or '点击' in action_str or '单击' in action_str:
        return "左键点击", "", hold_time
    if '左键按下' in action_str:
        return "左键按下", "", hold_time
    if '左键抬起' in action_str:
        return "左键抬起", "", hold_time
    if '右键双击' in action_str or '右双击' in action_str:
        return "右键双击", "", hold_time
    if '右键点击' in action_str or '右键' in action_str:
        return "右键点击", "", hold_time
    if '右键按下' in action_str:
        return "右键按下", "", hold_time
    if '右键抬起' in action_str:
        return "右键抬起", "", hold_time
    if '中键' in action_str:
        return "中键单击", "", hold_time

    # 默认左键点击
    return "左键点击", "", hold_time


def _detect_match_mode(text: str) -> str:
    """根据目标文字检测匹配模式"""
    if text.startswith('=') or text.startswith('=='):
        return "完全相等"
    return "包含该文字"
