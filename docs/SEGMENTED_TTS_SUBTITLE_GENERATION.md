# 分段TTS字幕生成流程

## 概述

本文档描述了AutoVideo项目中新的字幕生成流程，该流程通过按标点符号分割口播文案，分段进行TTS合成，然后基于实际TTS时长计算字幕时间轴，确保字幕内容与原始口播文本完全一致。

## 流程对比

### 原始流程
1. 生成完整口播文案
2. 一次性TTS合成完整音频
3. 使用Whisper转录音频生成字幕
4. 渲染字幕到视频

### 新流程
1. 生成完整口播文案
2. 按标点符号分割口播文案为多个段落
3. 分段进行TTS合成，获取每段音频的实际时长
4. 将分段TTS音频拼接成一个完整音频文件
5. 基于分段TTS实际时长累加计算字幕时间轴
6. 使用原始口播文本生成SRT字幕文件
7. 渲染字幕到视频

## 技术实现

### 1. 文本分割功能

位置：`src/utils/text_utils.py`

函数：`split_text_by_punctuation(text, language='zh', min_length=10, max_length=100)`

功能：
- 按中文标点符号（。！？；：）分割文本
- 处理过长的段落，按句子进一步分割
- 过滤过短的段落
- 返回适合TTS的文本段落列表

### 2. 分段TTS合成功能

位置：`src/modules/tts_engine.py`

新增方法：
- `get_audio_duration(audio_path)`: 获取音频文件时长
- `synthesize_segments(text_segments, output_dir, **kwargs)`: 分段合成语音

功能：
- 为每个文本段落生成独立的TTS音频
- 返回每段音频的路径和实际时长信息
- 支持所有原有的TTS参数（语音、语速、音量、音调）

### 3. 音频拼接功能

位置：`src/utils/ffmpeg_wrapper.py`

新增方法：`concat_audio_files(audio_files, output_path)`

功能：
- 使用FFmpeg concat demuxer无损拼接多个音频文件
- 支持不同格式的音频文件
- 保持音频质量不变

### 4. 工作流管理器修改

位置：`src/core/workflow_manager.py`

新增方法：
- `_generate_tts_with_segments(script, task_id)`: 分段生成TTS语音
- `_generate_subtitles_from_segments(segments_info, task_id)`: 基于分段信息生成字幕
- `_format_srt_time(seconds)`: 格式化时间为SRT格式

修改方法：
- `execute_video_generation_pipeline()`: 使用新的分段TTS流程
- `execute_video_generation_pipeline_with_script()`: 使用新的分段TTS流程

### 5. 配置选项

位置：`config.toml`

新增配置项：
```toml
[tts]
segment_by_punctuation = true  # 是否按标点符号分段TTS
min_segment_length = 10  # 最小段落长度(字符)
max_segment_length = 100  # 最大段落长度(字符)
segment_pause = 0.5  # 段落间停顿时间(秒)
```

## 优势

### 1. 字幕内容准确性
- 字幕内容与原始口播文本完全一致
- 避免了Whisper转录可能出现的识别错误
- 保留了原始文本的所有标点符号和格式

### 2. 时间轴精确性
- 基于实际TTS音频时长计算时间轴
- 每段字幕的开始和结束时间与音频完全同步
- 避免了音频转录的时间偏差

### 3. 处理效率
- 分段处理可以更好地利用系统资源
- 支持并行处理（未来可扩展）
- 减少了单次长文本TTS的失败风险

### 4. 容错性
- 如果分段TTS失败，自动回退到原始TTS方法
- 如果基于分段信息生成字幕失败，自动回退到Whisper方法
- 保持了系统的稳定性和可靠性

## 测试

测试脚本：`test_segmented_tts.py`

测试内容：
1. 文本分割功能测试
2. 分段TTS合成功能测试
3. 音频拼接功能测试
4. 字幕生成功能测试

测试结果：
- ✅ 文本分割：将104字符的文本分割为4个段落
- ✅ 分段TTS：成功生成4个音频文件，总时长12.31秒
- ✅ 音频拼接：成功拼接音频，时长正确
- ✅ 字幕生成：生成了SRT格式字幕，时间轴基于实际TTS时长

## 使用示例

### 基本使用

```python
from src.core.workflow_manager import WorkflowManager
from src.core.config import ConfigManager

# 初始化
config_manager = ConfigManager()
workflow_manager = WorkflowManager(config_manager)

# 执行视频生成流程（自动使用新的分段TTS）
video_path = workflow_manager.execute_video_generation_pipeline(
    description="介绍一款新产品",
    duration_seconds=60
)
```

### 自定义文案

```python
# 使用已有文案执行视频生成流程
script = "大家好！今天我要向大家介绍一款非常棒的产品。这个产品有什么特点呢？首先，它的设计非常精美。"

video_path = workflow_manager.execute_video_generation_pipeline_with_script(
    description="介绍一款新产品",
    duration_seconds=60,
    script=script
)
```

## 注意事项

1. **配置要求**：确保`config.toml`中`segment_by_punctuation = true`以启用新流程
2. **依赖项**：需要FFmpeg和ffprobe正确安装并在PATH中
3. **资源需求**：分段TTS会生成临时文件，确保有足够的磁盘空间
4. **网络连接**：Edge TTS需要网络连接进行语音合成

## 故障排除

### 常见问题

1. **文本分割失败**
   - 检查文本是否包含有效的标点符号
   - 调整`min_segment_length`和`max_segment_length`参数

2. **TTS合成失败**
   - 检查网络连接
   - 验证TTS语音配置是否正确
   - 查看日志中的详细错误信息

3. **音频拼接失败**
   - 确保FFmpeg正确安装
   - 检查临时文件权限
   - 验证音频文件格式兼容性

4. **字幕时间轴不准确**
   - 检查音频时长获取是否正确
   - 验证时间累加计算逻辑
   - 确认SRT时间格式正确

### 调试模式

在`config.toml`中设置：
```toml
[app]
debug = true
```

启用详细日志输出，帮助定位问题。

## 未来改进

1. **并行处理**：支持并行TTS合成以提高速度
2. **智能分割**：基于语义和语气的更智能文本分割
3. **缓存机制**：缓存常用文本段的TTS结果
4. **质量优化**：支持更高质量的音频拼接算法