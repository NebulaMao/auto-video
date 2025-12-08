# AutoVideo - 自动化宣传视频生成工具

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-alpha-orange)

基于AI技术的自动化宣传视频生成系统，通过大语言模型、语音合成、语音识别和视频编辑技术，自动创建高质量的宣传视频。

[快速开始](#-快速开始) • [功能特性](#-主要特性) • [文档](#-文档) • [常见问题](#-常见问题)

</div>

---

## 📑 目录

- [项目简介](#-项目简介)
- [主要特性](#-主要特性)
- [系统要求](#-系统要求)
- [快速开始](#-快速开始)
- [安装指南](#-安装指南)
- [配置指南](#-配置指南)
- [使用指南](#-使用指南)
- [项目结构](#-项目结构)
- [功能模块](#-功能模块)
- [常见问题](#-常见问题)
- [开发指南](#-开发指南)
- [路线图](#-路线图)
- [许可证](#-许可证)
- [致谢](#-致谢)

---

## 📝 项目简介

AutoVideo是一个基于AI技术的自动化宣传视频生成工具，旨在简化视频制作流程。通过整合多种先进的AI技术，AutoVideo能够：

- 📝 **智能脚本生成**：利用DeepSeek大语言模型自动生成视频脚本
- 🎙️ **语音合成**：使用Edge-TTS生成自然流畅的中文配音
- 🎬 **智能剪辑**：基于语义理解自动匹配和剪辑素材
- 📊 **字幕渲染**：自动生成精美的同步字幕
- 🖥️ **Web界面**：提供友好的Gradio Web界面，无需编程即可使用

该项目适合需要快速生成产品宣传片、教程视频、新闻视频等场景的用户。

---

## ✨ 主要特性

### 🤖 AI驱动的内容生成
- **DeepSeek LLM集成**：支持使用DeepSeek API进行智能脚本生成和内容优化
- **语义素材匹配**：基于Sentence-Transformers的语义相似度搜索，智能匹配最合适的素材
- **上下文理解**：理解视频主题，生成连贯的脚本和解说词

### 🎙️ 专业语音合成
- **多引擎支持**：支持Edge-TTS、PyTTSx3等多种TTS引擎
- **中文优化**：特别优化的中文语音合成，支持多种音色
- **语音参数调节**：可调节语速、音量、音调等参数

### 🎬 智能视频编辑
- **自动剪辑**：根据脚本时长自动剪辑素材
- **转场效果**：支持多种转场效果（淡入淡出、交叉溶解等）
- **多轨合成**：支持视频、音频、字幕多轨道合成
- **高质量输出**：支持1080p/4K分辨率，H.264/H.265编码

### 📊 专业字幕系统
- **Whisper集成**：使用OpenAI Whisper进行精确的语音识别
- **样式定制**：支持字体、颜色、位置、描边等全面定制
- **自动同步**：字幕与语音自动同步，确保准确性
- **多语言支持**：支持中英文等多语言字幕

### 🖥️ 友好的用户界面
- **Gradio Web界面**：直观的图形化操作界面
- **实时预览**：支持素材预览和效果预览
- **进度追踪**：实时显示生成进度和状态
- **批量处理**：支持批量生成多个视频

---

## 🔧 系统要求

### 硬件要求
- **CPU**：建议4核或以上
- **内存**：建议8GB或以上（16GB更佳）
- **显卡**：
  - 可选GPU加速（NVIDIA显卡，支持CUDA）
  - CPU模式下也可运行，但速度较慢
- **存储**：至少10GB可用空间（用于模型和素材）

### 软件要求
- **操作系统**：
  - Windows 10/11 ✅
  - macOS 10.15+ ✅
  - Linux（Ubuntu 20.04+） ✅
- **Python**：3.10 或更高版本
- **FFmpeg**：必须安装（用于视频处理）

### 依赖的外部服务
- **DeepSeek API**：需要有效的API密钥（可在[DeepSeek官网](https://platform.deepseek.com)申请）
- **网络连接**：用于下载模型和调用API

---

## 🚀 快速开始

### 第一步：克隆项目
```bash
git clone https://github.com/yourusername/autovideo.git
cd autovideo
```

### 第二步：安装FFmpeg

**Windows用户**：
```bash
# 使用Chocolatey安装
choco install ffmpeg

# 或者手动下载
# 1. 访问 https://www.gyan.dev/ffmpeg/builds/
# 2. 下载 ffmpeg-release-full.7z
# 3. 解压并添加到系统PATH
```

**macOS用户**：
```bash
brew install ffmpeg
```

**Linux用户**：
```bash
sudo apt update
sudo apt install ffmpeg
```

### 第三步：安装Python依赖

**基础安装**：
```bash
pip install -e .

# 或使用国内镜像加速
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**GPU加速安装（可选，推荐）**：

如果你有NVIDIA GPU，可以启用GPU加速以提高处理速度：

1. 先安装项目基础依赖：
   ```bash
   pip install -e .
   ```

2. 卸载CPU版本的PyTorch：
   ```bash
   pip uninstall torch torchvision torchaudio
   ```

3. 访问 [PyTorch官网](https://pytorch.org/get-started/locally/) 选择适合你的CUDA版本并安装GPU版本：
   ```bash
   # CUDA 11.8 示例
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

4. 验证GPU可用性：
   ```bash
   python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}')"
   ```

### 第四步：配置文件
```bash
# 复制示例配置文件
copy config.toml.example config.toml  # Windows
# 或
cp config.toml.example config.toml    # macOS/Linux

# 编辑配置文件，填入你的DeepSeek API密钥
# 使用记事本或任何文本编辑器打开 config.toml
notepad config.toml  # Windows
```

在配置文件中，至少需要修改：
```toml
[llm]
api_key = "your-actual-deepseek-api-key"  # 替换为你的真实API密钥
```

### 第五步：运行程序

**启动Web界面**：
```bash
python main.py
```

然后在浏览器中打开：http://127.0.0.1:7860

**命令行模式**（即将支持）：
```bash
python main.py --mode cli --topic "产品介绍" --duration 60
```

---

## 📦 安装指南

### 详细安装步骤

#### 1. 准备Python环境

**检查Python版本**：
```bash
python --version
# 应显示 Python 3.10.x 或更高
```

**创建虚拟环境（推荐）**：
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

#### 2. 安装依赖包

**标准安装**：
```bash
pip install -e .
```

**开发者安装**（包含开发工具）：
```bash
pip install -e ".[dev]"
```

**GPU加速安装**（需要NVIDIA GPU和CUDA）：

⚠️ **重要提示**：由于PEP 508规范限制，PyTorch的CUDA版本需要单独安装。

1. **先安装项目基础依赖**：
   ```bash
   pip install -e .
   ```

2. **卸载CPU版本的PyTorch**：
   ```bash
   pip uninstall torch torchvision torchaudio
   ```

3. **访问PyTorch官网选择适合的CUDA版本**：
   - 打开 [PyTorch官网](https://pytorch.org/get-started/locally/)
   - 选择你的操作系统、包管理器和CUDA版本
   - 复制官网提供的安装命令

4. **安装GPU版本的PyTorch**：
   ```bash
   # CUDA 11.8 示例（请根据你的CUDA版本调整）
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # CUDA 12.1 示例
   # pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

5. **验证GPU安装**：
   ```bash
   python -c "import torch; print(f'PyTorch版本: {torch.__version__}'); print(f'CUDA可用: {torch.cuda.is_available()}')"
   ```

#### 3. 验证安装

创建测试脚本 [`test_install.py`](test_install.py):
```python
import sys
print(f"Python版本: {sys.version}")

# 测试关键依赖
try:
    import torch
    print(f"PyTorch版本: {torch.__version__}")
    print(f"CUDA可用: {torch.cuda.is_available()}")
except ImportError:
    print("PyTorch未安装")

try:
    import whisper
    print("Whisper已安装 ✓")
except ImportError:
    print("Whisper未安装")

try:
    import gradio
    print("Gradio已安装 ✓")
except ImportError:
    print("Gradio未安装")

try:
    import moviepy
    print("MoviePy已安装 ✓")
except ImportError:
    print("MoviePy未安装")

print("\n安装验证完成！")
```

运行测试：
```bash
python test_install.py
```

#### 4. 下载Whisper模型（可选）

首次使用Whisper时会自动下载，但也可以预先下载：
```bash
python -c "import whisper; whisper.load_model('base')"
```

---

## ⚙️ 配置指南

AutoVideo使用TOML格式的配置文件 [`config.toml`](config.toml:1)，所有配置项都有详细注释。

### 核心配置项说明

#### 1. LLM配置（必需）
```toml
[llm]
api_key = "sk-xxxxx"              # ⚠️ 必填：你的DeepSeek API密钥
base_url = "https://api.deepseek.com"  # API基础URL
model = "deepseek-chat"           # 模型名称
max_tokens = 4000                 # 最大生成token数
temperature = 0.7                 # 生成温度(0-1)，越高越有创意
timeout = 30                      # API请求超时时间(秒)
```

**如何获取API密钥**：
1. 访问[DeepSeek平台](https://platform.deepseek.com)
2. 注册并登录
3. 进入"API Keys"页面
4. 点击"创建新密钥"
5. 复制密钥并填入配置文件

#### 2. TTS语音合成配置

**Edge TTS（默认）**：
```toml
[tts]
engine = "edge-tts"               # TTS引擎
voice = "zh-CN-XiaoxiaoNeural"   # 语音名称（中文女声）
rate = 1.0                        # 语速倍率(0.5-2.0)
volume = 1.0                      # 音量(0.0-2.0)
pitch = 0                         # 音调偏移(-100到100)
```

**可用的中文语音**：
- `zh-CN-XiaoxiaoNeural`：温柔女声（推荐）
- `zh-CN-YunxiNeural`：平和男声
- `zh-CN-YunyangNeural`：专业男声
- `zh-CN-XiaoyiNeural`：活泼女声

**SiliconFlow TTS（推荐）**：
```toml
[tts]
engine = "siliconflow"            # TTS引擎

[siliconflow_tts]
api_key = "your-api-key-here"     # SiliconFlow API密钥
model = "fnlp/MOSS-TTSD-v0.5"     # 模型名称
voice = "fnlp/MOSS-TTSD-v0.5:alex" # 语音名称
speed = 1.0                        # 语速倍率(0.25-4.0)
gain = 0                           # 音量增益(-10到10)
response_format = "mp3"            # 输出格式
```

**SiliconFlow 可用语音**：
- `fnlp/MOSS-TTSD-v0.5:alex`：Alex 男声
- `fnlp/MOSS-TTSD-v0.5:emma`：Emma 女声
- `fnlp/MOSS-TTSD-v0.5:brian`：Brian 英文男声
- `fnlp/MOSS-TTSD-v0.5:alice`：Alice 英文女声

**SiliconFlow 优势**：
- 支持中英双语合成
- 更自然的语音质量
- 可调节语速范围更广（0.25-4.0）
- 支持音量增益调节
- 基于 MOSS-TTSD 模型

**如何获取 SiliconFlow API Key**：
1. 访问 [SiliconFlow 官网](https://siliconflow.cn)
2. 注册并登录账户
3. 进入控制台 → API Keys
4. 创建新的 API Key
5. 复制密钥到配置文件中

#### 3. Whisper语音识别配置
```toml
[whisper]
model_size = "base"               # 模型大小
language = "zh"                   # 识别语言
device = "auto"                   # 计算设备
```

**模型大小选择**：
| 模型 | 参数量 | 内存需求 | 速度 | 准确度 |
|------|--------|----------|------|--------|
| tiny | 39M | ~1GB | 最快 | 较低 |
| base | 74M | ~1GB | 快 | 中等 |
| small | 244M | ~2GB | 中 | 良好 |
| medium | 769M | ~5GB | 慢 | 很好 |
| large | 1550M | ~10GB | 最慢 | 最佳 |

#### 4. 视频处理配置
```toml
[video]
resolution = [1920, 1080]         # 分辨率[宽, 高]
fps = 30                          # 帧率
codec = "libx264"                 # 视频编码器
bitrate = "2000k"                 # 视频比特率
audio_codec = "aac"               # 音频编码器
audio_bitrate = "128k"            # 音频比特率
format = "mp4"                    # 输出格式
```

**分辨率预设**：
- `[1280, 720]`：720p（快速，文件小）
- `[1920, 1080]`：1080p（推荐，质量好）
- `[2560, 1440]`：2K（高质量）
- `[3840, 2160]`：4K（超高质量，慢）

#### 5. 字幕样式配置
```toml
[subtitle]
font_family = "SimHei"            # 字体（黑体）
font_size = 36                    # 字体大小
font_color = "#FFFFFF"            # 字体颜色（白色）
background_color = "#000000"      # 背景颜色（黑色）
background_alpha = 0.7            # 背景透明度
position = "bottom"               # 位置：top, center, bottom
margin = 50                       # 边距(像素)
alignment = "center"              # 对齐：left, center, right
outline_color = "#000000"         # 描边颜色
outline_width = 2                 # 描边宽度
```

#### 6. 路径配置
```toml
[paths]
materials_dir = "./data/materials"    # 素材库目录
output_dir = "./data/output"          # 输出目录
temp_dir = "./data/temp"              # 临时文件目录
fonts_dir = "./assets/fonts"          # 字体文件目录
templates_dir = "./assets/templates"  # 模板目录
```

#### 7. Gradio界面配置
```toml
[ui]
title = "AutoVideo - 自动化宣传视频生成系统"
description = "基于AI技术的自动化宣传视频生成工具"
theme = "default"                 # 界面主题
share = false                     # 是否生成公共链接
server_port = 7860                # 服务端口
server_name = "127.0.0.1"         # 服务地址
```

**开启外部访问**：
```toml
server_name = "0.0.0.0"  # 允许局域网访问
share = true             # 生成公网访问链接（需要gradio服务）
```

---

## 🎯 使用指南

### Web界面使用

#### 1. 启动应用
```bash
python main.py
```

启动成功后会显示：
```
Running on local URL:  http://127.0.0.1:7860
```

#### 2. 访问界面
在浏览器中打开显示的URL。

#### 3. 操作步骤

**步骤1：输入视频主题**
- 在"视频主题"文本框中输入你想制作的视频主题
- 例如："介绍我们的智能手表产品"

**步骤2：设置视频参数**
- **时长**：选择视频时长（30秒、60秒、90秒等）
- **风格**：选择视频风格（专业、活泼、简约等）
- **语音**：选择配音音色

**步骤3：上传素材（可选）**
- 点击"上传素材"按钮
- 支持视频（.mp4, .avi, .mov）和图片（.jpg, .png）
- 系统会自动分析和匹配素材

**步骤4：生成视频**
- 点击"生成视频"按钮
- 等待处理完成（通常需要2-5分钟）
- 进度条会显示当前处理状态

**步骤5：预览和下载**
- 生成完成后可以在线预览
- 点击"下载"按钮保存视频

### 命令行使用（高级）

虽然当前版本主要通过Web界面使用，但也可以通过Python脚本调用：

```python
from src.core.config import load_config
from src.modules.llm_client import LLMClient
from src.modules.tts_engine import TTSEngine
from src.modules.video_editor import VideoEditor

# 加载配置
config = load_config("config.toml")

# 生成脚本
llm = LLMClient(config.llm)
script = llm.generate_script(topic="产品介绍", duration=60)

# 生成语音
tts = TTSEngine(config.tts)
audio_path = tts.synthesize(script.text)

# 生成视频
editor = VideoEditor(config.video)
video_path = editor.create_video(
    audio_path=audio_path,
    materials=["path/to/video1.mp4", "path/to/image1.jpg"],
    script=script
)

print(f"视频已生成：{video_path}")
```

### 常用操作技巧

#### 提高生成质量
1. **提供详细的主题描述**：越详细越好
2. **上传相关素材**：使用高质量的素材
3. **调整温度参数**：在config.toml中调整temperature

#### 加快生成速度
1. **使用较小的Whisper模型**：如`tiny`或`base`
2. **降低视频分辨率**：如使用720p
3. **使用GPU加速**：安装CUDA和GPU版PyTorch

#### 素材管理
- 将素材放在[`./data/materials/`](data/materials)目录下
- 视频素材：`./data/materials/videos/`
- 图片素材：`./data/materials/images/`
- 音频素材：`./data/materials/audio/`

---

## 📁 项目结构

```
autovideo/
├── README.md                 # 项目说明文档
├── config.toml              # 配置文件
├── config.toml.example      # 配置文件示例
├── pyproject.toml           # Python项目配置
├── main.py                  # 主程序入口
├── .gitignore              # Git忽略文件
│
├── src/                    # 源代码目录
│   ├── __init__.py
│   ├── core/               # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py       # 配置管理
│   │   ├── logger.py       # 日志系统
│   │   └── exceptions.py   # 异常定义
│   │
│   ├── modules/            # 功能模块
│   │   ├── __init__.py
│   │   ├── llm_client.py          # LLM客户端
│   │   ├── tts_engine.py          # TTS语音合成
│   │   ├── whisper_transcriber.py # Whisper语音识别
│   │   ├── material_searcher.py   # 素材检索
│   │   ├── video_editor.py        # 视频编辑
│   │   └── subtitle_renderer.py   # 字幕渲染
│   │
│   ├── ui/                 # 用户界面
│   │   ├── __init__.py
│   │   ├── gradio_app.py   # Gradio应用
│   │   └── components.py   # UI组件
│   │
│   └── utils/              # 工具函数
│       ├── __init__.py
│       ├── file_utils.py   # 文件操作
│       ├── video_utils.py  # 视频工具
│       └── text_utils.py   # 文本处理
│
├── data/                   # 数据目录
│   ├── materials/          # 素材库
│   │   ├── videos/         # 视频素材
│   │   ├── images/         # 图片素材
│   │   └── audio/          # 音频素材
│   ├── output/             # 输出目录
│   └── temp/               # 临时文件
│
├── assets/                 # 资源文件
│   ├── fonts/              # 字体文件
│   └── templates/          # 模板文件
│
├── docs/                   # 文档目录
│   ├── QUICKSTART.md       # 快速开始指南
│   ├── API.md              # API文档
│   └── architecture.md     # 架构文档
│
├── tests/                  # 测试目录
│   ├── test_llm.py
│   ├── test_tts.py
│   └── test_video.py
│
└── logs/                   # 日志目录
    └── autovideo.log
```

---

## 🔍 功能模块

### 1. LLM客户端 ([`llm_client.py`](src/modules/llm_client.py:1))
- **功能**：与DeepSeek API交互，生成视频脚本
- **主要方法**：
  - `generate_script()`: 生成视频脚本
  - `optimize_text()`: 优化文本内容
  - `generate_keywords()`: 生成关键词

### 2. TTS语音合成 ([`tts_engine.py`](src/modules/tts_engine.py:1))
- **功能**：将文本转换为语音
- **支持引擎**：Edge-TTS、PyTTSx3
- **主要方法**：
  - `synthesize()`: 合成语音
  - `list_voices()`: 列出可用语音
  - `adjust_parameters()`: 调整语音参数

### 3. Whisper语音识别 ([`whisper_transcriber.py`](src/modules/whisper_transcriber.py:1))
- **功能**：将语音转换为文本和字幕
- **主要方法**：
  - `transcribe()`: 转录音频
  - `generate_subtitles()`: 生成字幕文件
  - `align_timestamps()`: 时间戳对齐

### 4. 素材检索器 ([`material_searcher.py`](src/modules/material_searcher.py:1))
- **功能**：基于语义相似度搜索和匹配素材
- **主要方法**：
  - `search_by_text()`: 根据文本搜索素材
  - `rank_materials()`: 素材排序
  - `build_index()`: 构建素材索引

### 5. 视频编辑器 ([`video_editor.py`](src/modules/video_editor.py:1))
- **功能**：组装视频、音频和字幕
- **主要方法**：
  - `create_video()`: 创建视频
  - `add_transitions()`: 添加转场效果
  - `merge_clips()`: 合并片段
  - `export()`: 导出最终视频

### 6. 字幕渲染器 ([`subtitle_renderer.py`](src/modules/subtitle_renderer.py:1))
- **功能**：渲染美观的字幕
- **主要方法**：
  - `render_subtitles()`: 渲染字幕
  - `apply_styles()`: 应用样式
  - `generate_srt()`: 生成SRT文件

---

## ❓ 常见问题

### 安装问题

**Q: pip install失败，显示网络错误**

A: 使用国内镜像源：
```bash
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: FFmpeg未找到**

A: 
- Windows：确保FFmpeg在系统PATH中，重启终端
- macOS/Linux：运行`which ffmpeg`检查安装
- 重新安装：`choco install ffmpeg`（Windows）或`brew install ffmpeg`（macOS）

**Q: CUDA错误或GPU不可用**

A:
1. 检查NVIDIA驱动是否最新
2. 确认安装了CUDA Toolkit
3. 重新安装GPU版PyTorch（选择正确的CUDA版本）：
   - 访问 [PyTorch官网](https://pytorch.org/get-started/locally/)
   - 根据你的CUDA版本选择对应的安装命令
   - 例如CUDA 11.8：
     ```bash
     pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
     ```
4. 验证安装：
   ```bash
   python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}, CUDA版本: {torch.version.cuda}')"
   ```

### 配置问题

**Q: DeepSeek API调用失败**

A: 检查以下几点：
1. API密钥是否正确（在config.toml中）
2. API密钥是否有效（未过期）
3. 账户是否有足够的余额
4. 网络连接是否正常

**Q: TTS语音合成失败**

A:
1. **Edge TTS**：
   - 检查网络连接（Edge-TTS需要网络）
   - 尝试更换语音：修改config.toml中的`voice`参数
   - 尝试离线引擎：改为`engine = "pyttsx3"`

2. **SiliconFlow TTS**：
   - 检查API密钥是否正确配置
   - 验证账户余额是否充足
   - 使用测试脚本验证：`python test_siliconflow_tts.py`
   - 检查网络连接到 api.siliconflow.cn

**Q: Whisper模型下载慢或失败**

A: 
1. 使用代理或VPN
2. 手动下载模型文件并放置到缓存目录
3. 使用较小的模型：`model_size = "tiny"`

### 使用问题

**Q: 生成的视频没有声音**

A: 检查：
1. 音频文件是否成功生成（查看temp目录）
2. FFmpeg是否正确安装
3. 配置文件中的audio_codec是否正确

**Q: 字幕显示不正确或乱码**

A: 
1. 确保字体文件存在（SimHei或其他中文字体）
2. 检查字体路径配置
3. Windows用户：安装中文字体包

**Q: 素材匹配不准确**

A: 
1. 提供更详细的主题描述
2. 使用高质量、语义明确的素材
3. 调整配置文件中的`semantic_similarity_threshold`

**Q: 视频生成速度太慢**

A: 优化方法：
1. 使用GPU加速
2. 降低视频分辨率（改为720p）
3. 使用较小的Whisper模型（base或tiny）
4. 减少素材数量和复杂度

**Q: 内存不足错误**

A: 
1. 关闭其他程序释放内存
2. 使用较小的Whisper模型
3. 降低视频分辨率
4. 分批处理素材

### 进阶问题

**Q: 如何自定义字体？**

A: 
1. 将字体文件（.ttf或.otf）放到`assets/fonts/`目录
2. 在config.toml中设置：`font_family = "YourFontName"`

**Q: 如何添加自定义转场效果？**

A: 编辑[`video_editor.py`](src/modules/video_editor.py:1)，在`add_transitions()`方法中添加新效果。

**Q: 如何批量生成多个视频？**

A: 创建脚本：
```python
topics = ["主题1", "主题2", "主题3"]
for topic in topics:
    # 调用生成逻辑
    pass
```

**Q: 可以使用其他LLM吗（如ChatGPT、Claude）？**

A: 可以，需要修改[`llm_client.py`](src/modules/llm_client.py:1)适配不同的API。

---

## 👨‍💻 开发指南

### 贡献代码

我们欢迎所有形式的贡献！
要快速了解目录布局、常用命令和提交流程，请阅读 [`AGENTS.md`](AGENTS.md)（Repository Guidelines）。

#### 开发环境设置

1. Fork本项目
2. 克隆你的Fork：
```bash
git clone https://github.com/your-username/autovideo.git
cd autovideo
```

3. 创建虚拟环境并安装开发依赖：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

4. 安装pre-commit钩子：
```bash
pre-commit install
```

#### 代码规范

- **格式化**：使用Black格式化代码
```bash
black src/ tests/
```

- **导入排序**：使用isort
```bash
isort src/ tests/
```

- **代码检查**：使用flake8
```bash
flake8 src/ tests/
```

- **类型检查**：使用mypy
```bash
mypy src/
```

#### 提交代码

1. 创建功能分支：
```bash
git checkout -b feature/your-feature-name
```

2. 编写代码和测试
3. 运行测试：
```bash
pytest tests/ -v
```

4. 提交更改：
```bash
git add .
git commit -m "feat: 添加新功能描述"
```

5. 推送到GitHub：
```bash
git push origin feature/your-feature-name
```

6. 创建Pull Request

#### 提交信息规范

使用语义化提交信息：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关

例如：
```
feat: 添加视频转场效果支持
fix: 修复字幕时间戳不同步问题
docs: 更新API文档
```

### 编写测试

测试文件放在`tests/`目录：

```python
# tests/test_tts.py
import pytest
from src.modules.tts_engine import TTSEngine

def test_tts_synthesis():
    tts = TTSEngine(config)
    audio_path = tts.synthesize("测试文本")
    assert audio_path.exists()
```

运行测试：
```bash
pytest tests/ -v --cov=src
```

### 文档贡献

- 更新README.md
- 添加代码注释
- 编写API文档
- 创建教程和示例

---

## 🗺️ 路线图

### v0.2.0（计划中）
- [ ] 支持更多TTS引擎（Azure TTS、Google TTS）
- [ ] 添加视频模板系统
- [ ] 支持视频效果（滤镜、特效）
- [ ] 批量处理功能
- [ ] 改进的素材管理界面

### v0.3.0（计划中）
- [ ] 支持多语言（英文、日文等）
- [ ] 视频预览和实时编辑
- [ ] 导出到各大平台（YouTube、抖音等）
- [ ] 协作功能
- [ ] API服务模式

### v1.0.0（未来）
- [ ] 完整的命令行工具
- [ ] 桌面应用版本
- [ ] 云端版本
- [ ] 视频分析和优化建议
- [ ] AI驱动的自动剪辑

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

```
MIT License

Copyright (c) 2024 AutoVideo Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 致谢

本项目使用了以下优秀的开源项目和服务：

- [DeepSeek](https://www.deepseek.com/) - 强大的大语言模型
- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别
- [Edge-TTS](https://github.com/rany2/edge-tts) - 微软Edge TTS
- [MoviePy](https://zulko.github.io/moviepy/) - 视频编辑
- [Gradio](https://www.gradio.app/) - Web界面框架
- [Sentence-Transformers](https://www.sbert.net/) - 语义匹配
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理

特别感谢所有贡献者和用户的支持！

---

## 📮 联系方式

- **问题反馈**：[GitHub Issues](https://github.com/yourusername/autovideo/issues)
- **功能建议**：[GitHub Discussions](https://github.com/yourusername/autovideo/discussions)
- **邮件**：autovideo@example.com

---

<div align="center">

**如果这个项目对你有帮助，请给我们一个⭐️Star！**

Made with ❤️ by AutoVideo Team

</div>
