# AutoVideo API 文档

本文档详细描述了AutoVideo各个模块的API接口、使用方法和示例代码。

---

## 📑 目录

- [核心模块](#核心模块)
  - [配置管理](#配置管理-configpy)
  - [日志系统](#日志系统-loggerpy)
  - [异常处理](#异常处理-exceptionspy)
- [功能模块](#功能模块)
  - [LLM客户端](#llm客户端-llm_clientpy)
  - [TTS语音合成](#tts语音合成-tts_enginepy)
  - [Whisper语音识别](#whisper语音识别-whisper_transcriberpy)
  - [素材检索器](#素材检索器-material_searcherpy)
  - [视频编辑器](#视频编辑器-video_editorpy)
  - [字幕渲染器](#字幕渲染器-subtitle_rendererpy)
- [工具模块](#工具模块)
  - [文件工具](#文件工具-file_utilspy)
  - [视频工具](#视频工具-video_utilspy)
  - [文本工具](#文本工具-text_utilspy)

---

## 核心模块

### 配置管理 ([`config.py`](../src/core/config.py:1))

配置管理模块负责加载和验证项目配置文件。

#### `load_config(config_path: str) -> Dict[str, Any]`

加载TOML配置文件。

**参数**：
- `config_path` (str): 配置文件路径

**返回**：
- `Dict[str, Any]`: 配置字典

**示例**：
```python
from src.core.config import load_config

# 加载配置文件
config = load_config("config.toml")

# 访问配置项
api_key = config['llm']['api_key']
resolution = config['video']['resolution']
```

**异常**：
- `FileNotFoundError`: 配置文件不存在
- `ConfigError`: 配置文件格式错误或缺少必需字段

---

### 日志系统 ([`logger.py`](../src/core/logger.py:1))

提供统一的日志记录功能。

#### `Logger` 类

**初始化**：
```python
from src.core.logger import Logger

logger = Logger(
    name="my_module",
    level="INFO",
    log_file="logs/app.log"
)
```

**方法**：

##### `info(message: str) -> None`
记录信息级别日志。

```python
logger.info("处理开始")
```

##### `warning(message: str) -> None`
记录警告级别日志。

```python
logger.warning("文件不存在，使用默认配置")
```

##### `error(message: str) -> None`
记录错误级别日志。

```python
logger.error("API调用失败")
```

##### `debug(message: str) -> None`
记录调试级别日志。

```python
logger.debug(f"变量值: {value}")
```

---

### 异常处理 ([`exceptions.py`](../src/core/exceptions.py:1))

定义了项目中使用的自定义异常类。

#### 异常类层次结构

```python
AutoVideoError                    # 基础异常类
├── ConfigError                   # 配置错误
├── LLMError                      # LLM相关错误
├── TTSError                      # TTS相关错误
├── WhisperError                  # Whisper相关错误
├── MaterialSearchError           # 素材搜索错误
├── VideoProcessingError          # 视频处理错误
└── SubtitleError                 # 字幕相关错误
```

**使用示例**：
```python
from src.core.exceptions import LLMError

try:
    # 执行LLM操作
    script = llm_client.generate_script(prompt)
except LLMError as e:
    print(f"LLM错误: {e}")
```

---

## 功能模块

### LLM客户端 ([`llm_client.py`](../src/modules/llm_client.py:1))

与DeepSeek API交互，生成视频脚本和内容分析。

#### `LLMClient` 类

**初始化**：
```python
from src.modules.llm_client import LLMClient

llm_client = LLMClient(
    config={
        'api_key': 'your-api-key',
        'base_url': 'https://api.deepseek.com',
        'model': 'deepseek-chat',
        'max_tokens': 4000,
        'temperature': 0.7,
        'timeout': 30
    },
    logger=logger
)
```

**方法**：

##### `generate_script(prompt: str, **kwargs) -> str`

生成视频脚本。

**参数**：
- `prompt` (str): 用户输入的视频描述
- `**kwargs`: 可选参数
  - `max_tokens` (int): 最大token数
  - `temperature` (float): 生成温度

**返回**：
- `str`: 生成的视频脚本文本

**示例**：
```python
prompt = "创建一个介绍智能手表的60秒宣传视频"
script = llm_client.generate_script(
    prompt=prompt,
    temperature=0.8,
    max_tokens=2000
)
print(script)
```

**异常**：
- `LLMError`: API调用失败

---

##### `generate_scene_descriptions(script: str) -> List[Dict[str, Any]]`

从脚本中提取场景描述。

**参数**：
- `script` (str): 视频脚本文本

**返回**：
- `List[Dict[str, Any]]`: 场景描述列表，每个场景包含：
  - `scene_id` (int): 场景编号
  - `visual_description` (str): 画面描述
  - `narration` (str): 旁白文本
  - `duration_estimate` (float): 预估时长（秒）

**示例**：
```python
scenes = llm_client.generate_scene_descriptions(script)
for scene in scenes:
    print(f"场景 {scene['scene_id']}: {scene['visual_description']}")
```

---

##### `extract_keywords(text: str) -> List[str]`

从文本中提取关键词。

**参数**：
- `text` (str): 输入文本

**返回**：
- `List[str]`: 关键词列表

**示例**：
```python
text = "智能手表具有健康监测和运动追踪功能"
keywords = llm_client.extract_keywords(text)
# 输出: ['智能手表', '健康监测', '运动追踪', ...]
```

---

### TTS语音合成 ([`tts_engine.py`](../src/modules/tts_engine.py:1))

将文本转换为语音。

#### `TTSEngine` 类

**初始化**：
```python
from src.modules.tts_engine import TTSEngine

tts_engine = TTSEngine(
    config={
        'engine': 'edge-tts',
        'voice': 'zh-CN-XiaoxiaoNeural',
        'rate': 1.0,
        'volume': 1.0,
        'pitch': 0
    },
    logger=logger
)
```

**方法**：

##### `synthesize(text: str, output_path: str, **kwargs) -> str`

合成语音。

**参数**：
- `text` (str): 要转换的文本
- `output_path` (str): 输出音频文件路径
- `**kwargs`: 可选参数
  - `voice` (str): 语音名称
  - `rate` (float): 语速倍率
  - `volume` (float): 音量倍率
  - `pitch` (int): 音调偏移

**返回**：
- `str`: 生成的音频文件路径

**示例**：
```python
text = "欢迎使用AutoVideo自动化视频生成工具"
audio_path = tts_engine.synthesize(
    text=text,
    output_path="output/narration.mp3",
    voice="zh-CN-YunxiNeural",  # 使用男声
    rate=1.2  # 加快语速
)
print(f"音频已生成: {audio_path}")
```

**异常**：
- `TTSError`: 语音合成失败

---

##### `get_available_voices() -> List[Dict[str, str]]`

获取可用的语音列表。

**返回**：
- `List[Dict[str, str]]`: 语音列表，每个语音包含：
  - `name` (str): 语音名称
  - `locale` (str): 语言区域
  - `gender` (str): 性别

**示例**：
```python
voices = tts_engine.get_available_voices()
for voice in voices:
    print(f"{voice['name']} - {voice['gender']} - {voice['locale']}")
```

---

##### `set_voice(voice: str) -> None`

设置语音。

**示例**：
```python
tts_engine.set_voice("zh-CN-YunyangNeural")
```

##### `set_speed(rate: float) -> None`

设置语速（0.5-2.0）。

**示例**：
```python
tts_engine.set_speed(1.5)  # 1.5倍速
```

##### `set_volume(volume: float) -> None`

设置音量（0.0-2.0）。

**示例**：
```python
tts_engine.set_volume(0.8)  # 80%音量
```

##### `set_pitch(pitch: int) -> None`

设置音调（-100到100 Hz）。

**示例**：
```python
tts_engine.set_pitch(10)  # 提高音调10Hz
```

---

### Whisper语音识别 ([`whisper_transcriber.py`](../src/modules/whisper_transcriber.py:1))

使用OpenAI Whisper进行语音识别和字幕生成。

#### `WhisperTranscriber` 类

**初始化**：
```python
from src.modules.whisper_transcriber import WhisperTranscriber

transcriber = WhisperTranscriber(
    config={
        'model_size': 'base',
        'language': 'zh',
        'device': 'auto'
    },
    logger=logger
)
```

**方法**：

##### `transcribe(audio_path: str, **kwargs) -> Dict[str, Any]`

转录音频。

**参数**：
- `audio_path` (str): 音频文件路径
- `**kwargs`: 可选参数
  - `language` (str): 语言代码
  - `task` (str): 任务类型（'transcribe'或'translate'）

**返回**：
- `Dict[str, Any]`: 转录结果，包含：
  - `text` (str): 完整文本
  - `segments` (List): 分段信息
  - `language` (str): 检测到的语言

**示例**：
```python
result = transcriber.transcribe("audio/narration.mp3")
print(f"转录文本: {result['text']}")

for segment in result['segments']:
    print(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text']}")
```

**异常**：
- `WhisperError`: 转录失败

---

##### `generate_subtitles(audio_path: str, output_path: str, format: str = 'srt') -> str`

生成字幕文件。

**参数**：
- `audio_path` (str): 音频文件路径
- `output_path` (str): 输出字幕文件路径
- `format` (str): 字幕格式（'srt'、'vtt'、'ass'）

**返回**：
- `str`: 生成的字幕文件路径

**示例**：
```python
subtitle_path = transcriber.generate_subtitles(
    audio_path="audio/narration.mp3",
    output_path="subtitles/video.srt",
    format="srt"
)
```

---

### 素材检索器 ([`material_searcher.py`](../src/modules/material_searcher.py:1))

基于语义相似度搜索和匹配素材。

#### `MaterialSearcher` 类

**初始化**：
```python
from src.modules.material_searcher import MaterialSearcher

searcher = MaterialSearcher(
    config={
        'materials_dir': './data/materials',
        'semantic_similarity_threshold': 0.7,
        'max_results': 10,
        'embedding_model': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    },
    logger=logger
)
```

**方法**：

##### `build_index() -> None`

构建素材索引。

**示例**：
```python
# 首次使用前需要构建索引
searcher.build_index()
```

---

##### `search(query: str, top_k: int = 5) -> List[Dict[str, Any]]`

搜索素材。

**参数**：
- `query` (str): 搜索查询（场景描述或关键词）
- `top_k` (int): 返回结果数量

**返回**：
- `List[Dict[str, Any]]`: 素材列表，每个素材包含：
  - `path` (str): 文件路径
  - `score` (float): 相似度分数
  - `type` (str): 素材类型（'video'、'image'、'audio'）

**示例**：
```python
query = "智能手表显示健康数据"
materials = searcher.search(query, top_k=5)

for material in materials:
    print(f"{material['path']} - 相似度: {material['score']:.2f}")
```

---

##### `search_by_keywords(keywords: List[str]) -> List[str]`

根据关键词搜索素材。

**参数**：
- `keywords` (List[str]): 关键词列表

**返回**：
- `List[str]`: 素材路径列表

**示例**：
```python
keywords = ['手表', '健康', '运动']
materials = searcher.search_by_keywords(keywords)
```

---

### 视频编辑器 ([`video_editor.py`](../src/modules/video_editor.py:1))

组装视频、音频和字幕。

#### `VideoEditor` 类

**初始化**：
```python
from src.modules.video_editor import VideoEditor

editor = VideoEditor(
    config={
        'resolution': [1920, 1080],
        'fps': 30,
        'codec': 'libx264',
        'bitrate': '2000k',
        'audio_codec': 'aac',
        'audio_bitrate': '128k',
        'format': 'mp4'
    },
    logger=logger
)
```

**方法**：

##### `create_video(script: List[Dict], materials: List[str], output_path: str, **kwargs) -> str`

创建视频。

**参数**：
- `script` (List[Dict]): 脚本片段列表
- `materials` (List[str]): 素材文件路径列表
- `output_path` (str): 输出视频文件路径
- `**kwargs`: 额外参数

**返回**：
- `str`: 生成的视频文件路径

**示例**：
```python
script = [
    {'duration': 5, 'text': '场景1'},
    {'duration': 8, 'text': '场景2'},
    {'duration': 7, 'text': '场景3'}
]

materials = [
    'materials/video1.mp4',
    'materials/image1.jpg',
    'materials/video2.mp4'
]

video_path = editor.create_video(
    script=script,
    materials=materials,
    output_path='output/final_video.mp4'
)
```

**异常**：
- `VideoProcessingError`: 视频创建失败

---

##### `add_audio_track(video_path: str, audio_path: str, output_path: str = None) -> str`

为视频添加音频轨道。

**参数**：
- `video_path` (str): 视频文件路径
- `audio_path` (str): 音频文件路径
- `output_path` (str, 可选): 输出文件路径

**返回**：
- `str`: 输出视频文件路径

**示例**：
```python
video_with_audio = editor.add_audio_track(
    video_path='temp/video_no_audio.mp4',
    audio_path='temp/narration.mp3',
    output_path='output/final_video.mp4'
)
```

---

##### `add_transitions(video_path: str, transition_type: str = 'fade', duration: float = 1.0) -> str`

添加转场效果。

**参数**：
- `video_path` (str): 视频文件路径
- `transition_type` (str): 转场类型（'fade'、'crossfade'）
- `duration` (float): 转场持续时间（秒）

**返回**：
- `str`: 处理后的视频路径

**示例**：
```python
video_with_transitions = editor.add_transitions(
    video_path='temp/video.mp4',
    transition_type='fade',
    duration=1.5
)
```

---

##### `export_video(video_path: str, output_path: str, **kwargs) -> str`

导出视频（格式转换或重新编码）。

**参数**：
- `video_path` (str): 源视频文件路径
- `output_path` (str): 输出视频文件路径
- `**kwargs`: 导出参数（fps、codec、bitrate等）

**返回**：
- `str`: 导出的视频文件路径

**示例**：
```python
exported_video = editor.export_video(
    video_path='temp/video.mp4',
    output_path='output/video_720p.mp4',
    resolution=[1280, 720],
    bitrate='1000k'
)
```

---

### 字幕渲染器 ([`subtitle_renderer.py`](../src/modules/subtitle_renderer.py:1))

渲染美观的字幕到视频。

#### `SubtitleRenderer` 类

**初始化**：
```python
from src.modules.subtitle_renderer import SubtitleRenderer

renderer = SubtitleRenderer(
    config={
        'font_family': 'SimHei',
        'font_size': 36,
        'font_color': '#FFFFFF',
        'background_color': '#000000',
        'background_alpha': 0.7,
        'position': 'bottom',
        'margin': 50
    },
    logger=logger
)
```

**方法**：

##### `render(video_path: str, subtitle_path: str, output_path: str, **kwargs) -> str`

渲染字幕到视频。

**参数**：
- `video_path` (str): 视频文件路径
- `subtitle_path` (str): 字幕文件路径（SRT格式）
- `output_path` (str): 输出视频文件路径
- `**kwargs`: 额外渲染参数

**返回**：
- `str`: 带字幕的视频文件路径

**示例**：
```python
video_with_subtitles = renderer.render(
    video_path='temp/video.mp4',
    subtitle_path='temp/subtitles.srt',
    output_path='output/final_video.mp4'
)
```

**异常**：
- `SubtitleError`: 字幕渲染失败

---

##### `generate_srt(segments: List[Dict], output_path: str) -> str`

生成SRT字幕文件。

**参数**：
- `segments` (List[Dict]): 字幕片段列表
- `output_path` (str): 输出SRT文件路径

**返回**：
- `str`: SRT文件路径

**示例**：
```python
segments = [
    {'start': 0.0, 'end': 3.5, 'text': '欢迎来到AutoVideo'},
    {'start': 3.5, 'end': 7.2, 'text': '自动化视频生成工具'},
]

srt_path = renderer.generate_srt(
    segments=segments,
    output_path='output/subtitles.srt'
)
```

---

## 工具模块

### 文件工具 ([`file_utils.py`](../src/utils/file_utils.py:1))

文件和目录操作工具。

#### 函数列表

##### `ensure_dir(path: str) -> None`

确保目录存在，如果不存在则创建。

```python
from src.utils.file_utils import ensure_dir

ensure_dir("output/videos")
```

---

##### `get_file_size(path: str) -> int`

获取文件大小（字节）。

```python
from src.utils.file_utils import get_file_size

size = get_file_size("video.mp4")
print(f"文件大小: {size / 1024 / 1024:.2f} MB")
```

---

##### `list_files(directory: str, extensions: List[str] = None) -> List[str]`

列出目录中的文件。

**参数**：
- `directory` (str): 目录路径
- `extensions` (List[str], 可选): 文件扩展名过滤

```python
from src.utils.file_utils import list_files

# 列出所有视频文件
videos = list_files("materials/videos", ['.mp4', '.avi', '.mov'])
```

---

### 视频工具 ([`video_utils.py`](../src/utils/video_utils.py:1))

视频处理相关工具函数。

#### 函数列表

##### `get_video_duration(video_path: str) -> float`

获取视频时长（秒）。

```python
from src.utils.video_utils import get_video_duration

duration = get_video_duration("video.mp4")
print(f"视频时长: {duration:.2f}秒")
```

---

##### `get_video_info(video_path: str) -> Dict[str, Any]`

获取视频信息。

**返回字典包含**：
- `duration`: 时长（秒）
- `fps`: 帧率
- `resolution`: 分辨率[宽, 高]
- `codec`: 编码器
- `bitrate`: 比特率

```python
from src.utils.video_utils import get_video_info

info = get_video_info("video.mp4")
print(f"分辨率: {info['resolution']}")
print(f"帧率: {info['fps']}")
```

---

##### `extract_audio(video_path: str, output_path: str) -> str`

从视频中提取音频。

```python
from src.utils.video_utils import extract_audio

audio_path = extract_audio("video.mp4", "audio.mp3")
```

---

### 文本工具 ([`text_utils.py`](../src/utils/text_utils.py:1))

文本处理工具函数。

#### 函数列表

##### `clean_text(text: str) -> str`

清理文本（去除多余空格、换行等）。

```python
from src.utils.text_utils import clean_text

text = "这是  一段\n\n有很多   空格的文本"
cleaned = clean_text(text)
# 输出: "这是 一段 有很多 空格的文本"
```

---

##### `split_sentences(text: str) -> List[str]`

将文本分割成句子。

```python
from src.utils.text_utils import split_sentences

text = "这是第一句。这是第二句！这是第三句？"
sentences = split_sentences(text)
# 输出: ["这是第一句。", "这是第二句！", "这是第三句？"]
```

---

##### `estimate_reading_time(text: str, words_per_minute: int = 150) -> float`

估算文本阅读时间（秒）。

```python
from src.utils.text_utils import estimate_reading_time

text = "这是一段需要朗读的文本"
duration = estimate_reading_time(text, words_per_minute=200)
print(f"预计时长: {duration:.1f}秒")
```

---

## 完整使用示例

### 示例1：生成完整视频

```python
from src.core.config import load_config
from src.core.logger import Logger
from src.modules.llm_client import LLMClient
from src.modules.tts_engine import TTSEngine
from src.modules.material_searcher import MaterialSearcher
from src.modules.video_editor import VideoEditor
from src.modules.whisper_transcriber import WhisperTranscriber
from src.modules.subtitle_renderer import SubtitleRenderer

# 1. 加载配置
config = load_config("config.toml")
logger = Logger("autovideo", level="INFO")

# 2. 初始化各模块
llm = LLMClient(config['llm'], logger)
tts = TTSEngine(config['tts'], logger)
searcher = MaterialSearcher(config['material_search'], logger)
editor = VideoEditor(config['video'], logger)
transcriber = WhisperTranscriber(config['whisper'], logger)
renderer = SubtitleRenderer(config['subtitle'], logger)

# 3. 生成脚本
topic = "介绍一款智能手表的健康监测功能"
script_text = llm.generate_script(topic)
logger.info(f"脚本生成完成: {script_text[:100]}...")

# 4. 生成语音
audio_path = tts.synthesize(
    text=script_text,
    output_path="temp/narration.mp3"
)
logger.info(f"语音生成完成: {audio_path}")

# 5. 搜索素材
keywords = llm.extract_keywords(script_text)
materials = searcher.search_by_keywords(keywords)
logger.info(f"找到 {len(materials)} 个素材")

# 6. 生成字幕
subtitle_path = transcriber.generate_subtitles(
    audio_path=audio_path,
    output_path="temp/subtitles.srt"
)

# 7. 创建视频
script_segments = [{'duration': 5, 'text': script_text}]
video_path = editor.create_video(
    script=script_segments,
    materials=materials[:3],
    output_path="temp/video_no_audio.mp4"
)

# 8. 添加音频
video_with_audio = editor.add_audio_track(
    video_path=video_path,
    audio_path=audio_path,
    output_path="temp/video_with_audio.mp4"
)

# 9. 添加字幕
final_video = renderer.render(
    video_path=video_with_audio,
    subtitle_path=subtitle_path,
    output_path="output/final_video.mp4"
)

logger.info(f"视频生成完成: {final_video}")
```

---

### 示例2：批量处理

```python
topics = [
    "介绍产品A的特点",
    "介绍产品B的优势",
    "介绍产品C的应用场景"
]

for i, topic in enumerate(topics):
    logger.info(f"处理第 {i+1} 个视频: {topic}")
    
    # 生成脚本
    script = llm.generate_script(topic)
    
    # 生成语音
    audio_path = tts.synthesize(
        text=script,
        output_path=f"temp/audio_{i}.mp3"
    )
    
    # 搜索素材
    keywords = llm.extract_keywords(script)
    materials = searcher.search_by_keywords(keywords)
    
    # 创建视频
    video_path = editor.create_video(
        script=[{'duration': 10, 'text': script}],
        materials=materials[:5],
        output_path=f"output/video_{i}.mp4"
    )
    
    logger.info(f"视频 {i+1} 完成: {video_path}")
```

---

## 错误处理最佳实践

```python
from src.core.exceptions import (
    LLMError, TTSError, VideoProcessingError,
    MaterialSearchError, WhisperError, SubtitleError
)

try:
    # 执行操作
    script = llm.generate_script(prompt)
    audio = tts.synthesize(script, "output.mp3")
    video = editor.create_video([], [], "final.mp4")
    
except LLMError as e:
    logger.error(f"LLM错误: {e}")
    # 处理LLM相关错误
    
except TTSError as e:
    logger.error(f"TTS错误: {e}")
    # 处理TTS相关错误
    
except VideoProcessingError as e:
    logger.error(f"视频处理错误: {e}")
    # 处理视频相关错误
    
except Exception as e:
    logger.error(f"未知错误: {e}")
    # 处理其他错误
    
finally:
    # 清理资源
    logger.info("任务完成或中断")
```

---

## 性能优化建议

### 1. 使用GPU加速

```python
# 配置Whisper使用GPU
transcriber = WhisperTranscriber(
    config={
        'model_size': 'base',
        'device': 'cuda'  # 使用GPU
    }
)
```

### 2. 批量处理

```python
# 批量合成语音
texts = ["文本1", "文本2", "文本3"]
for i, text in enumerate(texts):
    tts.synthesize(text, f"audio_{i}.mp3")
```

### 3. 缓存结果

```python
import pickle

# 缓存素材索引
searcher.build_index()
with open('cache/index.pkl', 'wb') as f:
    pickle.dump(searcher.index, f)

# 加载缓存
with open('cache/index.pkl', 'rb') as f:
    searcher.index = pickle.load(f)
```

---

## 更多资源

- [README.md](../README.md) - 完整项目文档
- [QUICKSTART.md](QUICKSTART.md) - 快速开始指南
- [GitHub Issues](https://github.com/yourusername/autovideo/issues) - 问题反馈

---

**最后更新**: 2024-10-24