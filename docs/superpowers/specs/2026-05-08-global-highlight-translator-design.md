# 全局划词 AI 翻译工具 — 设计文档

**日期:** 2026-05-08
**状态:** 草案

## 概述

一个 Windows 原生系统托盘应用。在屏幕任何位置选中文字后，鼠标旁弹出小图标，鼠标悬停时展开浮窗显示 AI 翻译结果。使用 DeepSeek API 进行翻译，SQLite 做本地缓存。

## 需求

### 功能性
- 在 Windows 任何位置检测文字选中，包括全屏游戏
- 选中文字后在鼠标附近显示 24×24 小图标
- 鼠标悬停小图标 200ms 后展开翻译浮窗（360×240）
- 自动检测源语言：英文→中文，中文→英文
- 可配置系统提示词，支持专有名词自定义翻译风格（如 CNN → "全称是 Convolutional Neural Network（卷积神经网络）"）
- SQLite 缓存，PRIMARY KEY B-tree 索引，O(log n) 查询
- 系统托盘常驻，左键单击或 Ctrl+Shift+F8 开关划词
- 托盘图标颜色指示状态：绿色（开启）/ 灰色（关闭）
- 翻译结果流式逐字显示
- 浮窗底栏提供复制和收藏按钮

### 非功能性
- 浮窗不抢焦点（WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW）
- 浮窗显示在全屏游戏之上（WS_EX_TOPMOST）
- 鼠标钩子不影响系统或游戏性能
- 所有错误静默处理，不弹对话框
- 配置文件修改后自动热加载
- 冷启动 < 2s，悬停展开 < 50ms，首个 token 显示 < 500ms

## 架构

```
主进程（系统托盘常驻）
├── core/
│   ├── text_detector.py    — 鼠标钩子 + UI Automation 文字检测
│   ├── translator.py        — DeepSeek API 异步流式调用
│   ├── cache.py             — SQLite B-tree 索引缓存
│   └── config.py            — YAML 配置加载 / 热重载
├── ui/
│   ├── overlay_icon.py      — 鼠标旁小图标窗口
│   ├── float_window.py      — 翻译结果浮窗
│   ├── tray.py              — 系统托盘图标 + 右键菜单
│   └── settings_dialog.py   — 设置对话框
└── main.py                  — 入口，组装所有模块
```

### 数据流

```
鼠标左键松开 → （100ms 去抖动） → UI Automation 读取选中文字
  → 文字非空/非纯数字/非纯符号/不超过2000字符？
    → 查 SQLite 缓存（PRIMARY KEY B-tree 索引，O(log n)）
      → 命中缓存？ → 浮窗直接显示翻译结果
      → 未命中？ → 异步 POST DeepSeek API → 流式输出到浮窗 → 写入缓存
```

## 组件说明

### 1. 文字检测器 (`core/text_detector.py`)

- 通过 `ctypes` 调用 `user32.dll` 注册底层鼠标钩子（`WH_MOUSE_LL`）
- 左键松开后等待 100ms 去抖动，再通过 UI Automation 读取焦点元素的选中文本
- 过滤规则：忽略空文本、纯数字、纯符号；超过 2000 字符截断
- 检测到有效文字后通过 Qt 信号发出

### 2. 翻译服务 (`core/translator.py`)

- 异步 HTTP 客户端（`aiohttp`）运行在 `QThread` 中
- 向 `https://api.deepseek.com/v1/chat/completions` 发送 POST 请求
- OpenAI 兼容格式，附带配置中的自定义系统提示词
- SSE 流式解析响应，逐 token 发送到浮窗
- 超时 10s；429/5xx 错误静默重试 1 次

### 3. 缓存 (`core/cache.py`)

- SQLite 数据库，文件路径 `data/cache.db`，首次运行自动创建
- 单表结构：`translations(source_text TEXT PRIMARY KEY, translated_text TEXT, created_at TIMESTAMP)`
- PRIMARY KEY 自带 B-tree 索引，保证 O(log n) 查询
- `max_entries`（默认 10000）和 `ttl_days`（默认 30 天）自动清理旧数据
- PRAGMA journal_mode=WAL 提升并发读性能

