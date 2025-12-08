"""
FFmpeg 封装工具类模块

提供完整的 FFmpeg 功能封装,用于替代 MoviePy。
"""

import subprocess
import json
import tempfile
import os
import shutil
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
from contextlib import contextmanager

from ..core.logger import Logger
from ..core.exceptions import VideoProcessingError


class FFmpegError(VideoProcessingError):
    """FFmpeg 相关错误"""
    
    def __init__(self, message: str, command: List[str] = None, return_code: int = None):
        """初始化 FFmpeg 错误
        
        Args:
            message: 错误消息
            command: 执行的命令
            return_code: 返回码
        """
        self.command = command
        self.return_code = return_code
        super().__init__(message, error_code="FFMPEG_ERROR")
    
    def __str__(self) -> str:
        """返回错误的字符串表示"""
        if self.command:
            return f"{self.message} (命令: {' '.join(self.command)})"
        return self.message


class FFmpegErrorHandler:
    """FFmpeg 错误处理器"""
    
    def __init__(self, logger: Logger = None):
        """初始化错误处理器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger
    
    def execute_command(self, cmd: List[str], timeout: int = None, **kwargs) -> str:
        """执行 FFmpeg 命令并处理错误
        
        Args:
            cmd: 命令列表
            timeout: 超时时间(秒)
            **kwargs: subprocess.Popen 的其他参数
            
        Returns:
            命令的标准输出
            
        Raises:
            FFmpegError: 命令执行失败
        """
        try:
            if self.logger:
                self.logger.debug(f"执行 FFmpeg 命令: {' '.join(cmd)}")
            
            # 执行命令（指定UTF-8编码，避免Windows GBK编码错误）
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',  # 遇到无法解码的字符时用替换字符代替
                **kwargs
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                raise FFmpegError("FFmpeg 命令执行超时", cmd, -2)
            
            # 检查返回码
            if process.returncode != 0:
                error_msg = self._parse_ffmpeg_error(stderr)
                if self.logger:
                    self.logger.error(f"FFmpeg 命令失败: {error_msg}")
                raise FFmpegError(f"FFmpeg 命令执行失败: {error_msg}", cmd, process.returncode)
            
            return stdout
            
        except FileNotFoundError:
            raise FFmpegError("FFmpeg 未安装或不在 PATH 中", cmd, -1)
        except Exception as e:
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"执行 FFmpeg 命令时发生未知错误: {str(e)}", cmd, -3)
    
    def _parse_ffmpeg_error(self, stderr: str) -> str:
        """解析 FFmpeg 错误信息
        
        Args:
            stderr: 标准错误输出
            
        Returns:
            解析后的错误消息
        """
        # 常见错误模式匹配
        error_patterns = [
            r"No such file or directory",
            r"Invalid data found when processing input",
            r"Conversion failed",
            r"Unsupported codec",
            r"Permission denied",
            r"Invalid argument",
            r"Output file .* already exists"
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, stderr, re.IGNORECASE):
                # 提取包含错误的行
                for line in stderr.split('\n'):
                    if re.search(pattern, line, re.IGNORECASE):
                        return line.strip()
        
        # 如果没有匹配到已知模式,返回最后几行非空错误
        lines = [line.strip() for line in stderr.strip().split('\n') if line.strip()]
        if lines:
            return lines[-1]
        return "未知错误"


class TempFileManager:
    """临时文件管理器"""
    
    def __init__(self, temp_dir: str = None, max_age_hours: int = 24, max_size_mb: int = 1024):
        """初始化临时文件管理器
        
        Args:
            temp_dir: 临时目录路径
            max_age_hours: 临时文件最大保存时间(小时)
            max_size_mb: 临时目录最大大小(MB)
        """
        self.temp_dir = temp_dir or os.path.join(tempfile.gettempdir(), 'autovideo_ffmpeg')
        self.max_age_hours = max_age_hours
        self.max_size_mb = max_size_mb
        
        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 启动时清理旧文件
        self.cleanup_old_files()
    
    @contextmanager
    def create_temp_file(self, suffix: str = '', prefix: str = 'tmp_'):
        """创建临时文件上下文管理器
        
        Args:
            suffix: 文件后缀
            prefix: 文件前缀
            
        Yields:
            临时文件路径
        """
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=self.temp_dir)
        os.close(fd)  # 关闭文件描述符,但保留文件
        
        try:
            yield path
        finally:
            # 确保文件被删除
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass  # 忽略删除错误
    
    def cleanup_old_files(self):
        """清理过期的临时文件"""
        now = time.time()
        max_age_seconds = self.max_age_hours * 3600
        
        for root, dirs, files in os.walk(self.temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                except Exception:
                    pass  # 忽略删除错误
    
    def get_temp_dir_size(self) -> int:
        """获取临时目录大小
        
        Returns:
            目录大小(MB)
        """
        total_size = 0
        for root, dirs, files in os.walk(self.temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except Exception:
                    pass
        return total_size // (1024 * 1024)  # 转换为MB
    
    def cleanup(self):
        """清理所有临时文件"""
        try:
            shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir, exist_ok=True)
        except Exception:
            pass


class VideoInfoExtractor:
    """视频信息提取器"""
    
    def __init__(self, error_handler: FFmpegErrorHandler):
        """初始化视频信息提取器
        
        Args:
            error_handler: 错误处理器
        """
        self.error_handler = error_handler
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典,包含 duration, fps, width, height, has_audio 等
            
        Raises:
            FFmpegError: 获取信息失败
        """
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        
        result = self.error_handler.execute_command(cmd)
        return self._parse_video_info(result)
    
    def _parse_video_info(self, probe_output: str) -> Dict[str, Any]:
        """解析 ffprobe 输出
        
        Args:
            probe_output: ffprobe 的 JSON 输出
            
        Returns:
            解析后的视频信息
        """
        data = json.loads(probe_output)
        
        # 查找视频流和音频流
        video_stream = next((s for s in data.get('streams', []) if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in data.get('streams', []) if s['codec_type'] == 'audio'), None)
        
        info = {
            'duration': float(data.get('format', {}).get('duration', 0)),
            'fps': self._parse_fps(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0,
            'width': int(video_stream.get('width', 0)) if video_stream else 0,
            'height': int(video_stream.get('height', 0)) if video_stream else 0,
            'size': [int(video_stream.get('width', 0)), int(video_stream.get('height', 0))] if video_stream else [0, 0],
            'has_audio': audio_stream is not None,
            'video_codec': video_stream.get('codec_name', '') if video_stream else '',
            'audio_codec': audio_stream.get('codec_name', '') if audio_stream else '',
            'bit_rate': int(data.get('format', {}).get('bit_rate', 0))
        }
        
        return info
    
    def _parse_fps(self, fps_str: str) -> float:
        """解析帧率字符串
        
        Args:
            fps_str: 帧率字符串,如 "30/1"
            
        Returns:
            帧率值
        """
        try:
            parts = fps_str.split('/')
            if len(parts) == 2:
                num, den = float(parts[0]), float(parts[1])
                return num / den if den != 0 else 0
            return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return 0
    
    def get_duration(self, video_path: str) -> float:
        """获取视频时长
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频时长(秒)
        """
        info = self.get_video_info(video_path)
        return info['duration']
    
    def get_fps(self, video_path: str) -> float:
        """获取视频帧率
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频帧率
        """
        info = self.get_video_info(video_path)
        return info['fps']
    
    def get_resolution(self, video_path: str) -> Tuple[int, int]:
        """获取视频分辨率
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            (宽度, 高度)元组
        """
        info = self.get_video_info(video_path)
        return (info['width'], info['height'])
    
    def has_audio(self, video_path: str) -> bool:
        """检测视频是否有音频
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            是否有音频轨道
        """
        info = self.get_video_info(video_path)
        return info['has_audio']


class VideoProcessor:
    """视频处理器"""

    def __init__(self, error_handler: FFmpegErrorHandler, temp_manager: TempFileManager, logger=None):
        """初始化视频处理器

        Args:
            error_handler: 错误处理器
            temp_manager: 临时文件管理器
            logger: 日志记录器
        """
        self.error_handler = error_handler
        self.temp_manager = temp_manager
        self.logger = logger
    
    def resize_video(
        self,
        video_path: str,
        output_path: str,
        width: int = None,
        height: int = None,
        keep_aspect_ratio: bool = True,
        reencode: bool = True,
        video_codec: str = 'libx264',
        audio_codec: str = 'aac'
    ) -> str:
        """调整视频尺寸
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            width: 目标宽度
            height: 目标高度
            keep_aspect_ratio: 是否保持宽高比
            reencode: 是否重新编码（默认True，确保兼容性）
            video_codec: 视频编码器
            audio_codec: 音频编码器
            
        Returns:
            输出视频路径
            
        Raises:
            FFmpegError: 处理失败
        """
        # 计算目标尺寸
        if width and height:
            if keep_aspect_ratio:
                scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            else:
                scale_filter = f"scale={width}:{height}"
        elif width:
            scale_filter = f"scale={width}:-2" if keep_aspect_ratio else f"scale={width}:ih"
        elif height:
            scale_filter = f"scale=-2:{height}" if keep_aspect_ratio else f"scale=iw:{height}"
        else:
            raise ValueError("必须指定 width 或 height")
        
        if reencode:
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', scale_filter,
                '-c:v', video_codec,    # 重新编码视频
                '-c:a', audio_codec,    # 重新编码音频
                '-pix_fmt', 'yuv420p',  # 标准化像素格式
                '-y',  # 覆盖输出文件
                output_path
            ]
        else:
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', scale_filter,
                '-c:a', 'copy',  # 保持音频不变
                '-y',  # 覆盖输出文件
                output_path
            ]
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def crop_video(
        self,
        video_path: str,
        output_path: str,
        x: int,
        y: int,
        width: int,
        height: int,
        reencode: bool = True,
        video_codec: str = 'libx264',
        audio_codec: str = 'aac'
    ) -> str:
        """裁剪视频
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            x: 裁剪起始 x 坐标
            y: 裁剪起始 y 坐标
            width: 裁剪宽度
            height: 裁剪高度
            reencode: 是否重新编码（默认True，确保兼容性）
            video_codec: 视频编码器
            audio_codec: 音频编码器
            
        Returns:
            输出视频路径
        """
        if reencode:
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', f"crop={width}:{height}:{x}:{y}",
                '-c:v', video_codec,    # 重新编码视频
                '-c:a', audio_codec,    # 重新编码音频
                '-pix_fmt', 'yuv420p',  # 标准化像素格式
                '-y',
                output_path
            ]
        else:
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', f"crop={width}:{height}:{x}:{y}",
                '-c:a', 'copy',
                '-y',
                output_path
            ]
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def cut_video(
        self,
        video_path: str,
        output_path: str,
        start_time: float,
        end_time: float = None,
        duration: float = None,
        reencode: bool = False,
        video_codec: str = 'libx264',
        audio_codec: str = 'aac'
    ) -> str:
        """截取视频片段
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            start_time: 开始时间(秒)
            end_time: 结束时间(秒)
            duration: 持续时间(秒),与 end_time 二选一
            reencode: 是否重新编码（默认False）
            video_codec: 视频编码器
            audio_codec: 音频编码器
            
        Returns:
            输出视频路径
        """
        cmd = ['ffmpeg', '-i', video_path, '-ss', str(start_time)]
        
        # 添加持续时间
        if duration is not None:
            cmd.extend(['-t', str(duration)])
        elif end_time is not None:
            cmd.extend(['-t', str(end_time - start_time)])
        
        # 添加编码参数
        if reencode:
            cmd.extend([
                '-c:v', video_codec,    # 重新编码视频
                '-c:a', audio_codec,    # 重新编码音频
                '-pix_fmt', 'yuv420p',  # 标准化像素格式
                '-avoid_negative_ts', '1',  # 避免负时间戳
                '-y',
                output_path
            ])
        else:
            cmd.extend([
                '-c', 'copy',  # 使用流复制,避免重新编码
                '-avoid_negative_ts', '1',  # 避免负时间戳
                '-y',
                output_path
            ])
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def concat_videos(self, video_paths: List[str], output_path: str,
                     reencode: bool = True, video_codec: str = 'libx264',
                     audio_codec: str = 'aac', pixel_format: str = 'yuv420p') -> str:
        """拼接多个视频

        Args:
            video_paths: 输入视频路径列表
            output_path: 输出视频路径
            reencode: 是否重新编码（默认True，提高兼容性）
            video_codec: 视频编码器
            audio_codec: 音频编码器
            pixel_format: 像素格式

        Returns:
            输出视频路径
        """
        if self.logger:
            self.logger.info(f"开始拼接视频: {len(video_paths)}个文件 -> {output_path}")
            self.logger.debug(f"输入文件: {video_paths}")

        # 验证输入文件
        for i, path in enumerate(video_paths):
            if not os.path.exists(path):
                raise FFmpegError(f"输入视频文件不存在: {path}")
            if not os.path.isfile(path):
                raise FFmpegError(f"输入路径不是文件: {path}")
            if os.path.getsize(path) == 0:
                raise FFmpegError(f"输入视频文件为空: {path}")

        # 确保输出目录存在并使用绝对路径
        output_path = os.path.abspath(output_path)
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 创建临时文件列表 - 使用更robust的格式
        with self.temp_manager.create_temp_file(suffix='.txt') as list_file:
            if self.logger:
                self.logger.debug(f"创建concat文件: {list_file}")

            # 使用UTF-8编码创建concat文件
            with open(list_file, 'w', encoding='utf-8') as f:
                for path in video_paths:
                    # 使用绝对路径避免路径问题
                    abs_path = os.path.abspath(path)

                    # Windows路径特殊处理：FFmpeg兼容格式
                    if os.name == 'nt':  # Windows系统
                        # 将反斜杠转为正斜杠并使用引号包围
                        normalized_path = abs_path.replace('\\', '/')
                        f.write(f"file '{normalized_path}'\n")
                    else:
                        # Unix-like系统使用正斜杠
                        abs_path = abs_path.replace('\\', '/')
                        f.write(f"file '{abs_path}'\n")

            # 记录concat文件内容用于调试
            if self.logger:
                try:
                    with open(list_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.logger.debug(f"Concat文件内容:\n{content}")
                except Exception as e:
                    self.logger.warning(f"无法读取concat文件内容: {e}")

            if reencode:
                # 重新编码以确保兼容性
                cmd = [
                    'ffmpeg', '-f', 'concat',
                    '-safe', '0',  # 允许不安全的文件路径
                    '-i', list_file,
                    '-c:v', video_codec,    # 重新编码视频
                    '-c:a', audio_codec,    # 重新编码音频
                    '-pix_fmt', pixel_format,  # 标准化像素格式
                    '-r', '30',             # 标准化帧率
                    '-y',
                    output_path
                ]
            else:
                # 使用流复制（仅用于兼容格式）
                cmd = [
                    'ffmpeg', '-f', 'concat',
                    '-safe', '0',  # 允许不安全的文件路径
                    '-i', list_file,
                    '-c', 'copy',
                    '-y',
                    output_path
                ]

            if self.logger:
                self.logger.debug(f"执行FFmpeg命令: {' '.join(cmd)}")

            try:
                self.error_handler.execute_command(cmd)
                if self.logger:
                    self.logger.info(f"视频拼接成功: {output_path}")
            except FFmpegError as e:
                if self.logger:
                    self.logger.error(f"视频拼接失败: {e}")
                    # 提供诊断信息
                    self.logger.error(f"命令: {e.command}")
                    self.logger.error(f"返回码: {e.return_code}")
                raise

        return output_path
    
    def image_to_video(
        self,
        image_path: str,
        output_path: str,
        duration: float = 5.0,
        fps: int = 25
    ) -> str:
        """图片转视频
        
        Args:
            image_path: 输入图片路径
            output_path: 输出视频路径
            duration: 视频时长(秒)
            fps: 帧率
            
        Returns:
            输出视频路径
        """
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', image_path,
            '-c:v', 'libx264',
            '-t', str(duration),
            '-pix_fmt', 'yuv420p',
            '-r', str(fps),
            '-y',
            output_path
        ]
        
        self.error_handler.execute_command(cmd)
        return output_path


