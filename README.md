# Global Highlight AI Translator

全局划词 AI 翻译工具 — 在 Windows 任何位置选中文字，AI 即时翻译。

## 功能

- 选中文字后光标旁弹出小图标
- 鼠标悬停图标展开翻译浮窗
- 自动检测中英文互译
- DeepSeek API 流式翻译
- SQLite 本地缓存，重复文字瞬间出结果
- 系统托盘常驻，全局热键 Ctrl+Shift+F8 开关
- 全屏游戏下也能正常弹出，不抢焦点

## 安装

需要 Windows，Python 3.10+。

```bash
git clone <repo-url>
cd global-highlight-AI-translator
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml`，填入 DeepSeek API Key：

```yaml
api:
  key: "sk-your-api-key-here"
```

其他可选项（模型、提示词、缓存大小、快捷键等）见配置文件注释。

## 使用

```bash
python main.py
```

程序启动后托盘出现绿色图标，表示划词翻译已开启。

1. 在任意位置选中文字
2. 光标旁出现小图标
3. 鼠标移到图标上 → 弹出翻译浮窗
4. 可复制翻译结果或收藏

## 项目结构

```
├── main.py                 # 入口
├── config.yaml             # 用户配置
├── core/
│   ├── config.py           # 配置加载/热重载
│   ├── cache.py            # SQLite 翻译缓存
│   ├── translator.py       # DeepSeek API 流式调用
│   └── text_detector.py    # 鼠标钩子 + UI Automation
├── ui/
│   ├── overlay_icon.py     # 光标旁小图标
│   ├── float_window.py     # 翻译结果浮窗
│   ├── tray.py             # 系统托盘
│   └── settings_dialog.py  # 设置对话框
├── tests/                  # 测试
└── assets/                 # 图标资源（自动生成）
```

## 开发

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests/ -v
```