### 4. 配置管理 (`core/config.py`)

- 读取用户配置目录下的 `config.yaml`
- 通过 `QFileSystemWatcher` 监听文件变更，自动热加载
- 提供类型化的配置访问接口

### 5. 悬浮图标 (`ui/overlay_icon.py`)

- 无边框小 `QWidget`（24×24），检测到文字后在鼠标附近显示
- Qt 标志：`FramelessWindowHint | Tool | WindowStaysOnTopHint`
- Win32 扩展标志：`WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT`
- 监测鼠标进入/离开；鼠标悬停 200ms 后发出展开信号

### 6. 翻译浮窗 (`ui/float_window.py`)

- 360×240 无边框 `QWidget`，圆角 + 阴影
- 与悬浮图标同样的不抢焦点窗口标志
- 顶部：原文灰色小字显示
- 中部：翻译结果，流式逐字更新
- 底部操作栏：复制按钮（写入剪贴板）、收藏按钮（存入 SQLite）
- 鼠标离开 500ms 后自动隐藏
- 等待首个 token 时显示加载动画

### 7. 系统托盘 (`ui/tray.py`)

- `QSystemTrayIcon`，两套图标：绿色（开启）/ 灰色（关闭）
- 左键单击：切换开关状态
- 右键菜单：开关、设置、关于、退出
- 通过 `RegisterHotKey` 注册全局快捷键 `Ctrl+Shift+F8`

### 8. 设置对话框 (`ui/settings_dialog.py`)

- 简单 `QDialog`：API Key 输入框、系统提示词编辑器、缓存大小、快捷键自定义
- 点击应用后写入 `config.yaml`，配置模块自动热加载

## 配置文件

```yaml
api:
  url: "https://api.deepseek.com/v1/chat/completions"
  key: "sk-your-api-key"
  model: "deepseek-v4-flash"
  timeout: 10
  max_tokens: 512

translation:
  auto_detect: true
  fallback_source: "en"
  fallback_target: "zh"

system_prompt: |
  你是一个翻译助手。翻译用户输入的文本。
  规则：
  1. 如果源语言是英文，翻译成中文；如果源语言是中文，翻译成英文
  2. 遇到专有名词缩写（如CNN、RNN、API），以"全称是 XXX（YYY）"格式输出
  3. 保持专业术语的准确性
  4. 简洁输出，不要额外解释

hotkeys:
  toggle: "Ctrl+Shift+F8"

cache:
  max_entries: 10000
  ttl_days: 30

ui:
  icon_size: 24
  float_window_width: 360
  float_window_max_height: 240
  hover_delay: 200
```

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| API Key 未配置/无效 | 托盘图标显示警告状态，不发起请求 |
| API 超时（>10s） | 静默放弃 |
| API 错误（429/5xx） | 静默重试 1 次，仍失败则放弃 |
| 网络断开 | 静默降级，仅使用本地缓存 |
| 选中纯数字/纯符号/空文本 | 直接忽略 |
| 选中内容 > 2000 字符 | 截断至前 2000 字符 |
| DeepSeek 返回空/格式异常 | 静默忽略 |
| SQLite 文件损坏 | 删除重建，从零开始 |

## 依赖

```
PyQt6>=6.5
aiohttp>=3.9
pyyaml>=6.0
comtypes>=1.4
```

## 项目结构

```
global-highlight-translator/
├── main.py
├── config.yaml
├── requirements.txt
├── README.md
├── core/
│   ├── __init__.py
│   ├── text_detector.py
│   ├── translator.py
│   ├── cache.py
│   └── config.py
├── ui/
│   ├── __init__.py
│   ├── overlay_icon.py
│   ├── float_window.py
│   ├── tray.py
│   └── settings_dialog.py
├── assets/
│   ├── icon_on.ico
│   ├── icon_off.ico
│   └── overlay_icon.png
└── data/
    └── cache.db              # 自动创建
```