class AudioProcessor:
    """音频处理器"""
    
    def __init__(self, error_handler: FFmpegErrorHandler, temp_manager: TempFileManager):
        """初始化音频处理器
        
        Args:
            error_handler: 错误处理器
            temp_manager: 临时文件管理器
        """
        self.error_handler = error_handler
        self.temp_manager = temp_manager
        # 创建视频信息提取器实例
        self.info_extractor = VideoInfoExtractor(error_handler)
    
    def extract_audio(
        self,
        video_path: str,
        audio_path: str,
        audio_format: str = 'mp3',
        bitrate: str = '128k'
    ) -> str:
        """从视频提取音频
        
        Args:
            video_path: 输入视频路径
            audio_path: 输出音频路径
            audio_format: 音频格式
            bitrate: 音频比特率
            
        Returns:
            输出音频路径
        """
        codec_map = {
            'mp3': 'libmp3lame',
            'aac': 'aac',
            'wav': 'pcm_s16le',
            'flac': 'flac',
            'ogg': 'libvorbis'
        }
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn',  # 禁用视频流
            '-acodec', codec_map.get(audio_format, 'libmp3lame'),
            '-ab', bitrate,
            '-y',
            audio_path
        ]
        
        self.error_handler.execute_command(cmd)
        return audio_path
    
    def merge_audio_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_start: float = 0,
        video_start: float = 0
    ) -> str:
        """合并音频和视频
        
        Args:
            video_path: 输入视频路径
            audio_path: 输入音频路径
            output_path: 输出视频路径
            audio_start: 音频开始时间(秒)
            video_start: 视频开始时间(秒)
            
        Returns:
            输出视频路径
        """
        # 获取视频信息，检查是否有视频流
        video_info = self.info_extractor.get_video_info(video_path)
        
        # 构建基础命令
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path
        ]
        
        # 根据视频流情况构建映射参数
        if video_info['width'] > 0 and video_info['height'] > 0:
            # 有视频流
            cmd.extend([
                '-map', '0:v',  # 使用第一个输入的视频流
                '-map', '1:a',  # 使用第二个输入的音频流
                '-c:v', 'copy',  # 保持视频编码不变
                '-c:a', 'aac',   # 音频使用AAC编码
            ])
        else:
            # 没有视频流，创建黑屏视频
            cmd = [
                'ffmpeg',
                '-f', 'lavfi', '-i', 'color=c=black:s=1920x1080:d=5',  # 5秒黑屏
                '-i', audio_path,
                '-map', '0:v',  # 使用黑屏视频流
                '-map', '1:a',  # 使用第二个输入的音频流
                '-c:v', 'libx264',  # 黑屏视频需要编码
                '-c:a', 'aac',   # 音频使用AAC编码
                '-shortest',     # 以最短的流为准
            ]
        
        cmd.extend(['-y', output_path])
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def cut_audio(
        self,
        audio_path: str,
        output_path: str,
        start_time: float,
        end_time: float = None,
        duration: float = None
    ) -> str:
        """截取音频片段
        
        Args:
            audio_path: 输入音频路径
            output_path: 输出音频路径
            start_time: 开始时间(秒)
            end_time: 结束时间(秒)
            duration: 持续时间(秒)
            
        Returns:
            输出音频路径
        """
        cmd = ['ffmpeg', '-i', audio_path, '-ss', str(start_time)]
        
        if duration is not None:
            cmd.extend(['-t', str(duration)])
        elif end_time is not None:
            cmd.extend(['-t', str(end_time - start_time)])
        
        cmd.extend(['-c', 'copy', '-y', output_path])
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def concat_audio_files(self, audio_files: List[str], output_path: str) -> str:
        """拼接多个音频文件
        
        Args:
            audio_files: 音频文件路径列表
            output_path: 输出音频文件路径
            
        Returns:
            拼接后的音频文件路径
        """
        # 添加调试日志
        if self.logger:
            self.logger.debug(f"concat_audio_files: 开始拼接音频文件，共 {len(audio_files)} 个文件")
            self.logger.debug(f"concat_audio_files: 输出路径={output_path}")

        # 验证输入文件存在性
        for i, audio_file in enumerate(audio_files):
            if not os.path.exists(audio_file):
                if self.logger:
                    self.logger.error(f"concat_audio_files: 错误！音频文件不存在: {audio_file}")
                raise FileNotFoundError(f"音频文件不存在: {audio_file}")
            if self.logger:
                self.logger.debug(f"concat_audio_files: 音频文件 {i+1} 存在: {audio_file}")
        
        # 获取每个音频文件的时长
        total_input_duration = 0
        for i, audio_file in enumerate(audio_files):
            try:
                duration = self.info_extractor.get_duration(audio_file)
                total_input_duration += duration
                if self.logger:
                    self.logger.debug(f"concat_audio_files: 音频文件 {i+1} 时长={duration:.2f}秒")
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"concat_audio_files: 获取音频文件 {i+1} 时长失败: {str(e)}")

        if self.logger:
            self.logger.debug(f"concat_audio_files: 输入音频总时长={total_input_duration:.2f}秒")

        # 创建临时文件列表
        with self.temp_manager.create_temp_file(suffix='.txt') as list_file:
            if self.logger:
                self.logger.debug(f"concat_audio_files: 创建临时列表文件={list_file}")

            with open(list_file, 'w', encoding='utf-8') as f:
                for i, path in enumerate(audio_files):
                    # 使用绝对路径避免路径问题,并转义特殊字符
                    abs_path = os.path.abspath(path).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")
                    if self.logger:
                        self.logger.debug(f"concat_audio_files: 添加到列表文件 {i+1}: {abs_path}")
            
            # 使用concat demuxer拼接音频
            cmd = [
                'ffmpeg', '-f', 'concat',
                '-safe', '0',  # 允许不安全的文件路径
                '-i', list_file,
                '-c', 'copy',  # 使用流复制，避免重新编码
                '-y',
                output_path
            ]
            
            if self.logger:
                self.logger.debug(f"concat_audio_files: 执行FFmpeg命令: {' '.join(cmd)}")

            try:
                self.error_handler.execute_command(cmd)
                if self.logger:
                    self.logger.debug(f"concat_audio_files: FFmpeg命令执行成功")
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"concat_audio_files: FFmpeg命令执行失败: {str(e)}")
                raise

        # 验证输出文件
        if os.path.exists(output_path):
            try:
                output_duration = self.info_extractor.get_duration(output_path)
                if self.logger:
                    self.logger.debug(f"concat_audio_files: 输出音频文件存在，时长={output_duration:.2f}秒")

                # 检查时长是否匹配
                if abs(output_duration - total_input_duration) > 0.5:
                    if self.logger:
                        self.logger.warning(f"concat_audio_files: 警告！输出时长({output_duration:.2f})与输入总时长({total_input_duration:.2f})不匹配")
                else:
                    if self.logger:
                        self.logger.debug(f"concat_audio_files: 时长匹配，拼接成功")
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"concat_audio_files: 获取输出音频时长失败: {str(e)}")
        else:
            if self.logger:
                self.logger.error(f"concat_audio_files: 错误！输出音频文件不存在: {output_path}")
        
        return output_path


