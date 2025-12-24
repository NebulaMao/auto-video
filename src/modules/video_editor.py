"""
视频编辑组装模块

负责视频片段的剪辑、拼接和音视频合成。
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from ..core.exceptions import VideoProcessingError
from ..core.logger import Logger
from ..core.video_backend_config import VideoBackendFactory, VideoBackendConfig, create_video_backend
from ..utils.ffmpeg_wrapper import FFmpegWrapper


class VideoEditor:
    """视频编辑器类
    
    提供视频剪辑、拼接、音频合成等功能。
    """
    
    def __init__(self, config: Dict[str, Any], logger: Logger = None):
        """初始化视频编辑器

        Args:
            config: 视频处理配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger

        # 修复：支持两种配置结构 - 顶级字段或video段下
        video_config = config.get('video', config)
        self.resolution = video_config.get('resolution', [1920, 1080])
        self.fps = video_config.get('fps', 30)
        self.codec = video_config.get('codec', 'libx264')
        self.bitrate = video_config.get('bitrate', '2000k')
        self.audio_codec = video_config.get('audio_codec', 'aac')
        self.audio_bitrate = video_config.get('audio_bitrate', '128k')
        self.output_format = video_config.get('format', 'mp4')

        # 使用工厂模式创建后端 - 修复：传递完整的配置结构
        # 确保后端能正确获取video段下的配置
        backend_config = {
            'backend': config.get('backend', 'ffmpeg'),
            **video_config  # 展开video配置，确保分辨率等参数正确传递
        }
        self.backend = create_video_backend(backend_config, logger)

        # 保留FFmpeg实例作为备用（用于向后兼容）
        if config.get('backend', 'ffmpeg') == 'ffmpeg':
            self.ffmpeg = self.backend
        else:
            self.ffmpeg = FFmpegWrapper(logger=logger)

        if self.logger:
            self.logger.info(f"视频编辑器初始化完成,后端: {config.get('backend', 'ffmpeg')}, 分辨率: {self.resolution}, FPS: {self.fps}")
    
    def create_video(
        self,
        script: List[Dict[str, Any]],
        materials: List[str],
        output_path: str,
        cleanup_temp: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """创建视频

        Args:
            script: 脚本片段列表,每个片段包含时长等信息
            materials: 素材文件路径列表
            output_path: 输出视频文件路径
            cleanup_temp: 是否清理临时文件
            **kwargs: 额外的处理参数

        Returns:
            Dict包含:
            - output_path: 输出视频路径
            - temp_files: 处理过程中生成的临时文件列表

        Raises:
            VideoProcessingError: 视频创建失败时抛出
        """
        # 根据后端类型选择处理方式
        backend_type = self.config.get('backend', 'ffmpeg')

        if self.logger:
            self.logger.info(f"开始创建视频,素材数量: {len(materials)}, 使用后端: {backend_type}")

        if backend_type == 'moviepy':
            return self._create_video_moviepy(script, materials, output_path, cleanup_temp, **kwargs)

        # FFmpeg后端处理逻辑（保持原有代码）
        try:
            processed_clips = []
            
            # 确保输出目录存在
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 处理每个素材
            for i, material_path in enumerate(materials):
                if not Path(material_path).exists():
                    if self.logger:
                        self.logger.warning(f"素材文件不存在: {material_path}")
                    continue
                
                # 获取对应的脚本信息
                duration = script[i].get('duration', 5) if i < len(script) else 5
                
                # 生成临时处理文件路径
                temp_output = str(output_file.parent / f"temp_clip_{i}.mp4")

                
                try:
                    # 根据素材类型处理
                    if self.ffmpeg.is_video_file(material_path):
                        # 视频素材:标准化格式并调整尺寸
                        # 首先获取视频信息
                        video_info = self.ffmpeg.get_video_info(material_path)
                        video_duration = video_info['duration']
                        
                        # 标准化视频格式（重新编码以确保兼容性）
                        temp_normalized = str(output_file.parent / f"temp_normalized_{i}.mp4")
                        self.ffmpeg.normalize_video_format(
                            material_path,
                            temp_normalized,
                            video_codec=self.codec,
                            audio_codec=self.audio_codec,
                            fps=self.fps,
                            width=self.resolution[0],
                            height=self.resolution[1]
                        )
                        
                        # 如果标准化后的视频比需要的时长长,截取
                        normalized_info = self.ffmpeg.get_video_info(temp_normalized)
                        if normalized_info['duration'] > duration:
                            self.ffmpeg.video_processor.cut_video(
                                temp_normalized,
                                temp_output,
                                start_time=0,
                                duration=duration,
                                reencode=False  # 已经是标准格式，不需要重新编码
                            )
                            # 清理临时标准化文件
                            if Path(temp_normalized).exists():
                                Path(temp_normalized).unlink()
                        else:
                            # 直接使用标准化文件
                            import shutil
                            shutil.move(temp_normalized, temp_output)
                        
                    elif self.ffmpeg.is_image_file(material_path):
                        # 图片素材:转为视频
                        temp_video = str(output_file.parent / f"temp_image_{i}.mp4")
                        self.ffmpeg.video_processor.image_to_video(
                            material_path,
                            temp_video,
                            duration=duration,
                            fps=self.fps
                        )
                        
                        # 标准化图片生成的视频
                        self.ffmpeg.normalize_video_format(
                            temp_video,
                            temp_output,
                            video_codec=self.codec,
                            audio_codec=self.audio_codec,
                            fps=self.fps,
                            width=self.resolution[0],
                            height=self.resolution[1]
                        )
                        
                        # 清理临时图片视频文件
                        if Path(temp_video).exists():
                            Path(temp_video).unlink()
                    else:
                        if self.logger:
                            self.logger.warning(f"不支持的素材格式: {material_path}")
                        continue
                    
                    processed_clips.append(temp_output)
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"处理素材 {material_path} 失败: {str(e)}")
                    # 清理可能的临时文件
                    if Path(temp_output).exists():
                        Path(temp_output).unlink()
                    continue
            
            if not processed_clips:
                raise VideoProcessingError("没有有效的素材可以使用")
            
            # 拼接视频片段
            if len(processed_clips) == 1:
                # 只有一个片段,直接移动到输出路径
                import shutil
                shutil.move(processed_clips[0], str(output_file))
            else:
                
                # 多个片段,拼接（使用后端抽象）
                self.backend.concat_videos(
                    processed_clips,
                    str(output_file),
                    reencode=True,
                    video_codec=self.codec,
                    audio_codec=self.audio_codec
                )
                
                # 根据参数决定是否清理临时片段文件
                if cleanup_temp:
                    for clip_path in processed_clips:
                        if Path(clip_path).exists():
                            Path(clip_path).unlink()

            if self.logger:
                self.logger.info(f"视频创建完成: {output_path}")

            return {
                'output_path': str(output_file),
                'temp_files': processed_clips
            }
            
        except Exception as e:
            error_msg = f"视频创建失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            
            # 清理所有临时文件
            try:
                for i in range(len(materials)):
                    for temp_file in [
                        output_file.parent / f"temp_clip_{i}.mp4",
                        output_file.parent / f"temp_cut_{i}.mp4",
                        output_file.parent / f"temp_image_{i}.mp4"
                    ]:
                        if temp_file.exists():
                            temp_file.unlink()
            except Exception:
                pass
            
            raise VideoProcessingError(error_msg)
    
    def add_audio_track(self, video_path: str, audio_path: str, output_path: str = None) -> str:
        """为视频添加音频轨道
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径(可选,默认覆盖原文件)
            
        Returns:
            输出视频文件路径
            
        Raises:
            VideoProcessingError: 音频添加失败时抛出
        """
        if self.logger:
            self.logger.info(f"为视频添加音频: {video_path} + {audio_path}")
        
        try:
            # 获取视频和音频信息
            video_info = self.ffmpeg.get_video_info(video_path)
            audio_info = self.ffmpeg.get_video_info(audio_path)
            
            video_duration = video_info['duration']
            audio_duration = audio_info['duration']
            
            # 添加调试日志
            if self.logger:
                self.logger.info(f"[DEBUG] 视频时长: {video_duration:.2f}秒")
                self.logger.info(f"[DEBUG] 音频时长: {audio_duration:.2f}秒")
                self.logger.info(f"[DEBUG] 时长差: {abs(audio_duration - video_duration):.2f}秒")
            
            # 确定输出路径
            if output_path is None:
                output_path = video_path
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果音频和视频时长不匹配,需要调整
            temp_audio = None
            audio_to_merge = audio_path
            
            if abs(audio_duration - video_duration) > 0.1:  # 时长差超过0.1秒
                if audio_duration > video_duration:
                    # 音频较长,这不应该发生，因为我们在素材选择阶段已经处理了
                    if self.logger:
                        self.logger.warning(f"[UNEXPECTED] 音频({audio_duration:.2f}s)仍然长于视频({video_duration:.2f}s),素材选择可能有问题")
                    
                    # 作为后备方案，仍然延长视频
                    temp_extended_video = str(output_file.parent / "temp_extended_video.mp4")
                    self._extend_video_to_match_audio(video_path, temp_extended_video, audio_duration)
                    video_path = temp_extended_video
                    
                    if self.logger:
                        self.logger.warning(f"[FALLBACK] 已延长视频到 {audio_duration:.2f} 秒以匹配音频长度")
                else:
                    # 音频较短,截取视频
                    if self.logger:
                        self.logger.info(f"[DEBUG] 音频({audio_duration:.2f}s)短于视频({video_duration:.2f}s),截取视频")
                    
                    temp_video = str(output_file.parent / "temp_video_cut.mp4")
                    self.backend.cut_video(
                        video_path,
                        temp_video,
                        start_time=0,
                        duration=audio_duration
                    )
                    video_path = temp_video
            else:
                if self.logger:
                    self.logger.info(f"[DEBUG] 音频和视频时长匹配,无需调整")
            
            # 合并音频和视频
            temp_output = str(output_file.parent / "temp_merged.mp4")
            self.backend.merge_audio_video(
                video_path,
                audio_to_merge,
                temp_output
            )
            
            # 移动到最终输出路径
            import shutil
            if Path(output_path).exists():
                Path(output_path).unlink()
            shutil.move(temp_output, output_path)
            
            # 清理临时文件
            if temp_audio and Path(temp_audio).exists():
                Path(temp_audio).unlink()
            if 'temp_video' in locals() and Path(temp_video).exists():
                Path(temp_video).unlink()
            if 'temp_extended_video' in locals() and Path(temp_extended_video).exists():
                Path(temp_extended_video).unlink()
            
            if self.logger:
                self.logger.info(f"音频添加完成: {output_path}")
            
            return str(output_file)
            
        except Exception as e:
            error_msg = f"音频添加失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            
            # 清理临时文件
            try:
                for temp_file in [
                    Path(output_file.parent / "temp_audio_cut.mp3"),
                    Path(output_file.parent / "temp_video_cut.mp4"),
                    Path(output_file.parent / "temp_merged.mp4")
                ]:
                    if temp_file.exists():
                        temp_file.unlink()
            except Exception:
                pass
            
            raise VideoProcessingError(error_msg)
    
    def _extend_video_to_match_audio(self, video_path: str, output_path: str, target_duration: float) -> str:
        """延长视频以匹配目标时长
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            target_duration: 目标时长（秒）
            
        Returns:
            延长后的视频路径
        """
        try:
            # 获取原视频信息
            video_info = self.ffmpeg.get_video_info(video_path)
            original_duration = video_info['duration']

            if self.logger:
                self.logger.debug(f"[EXTEND] 原视频时长: {original_duration:.2f}秒, 目标时长: {target_duration:.2f}秒")

            # 安全检查：避免除零错误
            if original_duration <= 0:
                if self.logger:
                    self.logger.warning(f"[EXTEND] 原视频时长无效，使用默认时长: {original_duration:.2f}秒")
                # 使用默认时长创建一个新视频
                from moviepy import ColorClip
                temp_clip = ColorClip(size=(self.resolution[0], self.resolution[1]), color=(255, 255, 255), duration=target_duration)
                temp_clip.write_videofile(output_path, fps=self.fps, codec=self.codec, audio=False)
                temp_clip.close()

                if self.logger:
                    self.logger.info(f"[EXTEND] 使用默认白色视频，时长: {target_duration:.2f}秒")
                return output_path

            # 计算需要循环的次数
            loop_count = int(target_duration // original_duration)
            remaining_time = target_duration - (loop_count * original_duration)
            
            if self.logger:
                self.logger.debug(f"[EXTEND] 需要循环 {loop_count} 次, 剩余时间: {remaining_time:.2f}秒")
            
            if loop_count == 0:
                # 不需要循环，只需要截取到目标长度
                self.backend.cut_video(
                    video_path,
                    output_path,
                    start_time=0,
                    duration=target_duration
                )
                return output_path
            
            # 创建临时文件列表用于拼接
            temp_files = []
            
            # 添加完整的循环视频
            for i in range(loop_count):
                temp_files.append(video_path)  # 原视频可以重复使用
            
            # 如果有剩余时间，添加截取的片段
            if remaining_time > 0.1:
                temp_remaining = str(Path(output_path).parent / f"temp_remaining_{Path(output_path).stem}.mp4")
                self.backend.cut_video(
                    video_path,
                    temp_remaining,
                    start_time=0,
                    duration=remaining_time
                )
                temp_files.append(temp_remaining)

            # 拼接所有视频片段
            self.backend.concat_videos(
                temp_files,
                output_path,
                reencode=True,
                video_codec=self.codec,
                audio_codec=self.audio_codec
            )
            
            # 清理临时文件
            if remaining_time > 0.1 and 'temp_remaining' in locals() and Path(temp_remaining).exists():
                Path(temp_remaining).unlink()
            
            # 验证输出视频时长
            output_info = self.ffmpeg.get_video_info(output_path)
            actual_duration = output_info['duration']
            
            if self.logger:
                self.logger.debug(f"[EXTEND] 延长后视频时长: {actual_duration:.2f}秒")
            
            return output_path
            
        except Exception as e:
            error_msg = f"延长视频失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise VideoProcessingError(error_msg)
    
    def add_transitions(
        self,
        video_path: str,
        transition_type: str = "fade",
        duration: float = 1.0
    ) -> str:
        """添加转场效果
        
        Args:
            video_path: 视频文件路径
            transition_type: 转场类型('fade', 'crossfade')
            duration: 转场持续时间(秒)
            
        Returns:
            处理后的视频路径
            
        Raises:
            VideoProcessingError: 转场添加失败时抛出
        """
        if self.logger:
            self.logger.info(f"添加转场效果: {transition_type}")
        
        try:
            # 创建临时输出文件
            video_file = Path(video_path)
            temp_output = str(video_file.parent / f"temp_transition_{video_file.name}")
            
            # 应用淡入淡出效果
            if transition_type == "fade":
                # 先添加淡入
                temp_fadein = str(video_file.parent / f"temp_fadein_{video_file.name}")
                self.ffmpeg.effect_processor.add_fade_in(
                    video_path,
                    temp_fadein,
                    duration=duration
                )
                
                # 再添加淡出
                self.ffmpeg.effect_processor.add_fade_out(
                    temp_fadein,
                    temp_output,
                    duration=duration
                )
                
                # 清理临时淡入文件
                if Path(temp_fadein).exists():
                    Path(temp_fadein).unlink()
            else:
                # 其他转场类型暂不支持,仅复制文件
                import shutil
                shutil.copy2(video_path, temp_output)
            
            # 替换原文件
            import shutil
            if Path(video_path).exists():
                Path(video_path).unlink()
            shutil.move(temp_output, video_path)
            
            if self.logger:
                self.logger.info("转场效果添加完成")
            
            return video_path
            
        except Exception as e:
            error_msg = f"转场效果添加失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            
            # 清理临时文件
            try:
                video_file = Path(video_path)
                for temp_file in [
                    video_file.parent / f"temp_transition_{video_file.name}",
                    video_file.parent / f"temp_fadein_{video_file.name}"
                ]:
                    if temp_file.exists():
                        temp_file.unlink()
            except Exception:
                pass
            
            raise VideoProcessingError(error_msg)
    
    def export_video(
        self,
        video_path: str,
        output_path: str,
        **kwargs
    ) -> str:
        """导出视频(格式转换或重新编码)
        
        Args:
            video_path: 源视频文件路径
            output_path: 输出视频文件路径
            **kwargs: 额外的导出参数
            
        Returns:
            导出的视频文件路径
            
        Raises:
            VideoProcessingError: 导出失败时抛出
        """
        if self.logger:
            self.logger.info(f"导出视频: {video_path} -> {output_path}")
        
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用 FFmpeg 重新编码视频
            # 构建 FFmpeg 命令
            cmd = [
                'ffmpeg', '-i', video_path,
                '-c:v', kwargs.get('codec', self.codec),
                '-b:v', kwargs.get('bitrate', self.bitrate),
                '-r', str(kwargs.get('fps', self.fps)),
                '-c:a', kwargs.get('audio_codec', self.audio_codec),
                '-b:a', kwargs.get('audio_bitrate', self.audio_bitrate),
                '-y',
                str(output_file)
            ]
            
            self.ffmpeg.error_handler.execute_command(cmd)
            
            if self.logger:
                self.logger.info(f"视频导出完成: {output_path}")
            
            return str(output_file)
            
        except Exception as e:
            error_msg = f"视频导出失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise VideoProcessingError(error_msg)

    def _create_video_moviepy(
        self,
        script: List[Dict[str, Any]],
        materials: List[str],
        output_path: str,
        cleanup_temp: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """使用MoviePy后端创建视频"""
        try:
            # 使用MoviePy后端的create_video方法
            target_total_duration = kwargs.get("target_duration")
            result_path = self.backend.create_video(
                script,
                materials,
                output_path,
                target_total_duration=target_total_duration
            )

            return {
                'output_path': result_path,
                'temp_files': []  # MoviePy后端自己管理临时文件
            }

        except Exception as e:
            error_msg = f"MoviePy视频创建失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise VideoProcessingError(error_msg)

    def __del__(self):
        """析构函数,清理资源"""
        try:
            if hasattr(self, 'ffmpeg'):
                self.ffmpeg.cleanup()
        except Exception:
            pass
