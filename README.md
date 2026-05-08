# 划词翻译

Windows 全局划词 AI 翻译工具 — 任意位置选中文字，光标旁弹出翻译。

## 功能

- 选中文字 → 光标旁出现图标 → 悬停图标展开翻译浮窗
- 流式翻译，逐字显示
- 中英双语互译（专有名词附带全称解释）
- SQLite 本地缓存，重复文字瞬间出结果
- 浮窗内二次划选翻译
- 托盘常驻，右键菜单开关/设置/退出

## 安装

Windows，Python 3.10+。

```bash
git clone https://github.com/Ottavia-Luca/global-highlight-AI-translator.git
cd global-highlight-AI-translator
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env`，填入 API Key：

```
DEEPSEEK_API_KEY=sk-your-api-key-here
```

其余配置（API URL、模型、提示词、缓存大小等）可在 `.env` 中按需修改，也可通过托盘右键 → 设置界面修改。

## 使用

```bash
python main.py
```

托盘出现绿色图标表示已开启。右键托盘图标可开关或退出。

1. 在任意位置选中文字
2. 光标旁出现小图标
3. 鼠标悬停图标 → 弹出翻译浮窗
4. 可复制翻译结果或收藏

## 项目结构

```
├── main.py                 # 入口
├── .env.example            # 配置模板
├── requirements.txt
├── core/
│   ├── config.py           # 配置读取（.env 热重载）
│   ├── cache.py            # SQLite 翻译缓存
│   ├── translator.py       # DeepSeek API 流式调用
│   └── text_detector.py    # 鼠标钩子 + 剪贴板取词
├── ui/
│   ├── overlay_icon.py     # 光标旁悬浮图标
│   ├── float_window.py     # 翻译结果浮窗
│   ├── tray.py             # 系统托盘
│   └── settings_dialog.py  # 设置对话框
└── assets/                 # 图标资源（启动时自动生成）
```