class SubtitleRenderer:
    """字幕渲染器"""
    
    def __init__(self, error_handler: FFmpegErrorHandler, temp_manager: TempFileManager):
        """初始化字幕渲染器
        
        Args:
            error_handler: 错误处理器
            temp_manager: 临时文件管理器
        """
        self.error_handler = error_handler
        self.temp_manager = temp_manager
    
    def add_text_subtitle(
        self,
        video_path: str,
        output_path: str,
        text: str,
        start_time: float,
        end_time: float,
        fontfile: str = None,
        fontsize: int = 24,
        fontcolor: str = 'white',
        x: str = '(w-text_w)/2',
        y: str = 'h-th-50',
        box: bool = True,
        boxcolor: str = 'black@0.5'
    ) -> str:
        """添加文本字幕
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            text: 字幕文本
            start_time: 开始时间(秒)
            end_time: 结束时间(秒)
            fontfile: 字体文件路径
            fontsize: 字体大小
            fontcolor: 字体颜色
            x: x 坐标表达式
            y: y 坐标表达式
            box: 是否显示背景框
            boxcolor: 背景框颜色
            
        Returns:
            输出视频路径
        """
        # 转义文本中的特殊字符
        text = text.replace("'", r"'\''").replace(":", r"\:")
        
        # 构建 drawtext 滤镜
        drawtext_parts = [
            f"text='{text}'",
            f"fontsize={fontsize}",
            f"fontcolor={fontcolor}",
            f"x={x}",
            f"y={y}",
            f"enable='between(t,{start_time},{end_time})'"
        ]
        
        if fontfile:
            drawtext_parts.insert(1, f"fontfile='{fontfile}'")
        
        if box:
            drawtext_parts.extend([
                f"box=1",
                f"boxcolor={boxcolor}",
                f"boxborderw=5"
            ])
        
        drawtext_filter = "drawtext=" + ":".join(drawtext_parts)
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', drawtext_filter,
            '-c:a', 'copy',
            '-y',
            output_path
        ]
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def add_srt_subtitle(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        fontfile: str = None,
        fontsize: int = 24,
        fontcolor: str = 'white',
        subtitle_type: str = 'hard'
    ) -> str:
        """添加 SRT 字幕文件
        
        Args:
            video_path: 输入视频路径
            srt_path: SRT 字幕文件路径
            output_path: 输出视频路径
            fontfile: 字体文件路径
            fontsize: 字体大小
            fontcolor: 字体颜色
            subtitle_type: 字幕类型,'hard'(硬字幕)或'soft'(软字幕)
            
        Returns:
            输出视频路径
        """
        if subtitle_type == 'soft':
            # 软字幕:保留字幕流,不烧录到视频
            cmd = [
                'ffmpeg', '-i', video_path, '-i', srt_path,
                '-c:v', 'copy', '-c:a', 'copy',
                '-c:s', 'mov_text',  # 使用mov_text编码器
                '-metadata:s:s:0', 'language=chi',  # 设置字幕语言
                '-map', '0', '-map', '1',
                '-y', output_path
            ]
        else:
            # 硬字幕:烧录字幕到视频
            # 转义字幕路径
            srt_path_escaped = srt_path.replace('\\', '/').replace(':', r'\:')
            
            # 构建字幕滤镜
            subtitle_parts = [f"subtitles='{srt_path_escaped}'"]
            
            if fontfile or fontsize or fontcolor:
                style_parts = []
                if fontfile:
                    style_parts.append(f"FontName={Path(fontfile).stem}")
                if fontsize:
                    style_parts.append(f"FontSize={fontsize}")
                if fontcolor:
                    hex_color = self._color_to_ass_hex(fontcolor)
                    style_parts.append(f"PrimaryColour={hex_color}")
                
                if style_parts:
                    subtitle_parts.append(f"force_style='{','.join(style_parts)}'")
            
            subtitle_filter = ":".join(subtitle_parts)
            
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', subtitle_filter,
                '-c:a', 'copy',
                '-y', output_path
            ]
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def _color_to_ass_hex(self, color: str) -> str:
        """将颜色转换为 ASS 字幕格式的十六进制
        
        Args:
            color: 颜色名称或十六进制值
            
        Returns:
            ASS 格式的颜色值
        """
        # 简单的颜色映射
        color_map = {
            'white': '&H00FFFFFF',
            'black': '&H00000000',
            'red': '&H000000FF',
            'green': '&H0000FF00',
            'blue': '&H00FF0000',
            'yellow': '&H0000FFFF'
        }
        
        if color.lower() in color_map:
            return color_map[color.lower()]
        
        # 处理 #RRGGBB 格式
        if color.startswith('#') and len(color) == 7:
            r, g, b = color[1:3], color[3:5], color[5:7]
            return f"&H00{b}{g}{r}".upper()
        
        return '&H00FFFFFF'  # 默认白色


