"""
改进版TTS语音合成模块 - 添加重试机制和错误处理

修复Edge TTS 401错误的改进方案
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import asyncio
import edge_tts
import subprocess
import json
import time
from ..core.exceptions import TTSError
from ..core.logger import Logger
from ..utils.text_utils import clean_xml_tags, has_xml_color_tags


class TTSEngineImproved:
    """改进版TTS语音合成引擎类

    添加了重试机制和更好的错误处理
    """

    def __init__(self, config: Dict[str, Any], logger: Logger = None):
        """初始化TTS引擎

        Args:
            config: TTS配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger

        self.engine = config.get('engine', 'edge-tts')
        self.voice = config.get('voice', 'zh-CN-XiaoxiaoNeural')
        self.rate = config.get('rate', 1.0)
        self.volume = config.get('volume', 1.0)
        self.pitch = config.get('pitch', 0)

        # 重试配置
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 2)  # 秒

        if self.logger:
            self.logger.info(f"改进版TTS引擎初始化完成,使用引擎: {self.engine}, 语音: {self.voice}")
            self.logger.info(f"重试配置: 最大重试次数={self.max_retries}, 重试延迟={self.retry_delay}秒")

    def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        """合成语音（带重试机制）

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
            self.logger.info(f"开始语音合成,文本长度: {len(clean_text)}")

        # 重试机制
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = self.retry_delay * (2 ** (attempt - 1))  # 指数退避
                    if self.logger:
                        self.logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

                if self.logger and attempt > 0:
                    self.logger.info(f"第 {attempt + 1}/{self.max_retries} 次尝试语音合成...")

                if self.engine == 'edge-tts':
                    return self._synthesize_edge_tts_with_retry(clean_text, output_path, **kwargs)
                else:
                    raise TTSError(f"不支持的TTS引擎: {self.engine}")

            except Exception as e:
                last_error = e
                error_msg = str(e)

                if self.logger:
                    self.logger.warning(f"第 {attempt + 1} 次尝试失败: {error_msg}")

                # 检查是否是401错误
                if "401" in error_msg or "Invalid response status" in error_msg:
                    if self.logger:
                        self.logger.warning("检测到Edge TTS 401认证错误，这可能是微软服务端问题")

                    # 如果是最后一次尝试，提供详细的错误信息
                    if attempt == self.max_retries - 1:
                        if self.logger:
                            self.logger.error("所有重试均失败，Edge TTS服务可能暂时不可用")
                        break
                else:
                    # 其他错误，直接抛出
                    if attempt == self.max_retries - 1:
                        break

        # 所有重试都失败了
        error_msg = f"语音合成失败（已重试{self.max_retries}次）: {str(last_error)}"
        if self.logger:
            self.logger.error(error_msg)
            self.logger.error("可能的原因：")
            self.logger.error("1. Edge TTS服务暂时不可用（微软服务端问题）")
            self.logger.error("2. 网络连接问题")
            self.logger.error("3. 防火墙阻止WebSocket连接")
            self.logger.error("解决方案：")
            self.logger.error("1. 稍后重试（通常几分钟到几小时后恢复）")
            self.logger.error("2. 检查网络连接")
            self.logger.error("3. 尝试使用VPN或代理")
        raise TTSError(error_msg)

    def _synthesize_edge_tts_with_retry(self, text: str, output_path: str, **kwargs) -> str:
        """使用Edge TTS合成语音（单次尝试）

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
        voice = kwargs.get('voice', self.voice)
        rate = kwargs.get('rate', self.rate)
        volume = kwargs.get('volume', self.volume)
        pitch = kwargs.get('pitch', self.pitch)

        # 格式化速度和音量参数
        rate_str = f"{int((rate - 1) * 100):+d}%"
        volume_str = f"{int((volume - 1) * 100):+d}%"
        pitch_str = f"{int(pitch):+d}Hz"

        # 异步合成（添加超时控制）
        async def _do_synthesis():
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate_str,
                volume=volume_str,
                pitch=pitch_str
            )

            # 使用超时控制
            try:
                await asyncio.wait_for(
                    communicate.save(str(output_file)),
                    timeout=30.0  # 30秒超时
                )
            except asyncio.TimeoutError:
                raise TTSError("语音合成超时（30秒）")

        # 运行异步函数
        asyncio.run(_do_synthesis())

        if self.logger:
            self.logger.info(f"语音合成完成: {output_path}")

        return str(output_file)

    def synthesize_segments(self, text_segments: List[str], output_dir: str, **kwargs) -> List[Dict[str, Any]]:
        """分段合成语音（带重试）

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
            self.logger.info(f"开始分段语音合成,共 {len(text_segments)} 个段落")

        segments_info = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        failed_segments = []

        try:
            for i, segment in enumerate(text_segments):
                if not segment.strip():
                    continue

                # 清理XML标记
                clean_segment = clean_xml_tags(segment.strip())

                if not clean_segment.strip():
                    continue

                # 生成分段音频文件路径
                segment_audio_path = output_path / f"segment_{i:03d}.mp3"

                # 合成该段语音（使用带重试的synthesize方法）
                try:
                    self.synthesize(clean_segment, str(segment_audio_path), **kwargs)
                except TTSError as e:
                    failed_segments.append((i, segment, str(e)))
                    if self.logger:
                        self.logger.error(f"段落 {i+1} 合成失败，继续处理下一个段落")
                    continue

                # 获取音频时长
                try:
                    duration = self.get_audio_duration(str(segment_audio_path))
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"无法获取段落 {i+1} 的音频时长: {e}")
                    duration = 0.0

                segments_info.append({
                    'index': i,
                    'text': clean_segment,
                    'original_text': segment.strip(),
                    'audio_path': str(segment_audio_path),
                    'duration': duration
                })

                if self.logger:
                    self.logger.info(f"段落 {i+1}/{len(text_segments)} 合成完成,时长: {duration:.2f}秒")

            # 检查是否有失败的段落
            if failed_segments:
                error_summary = f"部分段落合成失败: {len(failed_segments)}/{len(text_segments)}"
                if self.logger:
                    self.logger.error(error_summary)
                    for idx, seg, err in failed_segments:
                        self.logger.error(f"  段落 {idx+1}: {seg[:50]}... - {err}")

                # 如果所有段落都失败了，抛出错误
                if len(failed_segments) == len(text_segments):
                    raise TTSError("所有段落合成均失败")

            # 统计最终结果
            total_duration = sum(seg['duration'] for seg in segments_info)
            if self.logger:
                self.logger.info(f"分段语音合成完成,成功 {len(segments_info)}/{len(text_segments)} 个段落,总时长: {total_duration:.2f}秒")

            return segments_info

        except TTSError:
            raise
        except Exception as e:
            error_msg = f"分段语音合成失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise TTSError(error_msg)

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

    # 其他方法保持与原TTSEngine相同
    def set_voice(self, voice: str) -> None:
        """设置语音"""
        self.voice = voice
        if self.logger:
            self.logger.info(f"语音已设置为: {voice}")

    def set_speed(self, rate: float) -> None:
        """设置语速"""
        self.rate = max(0.5, min(2.0, rate))
        if self.logger:
            self.logger.info(f"语速已设置为: {self.rate}")

    def set_volume(self, volume: float) -> None:
        """设置音量"""
        self.volume = max(0.0, min(2.0, volume))
        if self.logger:
            self.logger.info(f"音量已设置为: {self.volume}")

    def set_pitch(self, pitch: int) -> None:
        """设置音调"""
        self.pitch = max(-100, min(100, pitch))
        if self.logger:
            self.logger.info(f"音调已设置为: {self.pitch}")
