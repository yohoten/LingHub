# -*- coding: utf-8 -*-
"""灵枢 LingHub —— Windows 桌面自动化编排平台

模块布局说明：
    main.py             主程序（含全部 UI 与执行引擎）
    parse_rule.py       自然语言 → 脚本规则解析
    template_render.py  脚本模板渲染

main.py 在源码模式下以脚本方式运行（__name__ == "__main__"），
因此本包不把 main 暴露为 API；入口见仓库根目录 run.py / pack_entry.py。
"""
__version__ = "2.6.0"
__app_name__ = "灵枢"
__app_code__ = "lingshu"