class EffectProcessor:
    """特效处理器"""
    
    def __init__(self, error_handler: FFmpegErrorHandler, temp_manager: TempFileManager):
        """初始化特效处理器
        
        Args:
            error_handler: 错误处理器
            temp_manager: 临时文件管理器
        """
        self.error_handler = error_handler
        self.temp_manager = temp_manager
        self.info_extractor = VideoInfoExtractor(error_handler)
    
    def add_fade_in(
        self,
        video_path: str,
        output_path: str,
        duration: float = 1.0
    ) -> str:
        """添加淡入效果
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            duration: 淡入时长(秒)
            
        Returns:
            输出视频路径
        """
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"fade=in:st=0:d={duration}",
            '-af', f"afade=in:st=0:d={duration}",
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-y',
            output_path
        ]
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def add_fade_out(
        self,
        video_path: str,
        output_path: str,
        duration: float = 1.0
    ) -> str:
        """添加淡出效果
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            duration: 淡出时长(秒)
            
        Returns:
            输出视频路径
        """
        # 获取视频时长
        video_duration = self.info_extractor.get_duration(video_path)
        fade_start = video_duration - duration
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"fade=out:st={fade_start}:d={duration}",
            '-af', f"afade=out:st={fade_start}:d={duration}",
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-y',
            output_path
        ]
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def add_transition(
        self,
        video1_path: str,
        video2_path: str,
        output_path: str,
        transition_type: str = "fade",
        duration: float = 1.0
    ) -> str:
        """添加转场效果
        
        Args:
            video1_path: 第一个视频路径
            video2_path: 第二个视频路径
            output_path: 输出视频路径
            transition_type: 转场类型(fade, wipeleft, wiperight, etc.)
            duration: 转场时长(秒)
            
        Returns:
            输出视频路径
        """
        # 获取第一个视频的时长
        video1_duration = self.info_extractor.get_duration(video1_path)
        
        # 转场开始时间
        transition_offset = video1_duration - duration
        
        # 构建转场滤镜
        filter_complex = (
            f"[0:v][1:v]xfade=transition={transition_type}:"
            f"duration={duration}:offset={transition_offset}[vout];"
            f"[0:a][1:a]acrossfade=d={duration}[aout]"
        )
        
        cmd = [
            'ffmpeg', '-i', video1_path, '-i', video2_path,
            '-filter_complex', filter_complex,
            '-map', '[vout]', '-map', '[aout]',
            '-y', output_path
        ]
        
        self.error_handler.execute_command(cmd)
        return output_path


