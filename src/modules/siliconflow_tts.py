"""
SiliconFlow TTS 语音合成模块

基于 SiliconFlow API 的文本转语音服务。
"""

import requests
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
import subprocess
from ..core.exceptions import TTSError
from ..core.logger import Logger
from ..utils.text_utils import clean_xml_tags, has_xml_color_tags


class SiliconFlowTTS:
    """SiliconFlow TTS 语音合成引擎类

    基于 SiliconFlow API 的文本转语音服务。
    """

    def __init__(self, config: Dict[str, Any], logger: Logger = None):
        """初始化 SiliconFlow TTS 引擎

        Args:
            config: TTS配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger

        # SiliconFlow API 配置
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', 'https://api.siliconflow.cn/v1')
        self.model = config.get('model', 'IndexTeam/IndexTTS-2')
        self.voice = config.get('voice', 'fishaudio/fish-speech-1.4:david')
        self.response_format = config.get('response_format', 'mp3')
        self.sample_rate = config.get('sample_rate', 32000)
        self.speed = config.get('speed', 1.0)
        self.gain = config.get('gain', 0)
        self.stream = config.get('stream', False)
        self.timeout = config.get('timeout', 30)

        # 验证配置
        if not self.api_key:
            raise TTSError("SiliconFlow API key 未配置")

        if self.logger:
            self.logger.info(f"SiliconFlow TTS 引擎初始化完成")
            self.logger.info(f"模型: {self.model}")
            self.logger.info(f"语音: {self.voice}")

    def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        """合成语音

        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径
            **kwargs: 额外的合成参数

        Returns:
            生成的音频文件路径

        Raises:
            TTSError: 语音合成失败时抛出
        """
        # 清理XML标记，避免TTS读出颜色标记
        clean_text = clean_xml_tags(text)

        if self.logger:
            if has_xml_color_tags(text):
                self.logger.info(f"检测到XML颜色标记，已清理文本进行语音合成")
                self.logger.info(f"原始文本: {text[:50]}...")
                self.logger.info(f"清理文本: {clean_text[:50]}...")
            self.logger.info(f"开始 SiliconFlow TTS 语音合成,文本长度: {len(clean_text)}")

        try:
            return self._synthesize_siliconflow(clean_text, output_path, **kwargs)

        except Exception as e:
            error_msg = f"SiliconFlow TTS 语音合成失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise TTSError(error_msg)

    def _synthesize_siliconflow(self, text: str, output_path: str, **kwargs) -> str:
        """使用 SiliconFlow API 合成语音

        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径
            **kwargs: 额外的合成参数

        Returns:
            生成的音频文件路径
        """
        # 确保输出目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 获取参数
        model = kwargs.get('model', self.model)
        voice = kwargs.get('voice', self.voice)
        response_format = kwargs.get('response_format', self.response_format)
        sample_rate = kwargs.get('sample_rate', self.sample_rate)
        speed = kwargs.get('speed', self.speed)
        gain = kwargs.get('gain', self.gain)

        # 构建请求数据
        data = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": response_format,
            "sample_rate": sample_rate,
            "speed": speed,
            "gain": gain,
            "stream": False  # 对于文件输出，不使用流式
        }

        # 设置请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 发送请求
        url = f"{self.base_url}/audio/speech"

        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )

            # 检查响应状态
            if response.status_code == 200:
                # 保存音频文件
                with open(output_file, 'wb') as f:
                    f.write(response.content)

                if self.logger:
                    self.logger.info(f"SiliconFlow TTS 语音合成完成: {output_path}")

                return str(output_file)
            else:
                error_info = {
                    "status_code": response.status_code,
                    "text": response.text
                }
                raise TTSError(f"SiliconFlow API 请求失败: {error_info}")

        except requests.exceptions.RequestException as e:
            raise TTSError(f"SiliconFlow API 请求异常: {str(e)}")

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取可用的语音列表

        Returns:
            语音列表,每个语音包含名称、语言等信息
        """
        # SiliconFlow 预设语音列表
        available_voices = [
            {
                'name': 'fnlp/MOSS-TTSD-v0.5:alex',
                'display_name': 'Alex',
                'language': 'zh-CN',
                'gender': 'male',
                'description': '男声'
            },
            {
                'name': 'fnlp/MOSS-TTSD-v0.5:emma',
                'display_name': 'Emma',
                'language': 'zh-CN',
                'gender': 'female',
                'description': '女声'
            },
            {
                'name': 'fnlp/MOSS-TTSD-v0.5:brian',
                'display_name': 'Brian',
                'language': 'en-US',
                'gender': 'male',
                'description': '英文男声'
            },
            {
                'name': 'fnlp/MOSS-TTSD-v0.5:alice',
                'display_name': 'Alice',
                'language': 'en-US',
                'gender': 'female',
                'description': '英文女声'
            }
        ]

        return available_voices

    def get_available_models(self) -> List[Dict[str, str]]:
        """获取可用的模型列表

        Returns:
            模型列表
        """
        available_models = [
            {
                'name': 'fnlp/MOSS-TTSD-v0.5',
                'display_name': 'MOSS-TTSD-v0.5',
                'description': '支持中英双语的TTS模型',
                'languages': ['zh-CN', 'en-US'],
                'features': ['中英双语', '声音克隆', '多人对话']
            }
        ]

        return available_models

    def set_voice(self, voice: str) -> None:
        """设置语音

        Args:
            voice: 语音名称
        """
        self.voice = voice
        if self.logger:
            self.logger.info(f"SiliconFlow TTS 语音已设置为: {voice}")

    def set_model(self, model: str) -> None:
        """设置模型

        Args:
            model: 模型名称
        """
        self.model = model
        if self.logger:
            self.logger.info(f"SiliconFlow TTS 模型已设置为: {model}")

    def set_speed(self, speed: float) -> None:
        """设置语速

        Args:
            speed: 语速倍率(0.25-4.0)
        """
        self.speed = max(0.25, min(4.0, speed))
        if self.logger:
            self.logger.info(f"SiliconFlow TTS 语速已设置为: {self.speed}")

    def set_gain(self, gain: float) -> None:
        """设置音量增益

        Args:
            gain: 音量增益(-10到10)
        """
        self.gain = max(-10, min(10, gain))
        if self.logger:
            self.logger.info(f"SiliconFlow TTS 音量增益已设置为: {self.gain}")

    def get_audio_duration(self, audio_path: str) -> float:
        """获取音频文件时长

        Args:
            audio_path: 音频文件路径

        Returns:
            音频时长(秒)

        Raises:
            TTSError: 获取时长失败时抛出
        """
        try:
            # 使用ffprobe获取音频时长
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_format', '-show_streams',
                audio_path
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )

            # 解析输出获取时长
            for line in result.stdout.split('\n'):
                if line.startswith('duration='):
                    return float(line.split('=')[1])

            # 如果没有找到duration，尝试从stream中获取
            for line in result.stdout.split('\n'):
                if 'duration=' in line.lower():
                    duration_str = line.split('duration=')[1].strip()
                    return float(duration_str)

            raise TTSError(f"无法获取音频时长: {audio_path}")

        except Exception as e:
            error_msg = f"获取音频时长失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise TTSError(error_msg)

    def synthesize_segments(self, text_segments: List[str], output_dir: str, **kwargs) -> List[Dict[str, Any]]:
        """分段合成语音

        Args:
            text_segments: 文本段落列表
            output_dir: 输出目录
            **kwargs: 额外的合成参数

        Returns:
            每段音频的信息列表，包含文件路径和时长

        Raises:
            TTSError: 语音合成失败时抛出
        """
        if self.logger:
            self.logger.info(f"开始 SiliconFlow TTS 分段语音合成,共 {len(text_segments)} 个段落")

        segments_info = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            for i, segment in enumerate(text_segments):
                if not segment.strip():
                    continue

                # 清理XML标记
                clean_segment = clean_xml_tags(segment.strip())

                # 跳过清理后为空白的段落
                if not clean_segment.strip():
                    continue

                # 生成分段音频文件路径
                segment_audio_path = output_path / f"segment_{i:03d}.mp3"

                # 合成该段语音
                self.synthesize(clean_segment, str(segment_audio_path), **kwargs)

                # 获取音频时长
                duration = self.get_audio_duration(str(segment_audio_path))

                segments_info.append({
                    'index': i,
                    'text': clean_segment,
                    'original_text': segment.strip(),
                    'audio_path': str(segment_audio_path),
                    'duration': duration
                })

                if self.logger:
                    self.logger.info(f"段落 {i+1} 合成完成,时长: {duration:.2f}秒")

            total_duration = sum(seg['duration'] for seg in segments_info)
            if self.logger:
                self.logger.info(f"SiliconFlow TTS 分段语音合成完成,总时长: {total_duration:.2f}秒")

            return segments_info

        except Exception as e:
            error_msg = f"SiliconFlow TTS 分段语音合成失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise TTSError(error_msg)

    def test_connection(self) -> bool:
        """测试 API 连接

        Returns:
            连接是否成功
        """
        try:
            # 使用简短文本测试
            test_text = "这是一个测试。"
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                test_output = Path(temp_dir) / "test_siliconflow_tts.mp3"
                self.synthesize(test_text, str(test_output))

            if self.logger:
                self.logger.info("SiliconFlow API 连接测试成功")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"SiliconFlow API 连接测试失败: {str(e)}")
            return False