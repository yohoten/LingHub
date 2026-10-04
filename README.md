# 灵枢 LingHub

Windows 桌面自动化编排平台。以「图色识别 + 键鼠模拟 + 流程编排」为核心，
把重复性桌面操作沉淀为可复用、可编排、可调度的自动化项目。

本项目由旧版单体程序（原品牌名「道码灵镜 / 道码灵境」）迁移而来，
完成品牌重命名与工程化改造，功能行为与原版保持一致。

---

## 1. 命名

| 项 | 旧 | 新 |
| --- | --- | --- |
| 中文名 | 道码灵镜 / 道码灵境（两个名字混用） | **灵枢** |
| 英文名 | DaomaLingjing | **LingHub** |
| 应用标识 | `dmlj` | `lingshu` |
| 用户数据目录 | `~/.daoma_spirit` | `~/.lingshu` |
| 单实例互斥体 | `DaoMaLingJing_SingleInstance_*` | `LingHub_SingleInstance_*` |

取名依据：「枢」为枢纽、中枢之意，对应本软件作为各类自动化能力调度中枢的定位；
舍弃旧名的玄学表述，避免「灵镜 / 灵境」两个异体字造成的品牌识别分裂。

---

## 2. 目录结构

```
lingshu/
├── run.py                     开发模式启动器
├── pack_entry.py              PyInstaller 打包入口
├── requirements.txt
├── config/
│   └── app_config.json        授权 / 更新 / 公告 / 购买链接配置
├── src/lingshu/
│   ├── main.py                主程序（58.7k 行，单体）
│   ├── parse_rule.py          自然语言 → 脚本规则解析
│   └── template_render.py     脚本模板渲染
├── build/
│   └── lingshu.spec           PyInstaller 打包配置
└── tools/
    └── bootstrap_from_legacy.py   旧版源码 → 本工程的迁移工具（可重复执行）
```

---

## 3. 快速开始

```bash
# 1) 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 2) 启动
.venv\Scripts\python run.py
```

首次启动为**离线开发模式**：不弹授权窗、不联网校验，直接进入主界面。

### 自检

```bash
.venv\Scripts\python tools\smoke_test.py
```

离屏模式下校验三层：主模块可导入、品牌与配置生效、主窗口可构造。
当前状态 9/9 通过。

---

## 4. 配置（`config/app_config.json`）

查找顺序（第一个命中的生效）：

1. 环境变量 `LINGSHU_CONFIG` 指向的文件
2. `<程序目录>/config/app_config.json`（打包后的推荐位置）
3. `~/.lingshu/app_config.json`
4. 内置默认值

```jsonc
{
  "license": {
    "enabled": false,          // true 时启用卡密验证 + 心跳
    "api_base": "",            // 例：https://your-domain.com/kami/qqXXXXXX
    "backup_api_base": "",
    "ping_endpoint": "/kami/ping",
    "app_id": "lingshu"
  },
  "update": { "enabled": false, "download_url": "" },
  "notice": { "enabled": false },
  "buy_url": ""
}
```

> 旧版把授权接口地址以 Base64 硬编码在源码中，换品牌就必须改代码。
> 灵枢改为配置驱动，默认留空 —— 不会访问任何第三方发卡平台。
> 需要启用商业授权时，填入自己的接口地址并把 `enabled` 置为 `true` 即可。

---

## 5. 打包

```bash
.venv\Scripts\python -m pip install pyinstaller
pyinstaller build/lingshu.spec --noconfirm --distpath dist --workpath build/.tmp
```

产物：`dist/LingHub/LingHub.exe`（onedir，约 181 MB）。分发时整个目录拷走。

冻结模式下的配置文件在 **`_internal/config/app_config.json`**
（PyInstaller 会把数据文件收进 `_internal/`，程序已同时查找这两个位置）。

已验证：PyInstaller 6.22.3 构建通过，`_internal/lingshu_src/` 含 main.py 与两个辅助模块。

> 瘦身提示：产物中 `cv2` 占 112 MB（含 30 MB 的 `opencv_videoio_ffmpeg`）。
> 若不需要视频读写，改用 `opencv-python-headless` 可直接省掉这 30 MB。

---

## 6. 相对旧版的改造清单

| # | 类别 | 改造 |
| --- | --- | --- |
| 1 | 品牌 | 全量重命名：中文名、应用标识、数据目录、临时文件前缀、注册表关键词、单实例互斥体 |
| 2 | 配置 | 授权/更新/公告/购买链接外部化为 `app_config.json`，默认离线 |
| 3 | 缺陷修复 | 消除 `from 道码灵境 import SystemCamouflage` 自引用 —— 旧版会在 `__main__` 中把 58k 行模块**二次完整执行**一遍 |
| 4 | 可运行性 | 源码模式 `sys.path` 自举，保证 `parse_rule` / `template_render` 可导入 |
| 5 | 工程化 | 新增 `run.py`（开发启动）、`pack_entry.py`（打包入口）、`.spec`、依赖清单、`.gitignore` |
| 6 | 可复现 | 迁移逻辑固化为 `tools/bootstrap_from_legacy.py`，锚点缺失即报错，不静默跳过 |
| 7 | 外链 | 两处原产品 QQ 群链接改为 `community.group_url` 配置项，留空即不跳转 |

### 已验证

| 项 | 结果 |
| --- | --- |
| 语法编译（`py_compile`） | 通过 |
| 冒烟测试 `tools/smoke_test.py` | 9/9 通过 |
| 离屏启动链路 | 跳过授权 → 主窗口「灵枢 当前版本: 2.6」→ 热键注册 → 事件循环 |
| PyInstaller 6.22.3 打包 | 构建成功，`dist/LingHub/`（181 MB） |

---

## 7. 已知待办

- [ ] 单体拆分：58.7k 行的 `main.py` 建议按职责拆为 `core/`、`ui/`、`dialogs/`、`device/`、`license/` 等子包
- [ ] 视觉资产仍沿用旧版太极 / 八卦图形（`get_bagua_icon`、`RotatingTaiChi`），品牌一致性待统一
- [ ] `community.group_url`、`buy_url` 仍为空，需填入自己的社群与购买页地址
- [ ] 部分依赖未在 `requirements.txt` 中声明（kmbox 硬件 SDK `kmNet`、Umi-OCR 外部程序），按需补充
- [ ] 无自动化测试；拆分前建议先对核心执行引擎补回归用例
# LingHub
