"""
视频处理工具模块

提供视频信息获取和基本处理的辅助函数。
使用 FFmpeg 实现所有视频处理功能。
"""

from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from .ffmpeg_wrapper import FFmpegWrapper, FFmpegError


def get_video_info(video_path: str) -> Dict[str, Any]:
    """获取视频信息
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        包含视频信息的字典
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    try:
        ffmpeg = FFmpegWrapper()
        info = ffmpeg.get_video_info(video_path)
        
        # 添加宽高比
        if info['height'] > 0:
            info['aspect_ratio'] = info['width'] / info['height']
        else:
            info['aspect_ratio'] = 0
        
        return info
        
    except FFmpegError as e:
        raise RuntimeError(f"获取视频信息失败: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"获取视频信息失败: {str(e)}")


def get_video_duration(video_path: str) -> float:
    """获取视频时长
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        视频时长(秒)
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    try:
        ffmpeg = FFmpegWrapper()
        return ffmpeg.info_extractor.get_duration(video_path)
    except FFmpegError as e:
        raise RuntimeError(f"获取视频时长失败: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"获取视频时长失败: {str(e)}")


def extract_audio_from_video(video_path: str, audio_path: str, audio_format: str = 'mp3') -> str:
    """从视频中提取音频
    
    Args:
        video_path: 视频文件路径
        audio_path: 输出音频文件路径
        audio_format: 音频格式
        
    Returns:
        音频文件路径
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    try:
        ffmpeg = FFmpegWrapper()
        
        # 检查视频是否包含音频轨道
        if not ffmpeg.info_extractor.has_audio(video_path):
            raise ValueError("视频不包含音频轨道")
        
        # 确保输出目录存在
        output_path = Path(audio_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 提取音频
        ffmpeg.audio_processor.extract_audio(
            video_path,
            str(output_path),
            audio_format=audio_format
        )
        
        return str(output_path)
        
    except FFmpegError as e:
        raise RuntimeError(f"提取音频失败: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"提取音频失败: {str(e)}")


def resize_video(
    video_path: str,
    output_path: str,
    width: int = None,
    height: int = None,
    keep_aspect_ratio: bool = True
) -> str:
    """调整视频尺寸
    
    Args:
        video_path: 视频文件路径
        output_path: 输出视频文件路径
        width: 目标宽度
        height: 目标高度
        keep_aspect_ratio: 是否保持宽高比
        
    Returns:
        输出视频文件路径
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    try:
        ffmpeg = FFmpegWrapper()
        
        # 确保输出目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 调整尺寸
        ffmpeg.video_processor.resize_video(
            video_path,
            str(output_file),
            width=width,
            height=height,
            keep_aspect_ratio=keep_aspect_ratio
        )
        
        return str(output_file)
        
    except FFmpegError as e:
        raise RuntimeError(f"调整视频尺寸失败: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"调整视频尺寸失败: {str(e)}")


def crop_video(
    video_path: str,
    output_path: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int
) -> str:
    """裁剪视频
    
    Args:
        video_path: 视频文件路径
        output_path: 输出视频文件路径
        x1: 左上角x坐标
        y1: 左上角y坐标
        x2: 右下角x坐标
        y2: 右下角y坐标
        
    Returns:
        输出视频文件路径
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    try:
        ffmpeg = FFmpegWrapper()
        
        # 计算裁剪区域的宽度和高度
        width = x2 - x1
        height = y2 - y1
        
        if width <= 0 or height <= 0:
            raise ValueError("裁剪区域无效")
        
        # 确保输出目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 裁剪视频
        ffmpeg.video_processor.crop_video(
            video_path,
            str(output_file),
            x=x1,
            y=y1,
            width=width,
            height=height
        )
        
        return str(output_file)
        
    except FFmpegError as e:
        raise RuntimeError(f"裁剪视频失败: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"裁剪视频失败: {str(e)}")


def trim_video(
    video_path: str,
    output_path: str,
    start_time: float,
    end_time: float = None
) -> str:
    """剪切视频片段
    
    Args:
        video_path: 视频文件路径
        output_path: 输出视频文件路径
        start_time: 开始时间(秒)
        end_time: 结束时间(秒),None表示到结尾
        
    Returns:
        输出视频文件路径
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    try:
        ffmpeg = FFmpegWrapper()
        
        # 确保输出目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 剪切视频
        ffmpeg.video_processor.cut_video(
            video_path,
            str(output_file),
            start_time=start_time,
            end_time=end_time
        )
        
        return str(output_file)
        
    except FFmpegError as e:
        raise RuntimeError(f"剪切视频失败: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"剪切视频失败: {str(e)}")


def get_frame_at_time(video_path: str, time: float, output_path: str = None) -> Any:
    """获取指定时间的视频帧
    
    Args:
        video_path: 视频文件路径
        time: 时间点(秒)
        output_path: 输出图片路径(可选)
        
    Returns:
        图像数组或输出路径
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    try:
        import subprocess
        import numpy as np
        from PIL import Image
        
        # 如果提供了输出路径,直接保存图片
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用 FFmpeg 提取帧并保存
            cmd = [
                'ffmpeg',
                '-ss', str(time),
                '-i', video_path,
                '-frames:v', '1',
                '-y',
                str(output_file)
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"提取视频帧失败: {result.stderr}")
            
            return str(output_file)
        else:
            # 提取帧到临时文件,然后读取为数组
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                cmd = [
                    'ffmpeg',
                    '-ss', str(time),
                    '-i', video_path,
                    '-frames:v', '1',
                    '-y',
                    tmp_path
                ]
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"提取视频帧失败: {result.stderr}")
                
                # 读取图片为数组
                img = Image.open(tmp_path)
                frame = np.array(img)
                
                return frame
            finally:
                # 清理临时文件
                import os
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
    except Exception as e:
        raise RuntimeError(f"获取视频帧失败: {str(e)}")


def concatenate_videos(video_paths: list, output_path: str, transition_duration: float = 0) -> str:
    """拼接多个视频
    
    Args:
        video_paths: 视频文件路径列表
        output_path: 输出视频文件路径
        transition_duration: 转场时长(秒)
        
    Returns:
        输出视频文件路径
    """
    try:
        # 检查所有视频文件是否存在
        for path in video_paths:
            if not Path(path).exists():
                raise FileNotFoundError(f"视频文件不存在: {path}")
        
        ffmpeg = FFmpegWrapper()
        
        # 确保输出目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果需要转场效果
        if transition_duration > 0:
            # 使用转场效果逐对拼接视频
            import tempfile
            import os
            
            if len(video_paths) < 2:
                # 只有一个视频,直接复制
                import shutil
                shutil.copy2(video_paths[0], str(output_file))
                return str(output_file)
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            
            try:
                # 逐对添加转场效果
                current_output = video_paths[0]
                
                for i in range(1, len(video_paths)):
                    if i == len(video_paths) - 1:
                        # 最后一对,输出到最终路径
                        next_output = str(output_file)
                    else:
                        # 中间步骤,输出到临时文件
                        next_output = os.path.join(temp_dir, f"temp_{i}.mp4")
                    
                    # 添加转场效果
                    ffmpeg.effect_processor.add_transition(
                        current_output,
                        video_paths[i],
                        next_output,
                        transition_type="fade",
                        duration=transition_duration
                    )
                    
                    current_output = next_output
            finally:
                # 清理临时目录
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            # 无转场效果,直接拼接
            ffmpeg.video_processor.concat_videos(video_paths, str(output_file))
        
        return str(output_file)
        
    except FFmpegError as e:
        raise RuntimeError(f"拼接视频失败: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"拼接视频失败: {str(e)}")