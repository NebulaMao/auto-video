# AutoVideo 快速开始指南

欢迎使用AutoVideo！本指南将帮助你在10分钟内完成从安装到生成第一个视频的全部过程。

---

## 📋 前提条件检查

在开始之前，请确认你的系统满足以下要求：

- ✅ **操作系统**：Windows 10/11、macOS 10.15+、或 Linux（Ubuntu 20.04+）
- ✅ **Python版本**：3.10 或更高
- ✅ **可用磁盘空间**：至少 10GB
- ✅ **网络连接**：需要下载模型和调用API

### 检查Python版本

打开终端（Windows用户打开"命令提示符"或"PowerShell"），运行：

```bash
python --version
```

应该显示 `Python 3.10.x` 或更高版本。

> **Windows用户注意**：如果显示 `Python 2.x` 或命令未找到，请尝试 `python3 --version`。如果Python 3未安装，请访问 [python.org](https://www.python.org/downloads/) 下载安装。

---

## 🚀 第一步：安装FFmpeg

FFmpeg是视频处理的核心工具，必须先安装。

### Windows用户

**方法1：使用Chocolatey（推荐）**

如果已安装Chocolatey，运行：
```bash
choco install ffmpeg
```

**方法2：手动安装**

1. 访问 [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
2. 下载 `ffmpeg-release-full.7z`
3. 解压到 `C:\ffmpeg`
4. 添加到系统PATH：
   - 右键"此电脑" → "属性" → "高级系统设置"
   - 点击"环境变量"
   - 在"系统变量"中找到"Path"，点击"编辑"
   - 添加新路径：`C:\ffmpeg\bin`
   - 点击"确定"保存
5. 重启终端，运行 `ffmpeg -version` 验证安装

### macOS用户

使用Homebrew安装（最简单）：
```bash
brew install ffmpeg
```

如果没有Homebrew，先安装Homebrew：
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Linux用户

Ubuntu/Debian：
```bash
sudo apt update
sudo apt install ffmpeg
```

CentOS/RHEL：
```bash
sudo yum install ffmpeg
```

### 验证FFmpeg安装

运行以下命令，应该显示FFmpeg的版本信息：
```bash
ffmpeg -version
```

---

## 📥 第二步：获取AutoVideo

### 克隆项目

```bash
# 克隆代码仓库
git clone https://github.com/yourusername/autovideo.git

# 进入项目目录
cd autovideo
```

如果没有安装Git，可以直接下载ZIP包：
1. 访问项目GitHub页面
2. 点击绿色的"Code"按钮
3. 选择"Download ZIP"
4. 解压到你想要的位置

---

## 🔧 第三步：创建虚拟环境（推荐但可选）

虚拟环境可以隔离项目依赖，避免与其他Python项目冲突。

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

激活后，你的终端提示符前面会显示 `(venv)`。

> **提示**：要退出虚拟环境，运行 `deactivate`

---

## 📦 第四步：安装Python依赖

这一步会安装所有需要的Python包，可能需要5-10分钟。

```bash
# 标准安装
pip install -e .

# 如果下载速度慢，使用国内镜像
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 可选：安装GPU支持（如果有NVIDIA显卡）

GPU加速可以显著提升Whisper的处理速度。

```bash
# 1. 首先安装CUDA（访问 https://developer.nvidia.com/cuda-downloads）

# 2. 安装PyTorch GPU版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 3. 验证GPU是否可用
python -c "import torch; print('CUDA可用:', torch.cuda.is_available())"
```

### 验证安装

运行以下命令检查关键依赖是否安装成功：

```bash
python -c "import gradio, moviepy, whisper, openai; print('所有依赖安装成功！')"
```

如果没有报错，说明安装成功！

---

## 🔑 第五步：获取DeepSeek API密钥

AutoVideo使用DeepSeek的大语言模型生成视频脚本。

### 注册并获取API密钥

1. **访问DeepSeek平台**
   - 打开浏览器访问：[https://platform.deepseek.com](https://platform.deepseek.com)

2. **注册账号**
   - 点击"注册"按钮
   - 使用邮箱注册（支持Gmail、QQ邮箱等）
   - 完成邮箱验证

3. **创建API密钥**
   - 登录后，点击左侧菜单的"API Keys"
   - 点击"创建新密钥"按钮
   - 输入密钥名称（如"AutoVideo"）
   - 点击"创建"
   - **重要**：复制显示的API密钥并妥善保存（只会显示一次！）

4. **充值（如果需要）**
   - DeepSeek通常会提供新用户免费额度
   - 如果需要更多使用量，在"充值"页面充值
   - 建议先充值少量金额测试（如10元）

### API密钥示例

API密钥格式类似：`sk-1234567890abcdefghijklmnopqrstuvwxyz`

---

## ⚙️ 第六步：配置AutoVideo

### 创建配置文件

在项目根目录下，复制示例配置文件：

```bash
# Windows
copy config.toml.example config.toml

# macOS/Linux
cp config.toml.example config.toml
```

### 编辑配置文件

使用任何文本编辑器打开 [`config.toml`](../config.toml:1)：

```bash
# Windows - 使用记事本
notepad config.toml

# macOS
open -e config.toml

# Linux
nano config.toml
# 或
gedit config.toml
```

### 最小必要配置

找到 `[llm]` 部分，将 `api_key` 替换为你的真实API密钥：

```toml
[llm]
api_key = "sk-your-actual-api-key-here"  # 替换这里！
```

**就这样！** 其他配置项可以保持默认值。

### 可选：调整其他配置

如果想要更好的效果，可以调整以下配置：

```toml
# 提高视频质量
[video]
resolution = [1920, 1080]  # 1080p
bitrate = "3000k"          # 提高比特率

# 提高语音识别准确度（需要更多内存）
[whisper]
model_size = "small"       # 从base改为small

# 更换语音音色
[tts]
voice = "zh-CN-YunxiNeural"  # 换成男声
```

---

## 🎬 第七步：生成你的第一个视频！

现在一切就绪，让我们生成第一个视频！

### 启动Web界面

在项目根目录运行：

```bash
python main.py
```

你会看到类似的输出：

```
Loading configuration...
Initializing AutoVideo...
Starting Gradio interface...
Running on local URL:  http://127.0.0.1:7860
```

### 访问Web界面

1. 打开浏览器（推荐使用Chrome或Edge）
2. 访问：[http://127.0.0.1:7860](http://127.0.0.1:7860)
3. 你会看到AutoVideo的用户界面

### 创建第一个视频

让我们创建一个简单的产品介绍视频：

**步骤1：输入视频主题**
```
在"视频主题"文本框中输入：
介绍一款智能手表，它具有健康监测、运动追踪和智能通知功能
```

**步骤2：设置参数（使用默认值即可）**
- 视频时长：60秒
- 视频风格：专业
- 配音音色：zh-CN-XiaoxiaoNeural（温柔女声）

**步骤3：上传素材（可选）**
- 如果你有产品图片或视频，可以点击"上传素材"
- 第一次可以跳过此步骤，让系统使用示例素材

**步骤4：点击"生成视频"按钮**

### 等待处理

视频生成过程通常需要 2-5 分钟，取决于：
- 视频时长
- 你的电脑性能
- 是否使用GPU加速

进度条会显示当前处理状态：
1. ✅ 生成脚本（10%）
2. ✅ 合成语音（30%）
3. ✅ 语音识别（50%）
4. ✅ 匹配素材（70%）
5. ✅ 生成字幕（80%）
6. ✅ 渲染视频（90%）
7. ✅ 完成！（100%）

### 预览和下载

生成完成后：
1. 视频会自动显示在界面中
2. 点击播放按钮预览效果
3. 点击"下载"按钮保存到本地

**恭喜！** 🎉 你已经成功生成了第一个AI视频！

---

## 💡 使用技巧

### 提高视频质量的建议

1. **提供详细的主题描述**
   ```
   ❌ 不好：介绍产品
   ✅ 好：介绍一款智能手表，重点展示它的健康监测功能，包括心率、血氧、睡眠监测，以及与手机的无缝连接体验
   ```

2. **上传高质量素材**
   - 使用1080p或更高分辨率的图片/视频
   - 确保素材与主题相关
   - 避免使用有水印的素材

3. **调整生成参数**
   ```toml
   # 在config.toml中
   [llm]
   temperature = 0.8  # 提高创意性
   
   [video]
   bitrate = "3000k"  # 提高视频质量
   ```

### 常见使用场景

#### 场景1：产品宣传视频
```
主题：介绍我们的新款智能耳机，具有主动降噪、高音质和长续航特点
时长：60秒
风格：专业
素材：产品照片、使用场景视频
```

#### 场景2：教程视频
```
主题：如何使用Python进行数据分析，包括导入数据、清洗数据和可视化
时长：90秒
风格：教育
素材：代码截图、图表
```

#### 场景3：新闻/资讯视频
```
主题：2024年AI技术发展趋势，重点介绍大语言模型和生成式AI的应用
时长：120秒
风格：专业
素材：相关图片、数据图表
```

---

## 🔧 故障排查

### 问题1：启动失败，提示"ModuleNotFoundError"

**原因**：某些Python包未正确安装

**解决方法**：
```bash
# 重新安装依赖
pip install -e . --force-reinstall
```

### 问题2：API调用失败

**可能原因和解决方法**：

1. **API密钥错误**
   - 检查[`config.toml`](../config.toml:1)中的api_key是否正确
   - 确认没有多余的空格或引号

2. **网络问题**
   - 确认可以访问 https://api.deepseek.com
   - 检查防火墙设置
   - 尝试使用代理

3. **余额不足**
   - 登录DeepSeek平台查看余额
   - 充值后重试

### 问题3：Whisper下载失败

**解决方法**：

1. **使用代理或VPN**

2. **手动下载模型**
   ```bash
   python -c "import whisper; whisper.load_model('base')"
   ```

3. **使用更小的模型**
   ```toml
   [whisper]
   model_size = "tiny"  # 改为tiny
   ```

### 问题4：FFmpeg错误

**检查FFmpeg是否正确安装**：
```bash
ffmpeg -version
```

如果显示"命令未找到"，重新安装FFmpeg并确保添加到PATH。

### 问题5：视频无声音

**检查点**：
1. 查看[`./data/temp/`](../data/temp)目录，确认音频文件已生成
2. 检查音频播放器能否播放该音频
3. 确认[`config.toml`](../config.toml:1)中的TTS配置正确

### 问题6：内存不足

**解决方法**：
```toml
# 在config.toml中降低资源使用
[whisper]
model_size = "tiny"  # 使用最小模型

[video]
resolution = [1280, 720]  # 降低分辨率
```

### 问题7：GPU不可用

**检查CUDA**：
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

如果显示`False`：
1. 确认已安装NVIDIA驱动
2. 安装CUDA Toolkit
3. 重新安装PyTorch GPU版本

---

## 📚 下一步

恭喜你完成了快速开始！现在你可以：

1. **阅读完整文档**
   - [README.md](../README.md) - 完整的项目文档
   - [API.md](API.md) - API接口文档

2. **探索高级功能**
   - 自定义字幕样式
   - 调整视频转场效果
   - 使用自定义字体
   - 批量生成视频

3. **优化配置**
   - 根据你的硬件调整性能配置
   - 尝试不同的语音音色
   - 调整视频质量设置

4. **加入社区**
   - 在GitHub上提问题和建议
   - 分享你的使用经验
   - 贡献代码

---

## 🆘 获取帮助

如果遇到本指南未涵盖的问题：

1. **查看日志**
   ```bash
   # 查看详细日志
   cat logs/autovideo.log  # macOS/Linux
   type logs\autovideo.log  # Windows
   ```

2. **查看常见问题**
   - [README.md - 常见问题部分](../README.md#-常见问题)

3. **提交Issue**
   - 访问：[https://github.com/yourusername/autovideo/issues](https://github.com/yourusername/autovideo/issues)
   - 点击"New Issue"
   - 详细描述你的问题，包括：
     - 操作系统和Python版本
     - 错误信息和日志
     - 复现步骤

4. **联系我们**
   - 邮箱：autovideo@example.com

---

## ✅ 快速参考命令

```bash
# 启动AutoVideo
python main.py

# 查看日志
cat logs/autovideo.log  # macOS/Linux
type logs\autovideo.log  # Windows

# 更新依赖
pip install -e . --upgrade

# 清理临时文件
rm -rf data/temp/*  # macOS/Linux
rmdir /s /q data\temp  # Windows

# 验证GPU
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

---

**祝你使用愉快！** 如果AutoVideo对你有帮助，请给我们一个⭐️Star！