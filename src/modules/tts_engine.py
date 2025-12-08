"""
TTS语音合成模块

支持多种TTS引擎,将文本转换为语音。
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import asyncio
import edge_tts
import subprocess
import json
from ..core.exceptions import TTSError
from ..core.logger import Logger
from ..utils.text_utils import clean_xml_tags, has_xml_color_tags
from .siliconflow_tts import SiliconFlowTTS


class TTSEngine:
    """TTS语音合成引擎类
    
    封装TTS引擎,提供文本转语音功能。
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

        # 初始化具体的TTS引擎
        self.siliconflow_engine = None
        if self.engine == 'siliconflow':
            try:
                self.siliconflow_engine = SiliconFlowTTS(config, logger)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"SiliconFlow TTS 引擎初始化失败: {str(e)}")
                raise TTSError(f"SiliconFlow TTS 引擎初始化失败: {str(e)}")

        if self.logger:
            self.logger.info(f"TTS引擎初始化完成,使用引擎: {self.engine}, 语音: {self.voice}")
    
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
            self.logger.info(f"开始语音合成,文本长度: {len(clean_text)}")

        try:
            if self.engine == 'edge-tts':
                return self._synthesize_edge_tts(clean_text, output_path, **kwargs)
            elif self.engine == 'siliconflow':
                if self.siliconflow_engine:
                    return self.siliconflow_engine.synthesize(clean_text, output_path, **kwargs)
                else:
                    raise TTSError("SiliconFlow TTS 引擎未初始化")
            else:
                raise TTSError(f"不支持的TTS引擎: {self.engine}")

        except Exception as e:
            error_msg = f"语音合成失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise TTSError(error_msg)
    
    def _synthesize_edge_tts(self, text: str, output_path: str, **kwargs) -> str:
        """使用Edge TTS合成语音
        
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
        
        # 异步合成
        async def _do_synthesis():
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate_str,
                volume=volume_str,
                pitch=pitch_str
            )
            await communicate.save(str(output_file))
        
        # 运行异步函数
        asyncio.run(_do_synthesis())
        
        if self.logger:
            self.logger.info(f"语音合成完成: {output_path}")
        
        return str(output_file)
    
    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取可用的语音列表

        Returns:
            语音列表,每个语音包含名称、语言等信息
        """
        if self.engine == 'edge-tts':
            return self._get_edge_tts_voices()
        elif self.engine == 'siliconflow':
            if self.siliconflow_engine:
                return self.siliconflow_engine.get_available_voices()
            else:
                return []
        else:
            return []
    
    def _get_edge_tts_voices(self) -> List[Dict[str, str]]:
        """获取Edge TTS可用语音列表
        
        Returns:
            语音列表
        """
        async def _get_voices():
            voices = await edge_tts.list_voices()
            return voices
        
        try:
            voices = asyncio.run(_get_voices())
            
            # 过滤中文语音
            chinese_voices = [
                {
                    'name': v['ShortName'],
                    'locale': v['Locale'],
                    'gender': v['Gender']
                }
                for v in voices
                if v['Locale'].startswith('zh-')
            ]
            
            return chinese_voices
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取语音列表失败: {str(e)}")
            return []
    
    def set_voice(self, voice: str) -> None:
        """设置语音

        Args:
            voice: 语音名称
        """
        self.voice = voice
        if self.engine == 'siliconflow' and self.siliconflow_engine:
            self.siliconflow_engine.set_voice(voice)

        if self.logger:
            self.logger.info(f"语音已设置为: {voice}")
    
    def set_speed(self, rate: float) -> None:
        """设置语速
        
        Args:
            rate: 语速倍率(0.5-2.0)
        """
        self.rate = max(0.5, min(2.0, rate))
        if self.logger:
            self.logger.info(f"语速已设置为: {self.rate}")
    
    def set_volume(self, volume: float) -> None:
        """设置音量
        
        Args:
            volume: 音量倍率(0.0-2.0)
        """
        self.volume = max(0.0, min(2.0, volume))
        if self.logger:
            self.logger.info(f"音量已设置为: {self.volume}")
    
    def set_pitch(self, pitch: int) -> None:
        """设置音调
        
        Args:
            pitch: 音调偏移(-100到100 Hz)
        """
        self.pitch = max(-100, min(100, pitch))
        if self.logger:
            self.logger.info(f"音调已设置为: {self.pitch}")
    
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
        # 添加调试日志
        print(f"[DEBUG] synthesize_segments: 开始分段语音合成，共 {len(text_segments)} 个段落")
        total_input_chars = sum(len(seg) for seg in text_segments)
        print(f"[DEBUG] synthesize_segments: 输入文本总字符数={total_input_chars}")

        if self.engine == 'siliconflow' and self.siliconflow_engine:
            # 使用 SiliconFlow 的分段合成
            return self.siliconflow_engine.synthesize_segments(text_segments, output_dir, **kwargs)

        if self.logger:
            self.logger.info(f"开始分段语音合成,共 {len(text_segments)} 个段落")

        segments_info = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            for i, segment in enumerate(text_segments):
                print(f"[DEBUG] synthesize_segments: 处理段落 {i+1}/{len(text_segments)}")
                print(f"[DEBUG] synthesize_segments: 段落 {i+1} 长度={len(segment)} 内容={segment[:50]}...")

                if not segment.strip():
                    print(f"[DEBUG] synthesize_segments: 段落 {i+1} 为空，跳过")
                    continue

                # 清理XML标记（重要：确保每个段落都清理）
                clean_segment = clean_xml_tags(segment.strip())
                if has_xml_color_tags(segment):
                    print(f"[DEBUG] synthesize_segments: 段落 {i+1} 包含XML颜色标记，已清理")
                    print(f"[DEBUG] synthesize_segments: 原始文本: {segment[:30]}...")
                    print(f"[DEBUG] synthesize_segments: 清理文本: {clean_segment[:30]}...")

                # 跳过清理后为空白的段落
                if not clean_segment.strip():
                    print(f"[DEBUG] synthesize_segments: 段落 {i+1} 清理后为空，跳过")
                    continue

                # 生成分段音频文件路径
                segment_audio_path = output_path / f"segment_{i:03d}.mp3"
                print(f"[DEBUG] synthesize_segments: 段落 {i+1} 音频路径={segment_audio_path}")

                # 合成该段语音（使用清理后的文本）
                print(f"[DEBUG] synthesize_segments: 开始合成段落 {i+1} 的语音")
                try:
                    self.synthesize(clean_segment, str(segment_audio_path), **kwargs)
                    print(f"[DEBUG] synthesize_segments: 段落 {i+1} 语音合成成功")
                except Exception as e:
                    print(f"[DEBUG] synthesize_segments: 段落 {i+1} 语音合成失败: {str(e)}")
                    raise

                # 获取音频时长
                print(f"[DEBUG] synthesize_segments: 获取段落 {i+1} 音频时长")
                try:
                    duration = self.get_audio_duration(str(segment_audio_path))
                    print(f"[DEBUG] synthesize_segments: 段落 {i+1} 音频时长={duration:.2f}秒")
                except Exception as e:
                    print(f"[DEBUG] synthesize_segments: 获取段落 {i+1} 音频时长失败: {str(e)}")
                    raise

                segments_info.append({
                    'index': i,
                    'text': clean_segment,  # 使用清理后的文本
                    'original_text': segment.strip(),  # 保留原始文本用于字幕
                    'audio_path': str(segment_audio_path),
                    'duration': duration
                })

                if self.logger:
                    self.logger.info(f"段落 {i+1} 合成完成,时长: {duration:.2f}秒")

            # 统计最终结果
            total_duration = sum(seg['duration'] for seg in segments_info)
            total_output_chars = sum(len(seg['text']) for seg in segments_info)
            print(f"[DEBUG] synthesize_segments: 分段语音合成完成")
            print(f"[DEBUG] synthesize_segments: 成功合成 {len(segments_info)} 个段落")
            print(f"[DEBUG] synthesize_segments: 输出文本总字符数={total_output_chars}")
            print(f"[DEBUG] synthesize_segments: 总音频时长={total_duration:.2f}秒")

            if total_output_chars < total_input_chars * 0.9:
                print(f"[DEBUG] synthesize_segments: 警告！输出文本字符数({total_output_chars})明显少于输入({total_input_chars})")

            if self.logger:
                self.logger.info(f"分段语音合成完成,总时长: {total_duration:.2f}秒")

            return segments_info

        except Exception as e:
            error_msg = f"分段语音合成失败: {str(e)}"
            print(f"[DEBUG] synthesize_segments: 异常 - {error_msg}")
            if self.logger:
                self.logger.error(error_msg)
            raise TTSError(error_msg)

    def get_available_models(self) -> List[Dict[str, str]]:
        """获取可用的模型列表（仅 SiliconFlow 支持）

        Returns:
            模型列表
        """
        if self.engine == 'siliconflow' and self.siliconflow_engine:
            return self.siliconflow_engine.get_available_models()
        else:
            return []

    def set_model(self, model: str) -> None:
        """设置模型（仅 SiliconFlow 支持）

        Args:
            model: 模型名称
        """
        if self.engine == 'siliconflow' and self.siliconflow_engine:
            self.siliconflow_engine.set_model(model)
            if self.logger:
                self.logger.info(f"SiliconFlow TTS 模型已设置为: {model}")

    def set_gain(self, gain: float) -> None:
        """设置音量增益（仅 SiliconFlow 支持）

        Args:
            gain: 音量增益(-10到10)
        """
        if self.engine == 'siliconflow' and self.siliconflow_engine:
            self.siliconflow_engine.set_gain(gain)
            if self.logger:
                self.logger.info(f"SiliconFlow TTS 音量增益已设置为: {gain}")

    def test_connection(self) -> bool:
        """测试 API 连接（仅 SiliconFlow 支持）

        Returns:
            连接是否成功
        """
        if self.engine == 'siliconflow' and self.siliconflow_engine:
            return self.siliconflow_engine.test_connection()
        else:
            return True  # Edge TTS 不需要连接测试