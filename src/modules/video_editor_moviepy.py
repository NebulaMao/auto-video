"""
MoviePy视频编辑器模块

使用MoviePy作为视频处理后端的替代实现
"""

import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

from ..core.logger import Logger
from ..core.exceptions import VideoProcessingError
from ..utils.moviepy_video_concat import MoviePyVideoConcatenator


class MoviePyVideoEditor:
    """MoviePy视频编辑器"""

    def __init__(self, config: Dict[str, Any], logger: Logger = None):
        """初始化MoviePy视频编辑器

        Args:
            config: 配置字典
            logger: 日志记录器
        """
        self.logger = logger
        self.config = config

        # 修复：支持两种配置结构 - 直接传递或video段下
        if 'video' in config:
            video_config = config['video']
        else:
            video_config = config  # 兼容直接传递视频配置

        self.resolution = tuple(video_config.get('resolution', [1920, 1080]))
        self.fps = video_config.get('fps', 30)
        self.codec = video_config.get('codec', 'libx264')
        self.bitrate = video_config.get('bitrate', '2000k')
        self.audio_codec = video_config.get('audio_codec', 'aac')
        self.audio_bitrate = video_config.get('audio_bitrate', '128k')

        # 修复：添加配置验证日志
        if self.logger:
            self.logger.info(f"MoviePy后端初始化完成")
            self.logger.info(f"  接收到的配置结构: {list(config.keys())}")
            self.logger.info(f"  解析出的video_config: {video_config}")
            self.logger.info(f"  最终分辨率设置: {self.resolution}")
            self.logger.info(f"  FPS: {self.fps}, 编码器: {self.codec}")

        # 初始化MoviePy视频拼接器
        self.moviepy_concat = MoviePyVideoConcatenator(logger)

    def create_video(
        self,
        script: List[Dict],
        materials: List[str],
        output_path: str,
        target_total_duration: Optional[float] = None
    ) -> str:
        """创建视频（使用MoviePy实现）

        Args:
            script: 脚本段落列表
            materials: 素材文件路径列表
            output_path: 输出视频路径
            target_total_duration: 目标总时长（用于按实际音频时长缩放场景时长）

        Returns:
            输出视频路径

        Raises:
            VideoProcessingError: 视频处理失败
        """
        if self.logger:
            self.logger.info(f"开始使用MoviePy创建视频: {len(materials)}个素材 -> {output_path}")

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 计算场景时长，必要时按目标总时长缩放
            scene_durations = [float(scene.get('duration', 5)) for scene in script] if script else []
            total_scene_duration = sum(scene_durations)
            if target_total_duration and total_scene_duration > 0:
                scale = target_total_duration / total_scene_duration
                scene_durations = [max(1.0, duration * scale) for duration in scene_durations]
                if self.logger:
                    self.logger.info(
                        f"按目标总时长 {target_total_duration:.2f}s 缩放场景时长, 比例 {scale:.3f}"
                    )
            elif not scene_durations:
                # 没有场景信息时，均分目标时长或使用默认值
                default_duration = (
                    float(target_total_duration) / max(len(materials), 1)
                    if target_total_duration else 5.0
                )
                default_duration = max(1.0, default_duration)
                scene_durations = [default_duration] * max(len(materials), 1)

            material_segments = []
            for material_path in materials:
                if not material_path or not Path(material_path).exists():
                    if self.logger:
                        self.logger.warning(f"素材文件不存在，跳过: {material_path}")
                    continue

                try:
                    with VideoFileClip(material_path) as probe_clip:
                        source_duration = float(probe_clip.duration or 0)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"读取素材时长失败，跳过 {material_path}: {e}")
                    continue

                if source_duration <= 0.1:
                    if self.logger:
                        self.logger.warning(f"素材时长异常（<=0.1s），跳过: {material_path}")
                    continue

                material_segments.append({
                    "path": material_path,
                    "start": 0.0,
                    "remaining": source_duration
                })

            if not material_segments:
                raise VideoProcessingError("没有可用的素材片段")

            total_target_duration = sum(scene_durations)
            total_material_duration = sum(seg["remaining"] for seg in material_segments)
            if total_material_duration + 0.1 < total_target_duration and self.logger:
                self.logger.warning(
                    f"素材总时长({total_material_duration:.2f}s)短于目标时长({total_target_duration:.2f}s)，"
                    "可能需要重复使用素材"
                )

            processed_clips: List[str] = []
            segment_index = 0
            last_material_path: Optional[str] = None
            for scene_idx, target_duration in enumerate(scene_durations):
                remaining = max(target_duration, 0.0)

                while remaining > 0.1 and segment_index < len(material_segments):
                    segment = material_segments[segment_index]
                    use_duration = min(remaining, segment["remaining"])
                    temp_output = str(output_file.parent / f"temp_clip_{len(processed_clips)}.mp4")

                    self.process_video_clip(
                        segment["path"],
                        use_duration,
                        temp_output,
                        start_time=segment["start"]
                    )

                    if not Path(temp_output).exists():
                        raise VideoProcessingError(f"临时文件未生成: {temp_output}")

                    temp_file_size = Path(temp_output).stat().st_size
                    if temp_file_size < 1000:
                        raise VideoProcessingError(f"临时文件大小异常: {temp_file_size} bytes")

                    processed_clips.append(temp_output)
                    last_material_path = segment["path"]

                    segment["start"] += use_duration
                    segment["remaining"] -= use_duration
                    remaining -= use_duration

                    if segment["remaining"] <= 0.1:
                        segment_index += 1

                if remaining > 0.1 and last_material_path:
                    # 素材不足时的兜底：重复最后一个素材补足剩余时长
                    if self.logger:
                        self.logger.warning(
                            f"场景 {scene_idx + 1} 仍有 {remaining:.2f}s 未覆盖，重复最后一个素材补足"
                        )
                    temp_output = str(output_file.parent / f"temp_clip_{len(processed_clips)}.mp4")
                    self.process_video_clip(last_material_path, remaining, temp_output)
                    processed_clips.append(temp_output)

            if not processed_clips:
                raise VideoProcessingError("没有有效的素材可以使用")

            if self.logger:
                self.logger.info(
                    f"素材分配完成: {len(processed_clips)} 个片段覆盖 {len(scene_durations)} 个场景"
                )

            # 拼接视频片段
            if len(processed_clips) == 1:
                shutil.copy2(processed_clips[0], str(output_file))
            else:
                if self.logger:
                    self.logger.info(f"使用MoviePy拼接 {len(processed_clips)} 个视频片段")

                self.moviepy_concat.concat_videos(
                    processed_clips,
                    str(output_file),
                    method="compose"  # 自动处理不同尺寸
                )

            # 清理临时文件
            for clip_path in processed_clips:
                if Path(clip_path).exists():
                    Path(clip_path).unlink()

            if self.logger:
                self.logger.info(f"视频创建完成: {output_path}")

            return str(output_file)

        except Exception as e:
            error_msg = f"视频创建失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise VideoProcessingError(error_msg)

    def process_video_clip(
        self,
        material_path: str,
        duration: float,
        output_path: str,
        start_time: float = 0.0
    ) -> str:
        """处理单个视频片段（使用MoviePy实现）

        Args:
            material_path: 输入素材路径
            duration: 目标时长(秒)
            output_path: 输出路径
            start_time: 起始截取时间(秒)

        Returns:
            输出视频路径
        """
        if self.logger:
            self.logger.info(
                f"使用MoviePy处理视频片段: {material_path} -> {output_path}, "
                f"起始: {start_time}s, 目标时长: {duration}s"
            )

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 加载视频
            clip = VideoFileClip(material_path)
            if self.logger:
                self.logger.info(f"原视频时长: {clip.duration:.2f}s, 分辨率: {clip.size}, FPS: {clip.fps}")

            available_duration = max(clip.duration - start_time, 0)
            if available_duration <= 0:
                raise VideoProcessingError(f"素材可用时长不足: {material_path}")

            target_duration = duration
            if duration > available_duration:
                target_duration = available_duration
                if self.logger:
                    self.logger.warning(
                        f"请求时长({duration:.2f}s)超过可用片段({available_duration:.2f}s)，截取剩余部分"
                    )

            # 截取所需片段，优先避免循环重复
            if start_time > 0 or target_duration < clip.duration:
                end_time = min(start_time + target_duration, clip.duration)
                processed_clip = clip.subclipped(start_time, end_time)
            elif clip.duration < target_duration:
                # 兜底：在需要时才循环补足，避免频繁重复
                loops_needed = int(target_duration // clip.duration) + 1
                clips_to_concat = [clip] * loops_needed
                concatenated = concatenate_videoclips(clips_to_concat)
                processed_clip = concatenated.subclipped(0, target_duration)
                concatenated.close()
            else:
                processed_clip = clip

            # 调整分辨率 - 修复：增强日志追踪
            original_size = processed_clip.size
            if processed_clip.size != self.resolution:
                if self.logger:
                    self.logger.info(f"调整分辨率: {original_size} -> {self.resolution}")
                processed_clip = processed_clip.resized(self.resolution)
                if self.logger:
                    self.logger.info(f"分辨率调整完成: {processed_clip.size}")
            else:
                if self.logger:
                    self.logger.info(f"分辨率无需调整: {processed_clip.size} == {self.resolution}")

            #[debug] 输出处理后视频信息
            if self.logger:
                self.logger.info(f"处理后视频时长: {processed_clip.duration:.2f}s, 最终分辨率: {processed_clip.size}, FPS: {processed_clip.fps}")
            # Logger.info("000000000000000000000000000000000")  # 修复：注释掉错误的调试代码
            # 导出视频 - 修复参数冲突
            # 检查原视频是否有音频轨道
            original_clip = VideoFileClip(material_path)
            has_audio = original_clip.audio is not None
            original_clip.close()

            if self.logger:
                self.logger.info(f"原视频音频状态: {'有音频' if has_audio else '无音频'}")

            # 根据是否有音频决定参数
            try:
                if has_audio:
                    if self.logger:
                        self.logger.info("使用带音频参数导出视频")
                    processed_clip.write_videofile(
                        str(output_file),
                        codec=self.codec,
                        audio_codec=self.audio_codec,
                        fps=self.fps,
                        bitrate=self.bitrate,
                        logger=None if self.logger else None  # 避免日志冲突
                    )
                else:
                    if self.logger:
                        self.logger.info("使用无音频参数导出视频")
                    processed_clip.write_videofile(
                        str(output_file),
                        codec=self.codec,
                        fps=self.fps,
                        bitrate=self.bitrate,
                        audio=False,  # 只有在没有音频时才禁用
                        logger=None if self.logger else None  # 避免日志冲突
                    )
            except Exception as export_error:
                if self.logger:
                    self.logger.error(f"MoviePy导出失败: {str(export_error)}")
                raise VideoProcessingError(f"视频导出失败: {str(export_error)}")

            # 验证输出文件
            if not output_file.exists():
                raise VideoProcessingError(f"视频文件未生成: {output_file}")

            file_size = output_file.stat().st_size
            if self.logger:
                self.logger.info(f"生成的视频文件大小: {file_size} bytes")

            if file_size < 1000:  # 小于1KB认为无效
                # 添加更多调试信息
                if self.logger:
                    self.logger.error(f"文件大小异常，详细信息:")
                    self.logger.error(f"  - 输出路径: {output_file}")
                    self.logger.error(f"  - 文件是否存在: {output_file.exists()}")
                    if output_file.exists():
                        self.logger.error(f"  - 文件统计信息: {output_file.stat()}")
                raise VideoProcessingError(f"生成的视频文件大小异常: {file_size} bytes")

            # 清理资源
            processed_clip.close()
            clip.close()

            if self.logger:
                self.logger.info(f"视频片段处理完成: {output_path} ({file_size} bytes)")

            return str(output_file)

        except Exception as e:
            error_msg = f"视频片段处理失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            # 确保清理资源
            try:
                if 'clip' in locals():
                    clip.close()
                if 'processed_clip' in locals():
                    processed_clip.close()
                if 'concatenated' in locals():
                    concatenated.close()
            except:
                pass
            raise VideoProcessingError(error_msg)

    def merge_audio_video(self, video_path: str, audio_path: str, output_path: str,
                         target_duration: float = None) -> str:
        """合并音视频（使用MoviePy实现）

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            target_duration: 目标时长(秒)，如果指定则会调整视频长度

        Returns:
            输出文件路径
        """
        if self.logger:
            self.logger.info(f"使用MoviePy合并音视频: {video_path} + {audio_path} -> {output_path}")

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 加载视频和音频
            with VideoFileClip(video_path) as video_clip, AudioFileClip(audio_path) as audio_clip:
                # 如果指定了目标时长，调整视频长度
                if target_duration:
                    if video_clip.duration > target_duration:
                        video_clip = video_clip.subclipped(0, target_duration)
                    elif video_clip.duration < target_duration:
                        # 循环视频直到达到目标时长
                        loops_needed = int(target_duration // video_clip.duration) + 1
                        clips_to_concat = [video_clip] * loops_needed
                        temp_clip = concatenate_videoclips(clips_to_concat)
                        video_clip = temp_clip.subclipped(0, target_duration)

                # 设置音频
                final_clip = video_clip.with_audio(audio_clip)

                # 导出最终视频
                final_clip.write_videofile(
                    str(output_file),
                    codec=self.codec,
                    audio_codec=self.audio_codec,
                    fps=self.fps,
                    bitrate=self.bitrate,
                    temp_audiofile=str(output_file) + "_temp_audio.m4a",
                    remove_temp=True
                )

            if self.logger:
                self.logger.info(f"音视频合并完成: {output_path}")

            return str(output_file)

        except Exception as e:
            error_msg = f"音视频合并失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise VideoProcessingError(error_msg)

    def concat_videos(self, video_paths: List[str], output_path: str, **kwargs) -> str:
        """拼接视频片段（使用MoviePy实现）

        Args:
            video_paths: 视频文件路径列表
            output_path: 输出视频路径
            **kwargs: 额外参数

        Returns:
            输出视频路径
        """
        if self.logger:
            self.logger.info(f"使用MoviePy拼接视频: {len(video_paths)}个片段 -> {output_path}")

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 加载所有视频片段（使用更健壮的方法）
            clips = []
            valid_video_paths = []
            for video_path in video_paths:
                if not Path(video_path).exists():
                    if self.logger:
                        self.logger.warning(f"视频文件不存在，跳过: {video_path}")
                    continue

                try:
                    # 尝试加载视频
                    clip = VideoFileClip(video_path)
                    if clip.duration > 0:  # 确保视频有有效时长
                        clips.append(clip)
                        valid_video_paths.append(video_path)
                    else:
                        if self.logger:
                            self.logger.warning(f"视频时长为0，跳过: {video_path}")
                        clip.close()
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"无法加载视频文件，跳过: {video_path}, 错误: {e}")
                    # 继续处理其他视频

            if not clips:
                # 如果没有有效的视频片段，尝试复制第一个有效的视频文件（如果有）
                for video_path in video_paths:
                    if Path(video_path).exists():
                        shutil.copy2(video_path, output_path)
                        if self.logger:
                            self.logger.info(f"没有有效的视频片段，复制第一个文件: {video_path} -> {output_path}")
                        return str(output_path)

                raise VideoProcessingError("没有有效的视频片段可以拼接")

            # 拼接视频
            if len(clips) == 1:
                # 只有一个片段，直接复制
                clips[0].close()
                shutil.copy2(valid_video_paths[0], output_path)
            else:
                # 多个片段，使用MoviePy拼接
                try:
                    final_clip = concatenate_videoclips(clips, method="compose")

                    # 导出视频
                    final_clip.write_videofile(
                        str(output_file),
                        codec=self.codec,
                        audio_codec=self.audio_codec,
                        fps=self.fps,
                        bitrate=self.bitrate
                    )

                    # 清理内存
                    final_clip.close()
                except Exception as e:
                    # 清理已加载的clips
                    for clip in clips:
                        try:
                            clip.close()
                        except:
                            pass
                    raise e

                # 清理所有clips
                for clip in clips:
                    try:
                        clip.close()
                    except:
                        pass

            if self.logger:
                self.logger.info(f"视频拼接完成: {output_path}")

            return str(output_path)

        except Exception as e:
            error_msg = f"视频拼接失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise VideoProcessingError(error_msg)

    def cut_video(self, input_path: str, output_path: str, start_time: float, duration: float, **kwargs) -> str:
        """截取视频片段（使用MoviePy实现）

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            start_time: 开始时间（秒）
            duration: 持续时间（秒）
            **kwargs: 额外参数

        Returns:
            输出视频路径
        """
        if self.logger:
            self.logger.info(f"使用MoviePy截取视频: {input_path} -> {output_path}, 开始: {start_time}s, 时长: {duration}s")

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 加载视频并截取
            with VideoFileClip(input_path) as clip:
                end_time = start_time + duration
                if end_time > clip.duration:
                    end_time = clip.duration

                cut_clip = clip.subclipped(start_time, end_time)

                # 导出视频
                cut_clip.write_videofile(
                    str(output_file),
                    codec=self.codec,
                    audio_codec=self.audio_codec,
                    fps=self.fps,
                    bitrate=self.bitrate
                )

            if self.logger:
                self.logger.info(f"视频截取完成: {output_path}")

            return str(output_path)

        except Exception as e:
            error_msg = f"视频截取失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise VideoProcessingError(error_msg)
