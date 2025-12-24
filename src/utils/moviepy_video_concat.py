"""
MoviePy视频拼接工具模块

提供使用MoviePy进行视频拼接的功能，作为FFmpeg concat的替代方案
"""

import os
from typing import List
from moviepy import VideoFileClip, concatenate_videoclips


class MoviePyVideoConcatenator:
    """MoviePy视频拼接器"""

    def __init__(self, logger=None):
        """初始化视频拼接器

        Args:
            logger: 日志记录器
        """
        self.logger = logger

    def concat_videos(self, video_paths: List[str], output_path: str,
                     method: str = "compose") -> str:
        """使用MoviePy拼接多个视频

        Args:
            video_paths: 输入视频路径列表
            output_path: 输出视频路径
            method: 拼接方法 ("compose" 或 "chain")
                   - "compose": 自动处理不同尺寸的视频，居中显示
                   - "chain": 简单串联，要求视频尺寸相同

        Returns:
            输出视频路径

        Raises:
            Exception: 视频处理失败
        """
        if self.logger:
            self.logger.info(f"开始使用MoviePy拼接视频: {len(video_paths)}个文件 -> {output_path}")
            self.logger.debug(f"输入文件: {video_paths}")

        # 验证输入文件
        for i, path in enumerate(video_paths):
            if not os.path.exists(path):
                raise Exception(f"输入视频文件不存在: {path}")
            if not os.path.isfile(path):
                raise Exception(f"输入路径不是文件: {path}")
            if os.path.getsize(path) == 0:
                raise Exception(f"输入视频文件为空: {path}")

        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 加载视频片段
        clips = []
        try:
            for path in video_paths:
                clip = VideoFileClip(path)
                clips.append(clip)
                if self.logger:
                    self.logger.debug(f"加载视频片段: {path}, 时长: {clip.duration}s, 尺寸: {clip.size}")

            if not clips:
                raise Exception("没有有效的视频片段可以拼接")

            # 拼接视频
            if self.logger:
                self.logger.info(f"开始拼接 {len(clips)} 个视频片段")

            final_clip = concatenate_videoclips(clips, method=method)

            # 导出视频
            if self.logger:
                self.logger.info(f"导出拼接视频到: {output_path}")

            # 写入输出文件
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=output_path + "_temp_audio.m4a",
                remove_temp=True,
                fps=24,  # 可以根据需要调整
                preset="medium",  # 编码速度与压缩比的平衡
                threads=4  # 使用多线程加速编码
            )

            # 关闭所有剪辑以释放资源
            final_clip.close()
            for clip in clips:
                clip.close()

            if self.logger:
                self.logger.info(f"视频拼接完成: {output_path}")

            return output_path

        except Exception as e:
            # 确保在出错时也关闭剪辑
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            raise Exception(f"视频拼接失败: {str(e)}")

    def validate_video_file(self, video_path: str) -> bool:
        """验证视频文件是否有效

        Args:
            video_path: 视频文件路径

        Returns:
            是否为有效视频文件
        """
        try:
            if not os.path.exists(video_path):
                return False

            if not os.path.isfile(video_path):
                return False

            if os.path.getsize(video_path) == 0:
                return False

            # 尝试加载视频以验证其有效性
            with VideoFileClip(video_path) as clip:
                duration = clip.duration
                # 检查是否有有效的帧
                if hasattr(clip, 'fps') and clip.fps and duration > 0:
                    return True
                return duration > 0
        except Exception as e:
            if self.logger:
                self.logger.warning(f"视频文件验证失败 {video_path}: {str(e)}")
            return False