class FFmpegWrapper:
    """FFmpeg 包装器主类"""
    
    def __init__(
        self,
        logger: Logger = None,
        temp_dir: str = None,
        ffmpeg_path: str = 'ffmpeg',
        ffprobe_path: str = 'ffprobe'
    ):
        """初始化 FFmpeg 包装器
        
        Args:
            logger: 日志记录器
            temp_dir: 临时文件目录
            ffmpeg_path: ffmpeg 可执行文件路径
            ffprobe_path: ffprobe 可执行文件路径
        """
        self.logger = logger
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        
        # 初始化各功能模块
        self.error_handler = FFmpegErrorHandler(logger)
        self.temp_manager = TempFileManager(temp_dir)
        self.info_extractor = VideoInfoExtractor(self.error_handler)
        self.video_processor = VideoProcessor(self.error_handler, self.temp_manager, self.logger)
        self.audio_processor = AudioProcessor(self.error_handler, self.temp_manager)
        self.subtitle_renderer = SubtitleRenderer(self.error_handler, self.temp_manager)
        self.effect_processor = EffectProcessor(self.error_handler, self.temp_manager)
        
        # 检测 FFmpeg 是否可用
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """检测 FFmpeg 是否安装"""
        try:
            subprocess.run(
                [self.ffmpeg_path, '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            subprocess.run(
                [self.ffprobe_path, '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            if self.logger:
                self.logger.info("FFmpeg 检测成功")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise FFmpegError(
                f"FFmpeg 未安装或不在 PATH 中。请安装 FFmpeg: {str(e)}"
            )
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息(快捷方法)"""
        return self.info_extractor.get_video_info(video_path)
    
    def normalize_video_format(
        self,
        input_path: str,
        output_path: str,
        video_codec: str = 'libx264',
        audio_codec: str = 'aac',
        pixel_format: str = 'yuv420p',
        fps: int = 30,
        width: int = None,
        height: int = None
    ) -> str:
        """标准化视频格式，确保所有视频使用相同的编码参数
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            video_codec: 视频编码器
            audio_codec: 音频编码器
            pixel_format: 像素格式
            fps: 帧率
            width: 目标宽度（可选）
            height: 目标高度（可选）
            
        Returns:
            输出视频路径
        """
        # 构建滤镜链
        filters = []
        
        # 如果需要调整尺寸
        if width and height:
            filters.append(f"scale={width}:{height}")
        elif width:
            filters.append(f"scale={width}:-2")
        elif height:
            filters.append(f"scale=-2:{height}")
        
        # 如果需要调整帧率
        video_info = self.get_video_info(input_path)
        if abs(video_info.get('fps', 0) - fps) > 0.1:
            filters.append(f"fps={fps}")
        
        # 构建滤镜字符串
        filter_string = ','.join(filters) if filters else None
        
        cmd = ['ffmpeg', '-i', input_path]
        
        # 添加滤镜
        if filter_string:
            cmd.extend(['-vf', filter_string])
        
        # 添加编码参数
        cmd.extend([
            '-c:v', video_codec,
            '-c:a', audio_codec,
            '-pix_fmt', pixel_format,
            '-movflags', '+faststart',  # 优化网络播放
            '-y',
            output_path
        ])
        
        self.error_handler.execute_command(cmd)
        return output_path
    
    def get_supported_video_formats(self) -> List[str]:
        """获取支持的视频格式列表
        
        Returns:
            支持的视频扩展名列表
        """
        return [
            '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm',
            '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'
        ]
    
    def get_supported_image_formats(self) -> List[str]:
        """获取支持的图片格式列表
        
        Returns:
            支持的图片扩展名列表
        """
        return [
            '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'
        ]
    
    def is_video_file(self, file_path: str) -> bool:
        """检查文件是否为支持的视频格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为视频文件
        """
        return Path(file_path).suffix.lower() in self.get_supported_video_formats()
    
    def is_image_file(self, file_path: str) -> bool:
        """检查文件是否为支持的图片格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为图片文件
        """
        return Path(file_path).suffix.lower() in self.get_supported_image_formats()
    
    def cleanup(self):
        """清理临时文件"""
        self.temp_manager.cleanup()