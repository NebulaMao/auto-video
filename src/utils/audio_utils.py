"""
音频处理工具模块

提供音频文件时长检测、验证等通用功能。
"""

import subprocess
import re
import os
from pathlib import Path
from typing import Optional, Union
import mutagen
from ..core.exceptions import TTSError
from ..core.logger import Logger


def get_audio_duration(
    audio_path: Union[str, Path],
    logger: Logger = None,
    fallback_methods: bool = True
) -> float:
    """获取音频文件时长，支持多种检测方法

    Args:
        audio_path: 音频文件路径
        logger: 日志记录器
        fallback_methods: 是否使用备用检测方法

    Returns:
        音频时长(秒)

    Raises:
        TTSError: 无法获取时长时抛出
    """
    audio_path = Path(audio_path)

    # 验证文件存在
    if not audio_path.exists():
        raise TTSError(f"音频文件不存在: {audio_path}")

    # 验证文件大小
    if audio_path.stat().st_size == 0:
        raise TTSError(f"音频文件为空: {audio_path}")

    duration = None

    # 方法1: 使用 ffprobe 获取时长
    try:
        duration = _get_duration_with_ffprobe(audio_path, logger)
        if duration and duration > 0:
            if logger:
                logger.debug(f"使用 ffprobe 获取音频时长: {duration:.2f}秒")
            return duration
    except Exception as e:
        if logger:
            logger.warning(f"ffprobe 获取音频时长失败: {str(e)}")

    # 方法2: 使用 mutagen 获取时长
    if fallback_methods:
        try:
            duration = _get_duration_with_mutagen(audio_path, logger)
            if duration and duration > 0:
                if logger:
                    logger.debug(f"使用 mutagen 获取音频时长: {duration:.2f}秒")
                return duration
        except Exception as e:
            if logger:
                logger.warning(f"mutagen 获取音频时长失败: {str(e)}")

    # 方法3: 使用 ffmpeg 获取时长
    if fallback_methods:
        try:
            duration = _get_duration_with_ffmpeg(audio_path, logger)
            if duration and duration > 0:
                if logger:
                    logger.debug(f"使用 ffmpeg 获取音频时长: {duration:.2f}秒")
                return duration
        except Exception as e:
            if logger:
                logger.warning(f"ffmpeg 获取音频时长失败: {str(e)}")

    # 所有方法都失败
    raise TTSError(f"无法获取音频时长: {audio_path}")


def _get_duration_with_ffprobe(audio_path: Path, logger: Logger = None) -> Optional[float]:
    """使用 ffprobe 获取音频时长"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_format', '-show_streams',
            str(audio_path)
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True,
            timeout=10
        )

        # 多种正则表达式模式匹配时长
        patterns = [
            r'duration=(\d+\.?\d*)',
            r'DURATION=(\d+\.?\d*)',
            r'Duration:\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*seconds?'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, result.stdout, re.IGNORECASE)
            if matches:
                try:
                    duration = float(matches[0])
                    if duration > 0:
                        return duration
                except ValueError:
                    continue

        # 尝试从具体流信息中提取
        stream_pattern = r'\[STREAM\].*?\[\/STREAM\]'
        streams = re.findall(stream_pattern, result.stdout, re.DOTALL)

        for stream in streams:
            if 'codec_type=audio' in stream:
                duration_match = re.search(r'duration=(\d+\.?\d*)', stream, re.IGNORECASE)
                if duration_match:
                    try:
                        duration = float(duration_match.group(1))
                        if duration > 0:
                            return duration
                    except ValueError:
                        continue

        return None

    except subprocess.TimeoutExpired:
        if logger:
            logger.warning(f"ffprobe 超时: {audio_path}")
        return None
    except subprocess.CalledProcessError as e:
        if logger:
            logger.warning(f"ffprobe 执行失败: {e}")
        return None
    except Exception as e:
        if logger:
            logger.warning(f"ffprobe 异常: {e}")
        return None


def _get_duration_with_mutagen(audio_path: Path, logger: Logger = None) -> Optional[float]:
    """使用 mutagen 获取音频时长"""
    try:
        audio_file = mutagen.File(str(audio_path))
        if audio_file is not None:
            if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                duration = float(audio_file.info.length)
                if duration > 0:
                    return duration
        return None
    except Exception as e:
        if logger:
            logger.warning(f"mutagen 读取音频时长失败: {str(e)}")
        return None


def _get_duration_with_ffmpeg(audio_path: Path, logger: Logger = None) -> Optional[float]:
    """使用 ffmpeg 获取音频时长"""
    try:
        cmd = [
            'ffmpeg', '-i', str(audio_path), '-f', 'null', '-'
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=15
        )

        # 从 stderr 中解析时长信息
        error_output = result.stderr

        # 查找时长信息
        duration_pattern = r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)'
        match = re.search(duration_pattern, error_output)

        if match:
            try:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = float(match.group(3))
                duration = hours * 3600 + minutes * 60 + seconds
                if duration > 0:
                    return duration
            except ValueError:
                pass

        # 查找 time 信息
        time_pattern = r'time=(\d+\.?\d*)'
        time_matches = re.findall(time_pattern, error_output)
        if time_matches:
            try:
                # 取最后一个时间值
                duration = float(time_matches[-1])
                if duration > 0:
                    return duration
            except ValueError:
                pass

        return None

    except subprocess.TimeoutExpired:
        if logger:
            logger.warning(f"ffmpeg 超时: {audio_path}")
        return None
    except Exception as e:
        if logger:
            logger.warning(f"ffmpeg 读取音频时长失败: {str(e)}")
        return None


def validate_audio_file(audio_path: Union[str, Path], logger: Logger = None) -> bool:
    """验证音频文件是否有效

    Args:
        audio_path: 音频文件路径
        logger: 日志记录器

    Returns:
        文件是否有效
    """
    try:
        audio_path = Path(audio_path)

        # 检查文件是否存在
        if not audio_path.exists():
            if logger:
                logger.error(f"音频文件不存在: {audio_path}")
            return False

        # 检查文件大小
        if audio_path.stat().st_size == 0:
            if logger:
                logger.error(f"音频文件为空: {audio_path}")
            return False

        # 尝试获取时长
        duration = get_audio_duration(audio_path, logger, fallback_methods=False)
        return duration > 0

    except Exception as e:
        if logger:
            logger.error(f"音频文件验证失败: {str(e)}")
        return False


def estimate_text_duration(text: str, words_per_minute: float = 150) -> float:
    """根据文本估算语音时长

    Args:
        text: 文本内容
        words_per_minute: 每分钟字数

    Returns:
        估算时长(秒)
    """
    if not text:
        return 0.0

    # 对于中文，按字符计算；对于英文，按单词计算
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))

    # 中文按每分钟200字，英文按每分钟150词
    chinese_duration = chinese_chars / 200 * 60  # 秒
    english_duration = english_words / words_per_minute * 60  # 秒

    return max(chinese_duration, english_duration)