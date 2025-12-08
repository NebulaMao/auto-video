"""
工作流编排器模块

协调整个视频生成流程,管理各个模块间的数据流转。
"""

import uuid
import json
import re
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import shutil

from .config import ConfigManager
from .logger import Logger
from .exceptions import (
    AutoVideoException,
    LLMError,
    MaterialNotFoundError,
    TTSError,
    VideoProcessingError,
    SubtitleError
)
from ..modules.llm_client import LLMClient
from ..modules.material_searcher import MaterialSearcher
from ..modules.random_material_selector import RandomMaterialSelector
from ..modules.tts_engine import TTSEngine
from ..modules.video_editor import VideoEditor
from ..modules.subtitle_renderer import SubtitleRenderer
from ..utils.text_utils import split_text_by_punctuation, has_xml_color_tags, clean_text, clean_xml_tags, clean_xml_preserving_tags


class WorkflowManager:
    """工作流管理器类
    
    协调各个模块完成从用户描述到最终视频的完整流水线。
    """
    
    def __init__(self, config_manager: ConfigManager):
        """初始化工作流管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        
        # 初始化日志器
        log_config = config_manager.get_section('logging')
        self.logger = Logger('WorkflowManager', log_config)
        
        # 初始化各个模块
        self.logger.info("开始初始化工作流管理器")
        
        try:
            # LLM客户端
            llm_config = config_manager.get_section('llm')
            self.llm_client = LLMClient(llm_config, self.logger)
            
            # 素材检索器
            material_config = config_manager.get_section('material_search')
            self.material_searcher = MaterialSearcher(material_config, self.logger)

            # 随机素材选择器
            random_config = config_manager.get_section('random_material_selector')
            if not random_config:
                random_config = {}
            random_config.setdefault('materials_dir', material_config.get('materials_dir', './data/materials'))
            random_config.setdefault('supported_formats', material_config.get('supported_formats', ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts', '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']))
            self.random_material_selector = RandomMaterialSelector(random_config, self.logger)
            
            # TTS引擎
            tts_config = config_manager.get_section('tts')
            # 如果使用 SiliconFlow，合并配置
            if tts_config.get('engine') == 'siliconflow':
                siliconflow_config = config_manager.get_section('siliconflow_tts')
                tts_config.update(siliconflow_config)

            self.tts_engine = TTSEngine(tts_config, self.logger)
            
            # 视频编辑器
            video_config = config_manager.get_section('video')
            self.video_editor = VideoEditor(video_config, self.logger)
            
            # 字幕渲染器
            subtitle_config = config_manager.get_section('subtitle')
            self.subtitle_renderer = SubtitleRenderer(subtitle_config, self.logger)
            
            # 路径配置
            self.paths = config_manager.get_section('paths')
            self.temp_dir = Path(self.paths.get('temp_dir', './data/temp'))
            self.output_dir = Path(self.paths.get('output_dir', './data/output'))

            # 确保目录存在
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # 初始化临时文件列表
            self.temp_files = []

            # 构建素材索引
            self.logger.info("构建素材索引")
            # self.material_searcher.build_index()  # 暂时禁用语义搜索
            self.random_material_selector.build_index()

            self.logger.info("工作流管理器初始化完成")
            
        except Exception as e:
            self.logger.error(f"工作流管理器初始化失败: {str(e)}")
            raise
    
    def execute_video_generation_pipeline(
        self,
        description: str,
        duration_seconds: int = 60,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> str:
        """执行完整的视频生成流水线

        Args:
            description: 用户输入的视频描述
            duration_seconds: 视频时长（秒）
            progress_callback: 进度回调函数,接收(步骤描述, 进度百分比)

        Returns:
            最终视频文件路径

        Raises:
            AutoVideoException: 流水线执行失败时抛出
        """
        # 生成唯一的任务ID
        task_id = str(uuid.uuid4())[:8]
        self.logger.info(f"========== 开始执行视频生成任务 [Task ID: {task_id}] ==========")
        self.logger.info(f"用户描述: {description}")
        self.logger.info(f"目标时长: {duration_seconds} 秒")
        
        # 临时文件列表,用于最后清理
        temp_files = []
        
        try:
            # 步骤1: 生成口播文案
            self._update_progress(progress_callback, "正在生成口播文案...", 10)
            self.logger.info("步骤1: 生成口播文案")
            script = self._generate_script(description, duration_seconds)
            self.logger.info(f"口播文案生成完成,长度: {len(script)} 字符")

            # 步骤2: 解析场景列表
            self._update_progress(progress_callback, "正在解析场景列表...", 20)
            self.logger.info("步骤2: 解析场景列表")
            scenes = self._parse_scenes(script, duration_seconds)
            self.logger.info(f"场景解析完成,共 {len(scenes)} 个场景")
            
            # 步骤3: 生成TTS语音（提前生成以获取实际时长）
            self._update_progress(progress_callback, "正在生成语音...", 40)
            self.logger.info("步骤3: 生成分段TTS语音")
            tts_audio_path, segments_info = self._generate_tts_with_segments(script, task_id)
            temp_files.append(tts_audio_path)
            self.logger.info(f"分段TTS音频生成完成: {tts_audio_path}")
            
            # 计算实际音频时长
            actual_audio_duration = sum(seg['duration'] for seg in segments_info)
            self.logger.info(f"实际音频时长: {actual_audio_duration:.2f}秒")
            
            # 步骤4: 根据实际音频时长重新选择素材
            self._update_progress(progress_callback, "正在重新选择素材...", 30)
            self.logger.info("步骤4: 根据实际音频时长重新选择素材")
            materials = self._select_materials_for_duration(scenes, actual_audio_duration)
            self.logger.info(f"素材选择完成,共 {len(materials)} 个素材")
            
            # 步骤5: 组装视频
            self._update_progress(progress_callback, "正在组装视频...", 50)
            self.logger.info("步骤5: 组装视频")
            video_without_audio_path = self._assemble_video(scenes, materials, task_id)
            temp_files.append(video_without_audio_path)
            self.logger.info(f"视频组装完成: {video_without_audio_path}")
            
            # 步骤6: 添加音频轨道
            self._update_progress(progress_callback, "正在添加音频...", 60)
            self.logger.info("步骤6: 添加音频轨道")
            video_with_audio_path = self._add_audio(video_without_audio_path, tts_audio_path, task_id)
            temp_files.append(video_with_audio_path)
            self.logger.info(f"音频添加完成: {video_with_audio_path}")
            
            # 步骤7: 生成字幕
            self._update_progress(progress_callback, "正在生成字幕...", 70)
            self.logger.info("步骤7: 基于分段TTS信息生成字幕")
            subtitle_path = self._generate_subtitles_from_segments(segments_info, task_id)
            temp_files.append(subtitle_path)
            self.logger.info(f"基于分段TTS信息生成字幕完成: {subtitle_path}")
            
            # 步骤8: 渲染字幕到视频
            self._update_progress(progress_callback, "正在渲染字幕...", 85)
            self.logger.info("步骤8: 渲染字幕到视频")
            final_video_path = self._render_subtitles(video_with_audio_path, subtitle_path, task_id)
            self.logger.info(f"字幕渲染完成: {final_video_path}")
            
            # 步骤9: 清理临时文件
            self._update_progress(progress_callback, "正在清理临时文件...", 95)
            self.logger.info("步骤9: 清理临时文件")
            self._cleanup_temp_files(temp_files)
            
            # 完成
            self._update_progress(progress_callback, "视频生成完成!", 100)
            self.logger.info(f"========== 视频生成任务完成 [Task ID: {task_id}] ==========")
            self.logger.info(f"最终视频路径: {final_video_path}")
            
            return final_video_path
            
        except Exception as e:
            self.logger.error(f"视频生成流水线执行失败: {str(e)}")
            self.logger.exception("详细错误信息:")
            
            # 清理临时文件
            self.logger.info("清理临时文件")
            self._cleanup_temp_files(temp_files)
            
            # 重新抛出异常
            if isinstance(e, AutoVideoException):
                raise
            else:
                raise AutoVideoException(f"视频生成失败: {str(e)}")
    
    def _generate_script(self, description: str, duration_seconds: int = 60) -> str:
        """生成口播文案

        Args:
            description: 用户描述
            duration_seconds: 视频时长（秒）

        Returns:
            生成的口播文案文本
        """
        try:
            script = self.llm_client.generate_script(description, duration_seconds)
            return script
        except LLMError as e:
            self.logger.error(f"口播文案生成失败: {str(e)}")
            raise
    
    def _parse_scenes(self, script: str, duration_seconds: int = 60) -> List[Dict[str, Any]]:
        """解析口播文案为场景列表

        Args:
            script: 口播文案文本
            duration_seconds: 视频时长（秒）

        Returns:
            场景列表
        """
        try:
            # 使用LLM提取场景描述
            scenes = self.llm_client.generate_scene_descriptions(script, duration_seconds)

            # 如果LLM返回空列表,创建简单的场景分割
            if not scenes:
                self.logger.warning("LLM未能提取场景,使用简单分割")
                scenes = self._simple_scene_split(script, duration_seconds)

            return scenes
        except LLMError as e:
            self.logger.error(f"场景解析失败: {str(e)}")
            # 降级到简单场景分割
            self.logger.info("降级到简单场景分割")
            return self._simple_scene_split(script, duration_seconds)
    
    def _simple_scene_split(self, script: str, duration_seconds: int = 60) -> List[Dict[str, Any]]:
        """简单的场景分割(备用方案)

        Args:
            script: 口播文案文本
            duration_seconds: 视频时长（秒）

        Returns:
            场景列表
        """
        # 按段落分割
        paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]

        # 计算场景数量和每个场景的时长
        scene_count = min(len(paragraphs), max(3, duration_seconds // 15))  # 每15秒一个场景，最少3个
        scene_duration = duration_seconds / scene_count

        scenes = []
        for i, paragraph in enumerate(paragraphs[:scene_count], start=1):
            scenes.append({
                'scene_id': i,
                'visual_description': paragraph[:100],  # 取前100字符作为视觉描述
                'narration': paragraph,
                'duration': int(scene_duration)
            })

        # 如果场景数不足，用最后一个场景补充
        while len(scenes) < scene_count and scenes:
            last_scene = scenes[-1].copy()
            last_scene['scene_id'] = len(scenes) + 1
            scenes.append(last_scene)

        return scenes
    
    def _select_materials_for_duration(self, scenes: List[Dict[str, Any]], actual_audio_duration: float) -> List[str]:
        """根据实际音频时长选择素材
        
        Args:
            scenes: 场景列表
            actual_audio_duration: 实际音频时长（秒）
            
        Returns:
            素材文件路径列表
        """
        try:
            scene_count = len(scenes)
            duration_seconds = max(1, int(round(actual_audio_duration)))

            if self.logger:
                self.logger.info(
                    f"[DURATION_FIX] 根据实际音频时长 {actual_audio_duration:.2f}秒 (场景 {scene_count} 个) 重新选择素材"
                )

            materials = self.random_material_selector.select_materials(scene_count, duration_seconds)

            if not materials:
                raise MaterialNotFoundError("未找到任何可用素材")
            
            if self.logger:
                self.logger.info(f"[DURATION_FIX] 根据音频时长选择素材完成,共 {len(materials)} 个素材")
            
            return materials
            
        except Exception as e:
            self.logger.error(f"根据音频时长选择素材失败: {str(e)}")
            raise MaterialNotFoundError(f"素材选择失败: {str(e)}")

    def _retrieve_materials(self, scenes: List[Dict[str, Any]]) -> List[str]:
        """检索匹配的素材（保留用于向后兼容）

        Args:
            scenes: 场景列表

        Returns:
            素材文件路径列表
        """
        materials = []

        for scene in scenes:
            try:
                # 使用场景的视觉描述检索素材
                visual_desc = scene.get('visual_description', scene.get('narration', ''))

                # 提取关键词
                keywords = self.llm_client.extract_keywords(visual_desc)
                search_query = ' '.join(keywords)

                self.logger.info(f"场景 {scene.get('scene_id')}: 检索关键词 '{search_query}'")

                # 检索素材(优先视频,其次图片)
                results = self.material_searcher.search(search_query, material_type='video', top_k=1)

                if not results:
                    # 如果没有视频,尝试检索图片
                    results = self.material_searcher.search(search_query, material_type='image', top_k=1)

                if results:
                    materials.append(results[0]['path'])
                    self.logger.info(f"找到素材: {results[0]['filename']}")
                else:
                    self.logger.warning(f"场景 {scene.get('scene_id')} 未找到匹配素材")

            except Exception as e:
                self.logger.warning(f"场景素材检索失败: {str(e)}")

        if not materials:
            raise MaterialNotFoundError("未找到任何可用素材")

        return materials
    
    def _generate_tts(self, script: str, task_id: str) -> str:
        """生成TTS语音
        
        Args:
            script: 脚本文本
            task_id: 任务ID
            
        Returns:
            音频文件路径
        """
        try:
            audio_path = self.temp_dir / f"tts_{task_id}.mp3"
            self.tts_engine.synthesize(script, str(audio_path))
            return str(audio_path)
        except TTSError as e:
            self.logger.error(f"TTS语音生成失败: {str(e)}")
            raise
    
    def _generate_tts_with_segments(self, script: str, task_id: str) -> tuple[str, list]:
        """分段生成TTS语音并返回音频路径和段落信息
        
        Args:
            script: 脚本文本
            task_id: 任务ID
            
        Returns:
            (完整音频文件路径, 段落信息列表)
        """
        try:
            tts_config = self.config_manager.get_section('tts')
            segment_by_punctuation = tts_config.get('segment_by_punctuation', True)
            min_segment_length = tts_config.get('min_segment_length', 10)
            max_segment_length = tts_config.get('max_segment_length', 100)
            include_comma = tts_config.get('segment_include_comma', True)

            if self.logger:
                self.logger.debug(
                    "[TTS] 文本分段配置: by_punctuation=%s, include_comma=%s, min=%s, max=%s"
                    % (segment_by_punctuation, include_comma, min_segment_length, max_segment_length)
                )

            # 按标点符号分割文本
            if segment_by_punctuation:
                text_segments = split_text_by_punctuation(
                    script,
                    language='zh',
                    min_length=min_segment_length,
                    max_length=max_segment_length,
                    include_comma=include_comma
                )
            else:
                text_segments = [clean_text(script)] if script.strip() else []
            
            if not text_segments:
                # 如果分割失败，回退到原始方法
                self.logger.warning("文本分割失败，回退到原始TTS方法")
                audio_path = self._generate_tts(script, task_id)
                # 获取实际音频时长
                try:
                    actual_duration = self.tts_engine.get_audio_duration(audio_path)
                    return audio_path, [{'text': script, 'duration': actual_duration, 'start_time': 0, 'end_time': actual_duration}]
                except Exception as e:
                    self.logger.warning(f"无法获取音频时长，使用估算时长: {str(e)}")
                    estimated_duration = len(script) * 0.1  # 简单估算：每个字符0.1秒
                    return audio_path, [{'text': script, 'duration': estimated_duration, 'start_time': 0, 'end_time': estimated_duration}]
            
            self.logger.info(f"文本分割为 {len(text_segments)} 个段落")
            
            # 创建分段音频输出目录
            segments_dir = self.temp_dir / f"tts_segments_{task_id}"
            segments_dir.mkdir(exist_ok=True)
            
            # 分段合成TTS
            segments_info = self.tts_engine.synthesize_segments(
                text_segments,
                str(segments_dir),
                voice=self.tts_engine.voice,
                rate=self.tts_engine.rate,
                volume=self.tts_engine.volume,
                pitch=self.tts_engine.pitch
            )
            
            # 拼接音频文件
            segment_audio_paths = [seg['audio_path'] for seg in segments_info]
            final_audio_path = self.temp_dir / f"tts_{task_id}.mp3"
            
            # 使用FFmpeg拼接音频
            self.video_editor.ffmpeg.audio_processor.concat_audio_files(
                segment_audio_paths,
                str(final_audio_path)
            )
            
            total_duration = sum(seg['duration'] for seg in segments_info)
            try:
                merged_duration = self.tts_engine.get_audio_duration(str(final_audio_path))
            except Exception as duration_error:
                merged_duration = total_duration
                if self.logger:
                    self.logger.warning(
                        f"[TIMING] 无法获取拼接后音频时长，使用片段总时长: {duration_error}"
                    )

            scale_factor = 1.0
            if total_duration > 0 and abs(merged_duration - total_duration) > 0.05:
                scale_factor = merged_duration / total_duration
                if self.logger:
                    self.logger.info(
                        "[TIMING] 拼接后音频时长与片段总和存在差异，按比例校正字幕时间轴 "
                        f"(scale={scale_factor:.4f}, merged={merged_duration:.2f}s, "
                        f"segments={total_duration:.2f}s)"
                    )

            # 计算每段的时间轴（应用校准因子）
            current_time = 0.0
            for i, segment in enumerate(segments_info):
                adjusted_duration = segment['duration'] * scale_factor
                segment['duration'] = adjusted_duration
                segment['start_time'] = current_time
                segment['end_time'] = current_time + adjusted_duration
                current_time = segment['end_time']

                try:
                    Path(segment['audio_path']).unlink()
                except Exception:
                    pass

            # 将最后一段结束时间对齐到实际音频时长，避免累计误差
            if segments_info and abs(current_time - merged_duration) > 0.02:
                drift = merged_duration - current_time
                segments_info[-1]['duration'] += drift
                segments_info[-1]['end_time'] += drift
                current_time = merged_duration
                if self.logger:
                    self.logger.debug(
                        f"[TIMING] 已对齐最后一段结束时间，修正差值 {drift:.3f}s"
                    )
            
            # 清理分段目录
            try:
                segments_dir.rmdir()
            except Exception:
                pass
            
            self.logger.info(f"分段TTS合成完成，总时长: {current_time:.2f}秒")
            
            return str(final_audio_path), segments_info
            
        except Exception as e:
            self.logger.error(f"分段TTS生成失败: {str(e)}")
            # 回退到原始方法
            self.logger.info("回退到原始TTS方法")
            audio_path = self._generate_tts(script, task_id)
            # 获取实际音频时长
            try:
                actual_duration = self.tts_engine.get_audio_duration(audio_path)
                return audio_path, [{'text': script, 'duration': actual_duration, 'start_time': 0, 'end_time': actual_duration}]
            except Exception as duration_error:
                self.logger.warning(f"无法获取音频时长，使用估算时长: {str(duration_error)}")
                estimated_duration = len(script) * 0.1  # 简单估算：每个字符0.1秒
                return audio_path, [{'text': script, 'duration': estimated_duration, 'start_time': 0, 'end_time': estimated_duration}]
    
    def _generate_subtitles_from_segments(self, segments_info: list, task_id: str) -> str:
        """基于分段TTS信息生成字幕

        Args:
            segments_info: 段落信息列表，包含文本和时长
            task_id: 任务ID

        Returns:
            字幕文件路径
        """
        try:
            subtitle_path = self.temp_dir / f"subtitle_{task_id}.srt"

            # 获取视频配置用于计算每行最大字符数
            video_config = self.config_manager.get_section('video')
            video_width = video_config.get('resolution', [1080, 1920])[0]  # 获取宽度
            max_chars_per_line = self.subtitle_renderer._calculate_max_chars_per_line(video_width)

            self.logger.info(f"字幕换行参数: 视频宽度={video_width}px, 每行最大字符数={max_chars_per_line}")

            # 智能分段处理
            processed_segments = self._smart_segmentation(segments_info, max_chars_per_line)

            # 生成SRT格式字幕
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(processed_segments, start=1):
                    start_time = segment['start_time']
                    end_time = segment['end_time']

                    # 如果有原始文本（包含XML标记），则使用原始文本，否则使用清理后的文本
                    text = segment.get('original_text', segment['text'])

                    # ✨ 新增：文本预处理和验证
                    text = self._preprocess_subtitle_text(text)

                    # 验证文本处理结果
                    original_length = len(segment.get('original_text', segment['text']))
                    processed_length = len(text)
                    if processed_length < original_length * 0.5:
                        self.logger.warning(f"段落{i} 文本长度变化过大：{original_length} -> {processed_length}，可能存在问题")

                    # ✨ 新增：预处理文本，智能换行
                    if len(text) > max_chars_per_line:
                        if has_xml_color_tags(text):
                            # 处理带颜色标记的文本
                            text = self.subtitle_renderer._split_xml_text_by_line_length(
                                text, max_chars_per_line
                            )
                            self.logger.debug(f"段落{i} 包含颜色标记，已应用XML文本换行")
                        else:
                            # 处理普通文本
                            text = self.subtitle_renderer._split_text_by_line_length(
                                text, max_chars_per_line
                            )
                            self.logger.debug(f"段落{i} 已应用普通文本换行")

                        # 将ASS格式的\N换行符转换为SRT格式的实际换行
                        text = text.replace('\\N', '\n')
                    else:
                        self.logger.debug(f"段落{i} 长度{len(text)}未超过{max_chars_per_line}，无需换行")

                    # 最终文本验证和清理
                    text = self._final_text_cleanup(text)

                    # 格式化时间轴
                    start_str = self._format_srt_time(start_time)
                    end_str = self._format_srt_time(end_time)

                    # 写入SRT格式
                    f.write(f"{i}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{text}\n\n")

            self.logger.info(f"基于分段TTS信息生成字幕完成: {subtitle_path}, 共{len(processed_segments)}条字幕")
            return str(subtitle_path)

        except Exception as e:
            self.logger.error(f"基于分段TTS信息生成字幕失败: {str(e)}")
            raise

    def _smart_segmentation(self, segments_info: list, max_chars_per_line: int) -> list:
        """智能分段处理，确保字幕显示效果良好

        Args:
            segments_info: 原始段落信息列表
            max_chars_per_line: 每行最大字符数

        Returns:
            处理后的段落信息列表
        """
        processed_segments = []

        for segment in segments_info:
            text = segment.get('original_text', segment['text'])
            duration = segment['duration']
            start_time = segment['start_time']
            end_time = segment['end_time']

            # 如果只有一个段落且文本很长，进行智能分割
            if len(segments_info) == 1 and len(text) > max_chars_per_line * 2:
                self.logger.info(f"单段落文本过长({len(text)}字符)，进行智能分割")

                # 按句子分割
                sentences = self._split_text_to_sentences(text)

                if len(sentences) > 1:
                    lengths = [max(len(sentence.strip()), 1) for sentence in sentences]
                    total_length = sum(lengths)
                    cursor = start_time

                    for sentence, seg_len in zip(sentences, lengths):
                        ratio = seg_len / total_length if total_length else 1 / len(sentences)
                        sentence_duration = duration * ratio
                        sentence_start = cursor
                        sentence_end = sentence_start + sentence_duration
                        cursor = sentence_end

                        processed_segments.append({
                            'text': sentence.strip(),
                            'original_text': sentence.strip(),
                            'duration': sentence_duration,
                            'start_time': sentence_start,
                            'end_time': sentence_end
                        })

                    # 对齐最后一句结束时间，避免浮点误差累积
                    if processed_segments:
                        drift = (start_time + duration) - processed_segments[-1]['end_time']
                        if abs(drift) > 1e-3:
                            processed_segments[-1]['duration'] += drift
                            processed_segments[-1]['end_time'] += drift
                else:
                    # 如果无法按句子分割，按长度强制分割
                    chunks = self._split_long_text(text, max_chars_per_line * 2)
                    lengths = [max(len(chunk.strip()), 1) for chunk in chunks]
                    total_length = sum(lengths)
                    cursor = start_time

                    for chunk, seg_len in zip(chunks, lengths):
                        ratio = seg_len / total_length if total_length else 1 / len(chunks)
                        chunk_duration = duration * ratio
                        chunk_start = cursor
                        chunk_end = chunk_start + chunk_duration
                        cursor = chunk_end

                        processed_segments.append({
                            'text': chunk.strip(),
                            'original_text': chunk.strip(),
                            'duration': chunk_duration,
                            'start_time': chunk_start,
                            'end_time': chunk_end
                        })

                    if processed_segments:
                        drift = (start_time + duration) - processed_segments[-1]['end_time']
                        if abs(drift) > 1e-3:
                            processed_segments[-1]['duration'] += drift
                            processed_segments[-1]['end_time'] += drift
            else:
                # 保持原有分段，但确保时间信息正确
                processed_segments.append({
                    'text': text,
                    'original_text': text,
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': end_time
                })

        self.logger.info(f"智能分段完成: {len(segments_info)} -> {len(processed_segments)} 个段落")
        return processed_segments

    def _split_text_to_sentences(self, text: str) -> list:
        """将文本分割为句子

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        import re
        # 按中英文标点符号分割
        sentences = re.split(r'[。！？.!?]+', text)
        # 过滤空句子并保留标点符号
        sentences = [s.strip() for s in sentences if s.strip()]

        # 如果分割后只有一个句子，尝试按逗号分割
        if len(sentences) <= 1:
            sentences = re.split(r'[，,、；;]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

        return sentences if sentences else [text]

    def _split_long_text(self, text: str, max_length: int) -> list:
        """将长文本按长度分割

        Args:
            text: 输入文本
            max_length: 每段最大长度

        Returns:
            文本段落列表
        """
        chunks = []
        current_chunk = ""

        for char in text:
            if len(current_chunk) >= max_length:
                chunks.append(current_chunk)
                current_chunk = char
            else:
                current_chunk += char

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _format_srt_time(self, seconds: float) -> str:
        """格式化时间为SRT格式
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT格式时间字符串 (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _assemble_video(
        self,
        scenes: List[Dict[str, Any]],
        materials: List[str],
        task_id: str
    ) -> str:
        """组装视频
        
        Args:
            scenes: 场景列表
            materials: 素材路径列表
            task_id: 任务ID
            
        Returns:
            视频文件路径
        """
        try:
            video_path = self.temp_dir / f"video_no_audio_{task_id}.mp4"
            result = self.video_editor.create_video(scenes, materials, str(video_path), cleanup_temp=False)
            # 将临时文件添加到统一清理列表
            if 'temp_files' in result:
                self.temp_files.extend(result['temp_files'])
            return result['output_path']
        except VideoProcessingError as e:
            self.logger.error(f"视频组装失败: {str(e)}")
            raise
    
    def _add_audio(self, video_path: str, audio_path: str, task_id: str) -> str:
        """添加音频轨道
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            task_id: 任务ID
            
        Returns:
            带音频的视频文件路径
        """
        try:
            output_path = self.temp_dir / f"video_with_audio_{task_id}.mp4"
            self.video_editor.add_audio_track(video_path, audio_path, str(output_path))
            return str(output_path)
        except VideoProcessingError as e:
            self.logger.error(f"音频添加失败: {str(e)}")
            raise
    
    def _render_subtitles(self, video_path: str, subtitle_path: str, task_id: str) -> str:
        """渲染字幕到视频

        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
            task_id: 任务ID

        Returns:
            最终视频文件路径
        """
        try:
            final_path = self.output_dir / f"final_video_{task_id}.mp4"

            # 检查SRT文件中的文本是否包含XML颜色标记
            contains_color_tags = False
            if Path(subtitle_path).exists():
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                    contains_color_tags = has_xml_color_tags(srt_content)

            if contains_color_tags:
                # 如果SRT文件包含颜色标记，我们先解析SRT，然后使用支持颜色的render_subtitles方法
                subtitles = self.subtitle_renderer._parse_srt(subtitle_path)
                result = self.subtitle_renderer.render_subtitles(video_path, subtitles, str(final_path))
            else:
                # 否则使用原来的方法
                result = self.subtitle_renderer.render_from_srt(video_path, subtitle_path, str(final_path))

            return result
        except SubtitleError as e:
            self.logger.error(f"字幕渲染失败: {str(e)}")
            raise
    
    def execute_video_generation_pipeline_with_script(
        self,
        description: str,
        duration_seconds: int,
        script: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> str:
        """使用已有口播文案执行视频生成流水线

        Args:
            description: 用户输入的视频描述
            duration_seconds: 视频时长（秒）
            script: 已生成的口播文案
            progress_callback: 进度回调函数,接收(步骤描述, 进度百分比)

        Returns:
            最终视频文件路径

        Raises:
            AutoVideoException: 流水线执行失败时抛出
        """
        # 生成唯一的任务ID
        task_id = str(uuid.uuid4())[:8]
        self.logger.info(f"========== 开始执行视频生成任务 [Task ID: {task_id}] ==========")
        self.logger.info(f"用户描述: {description}")
        self.logger.info(f"目标时长: {duration_seconds} 秒")
        self.logger.info(f"使用已有口播文案，长度: {len(script)} 字符")

        # 临时文件列表,用于最后清理
        temp_files = []

        try:
            # 步骤1: 验证口播文案
            self._update_progress(progress_callback, "正在验证口播文案...", 5)
            self.logger.info("步骤1: 验证口播文案")
            if not script or not script.strip():
                raise ValueError("口播文案为空，无法生成视频")
            self.logger.info(f"口播文案验证通过,长度: {len(script)} 字符")

            # 步骤2: 解析场景列表
            self._update_progress(progress_callback, "正在解析场景列表...", 20)
            self.logger.info("步骤2: 解析场景列表")
            scenes = self._parse_scenes(script, duration_seconds)
            self.logger.info(f"场景解析完成,共 {len(scenes)} 个场景")

            # 步骤3: 生成TTS语音（提前生成以获取实际时长）
            self._update_progress(progress_callback, "正在生成语音...", 40)
            self.logger.info("步骤3: 生成分段TTS语音")
            tts_audio_path, segments_info = self._generate_tts_with_segments(script, task_id)
            temp_files.append(tts_audio_path)
            self.logger.info(f"分段TTS音频生成完成: {tts_audio_path}")
            
            # 计算实际音频时长
            actual_audio_duration = sum(seg['duration'] for seg in segments_info)
            self.logger.info(f"实际音频时长: {actual_audio_duration:.2f}秒")
            
            # 步骤4: 根据实际音频时长重新选择素材
            self._update_progress(progress_callback, "正在重新选择素材...", 30)
            self.logger.info("步骤4: 根据实际音频时长重新选择素材")
            materials = self._select_materials_for_duration(scenes, actual_audio_duration)
            self.logger.info(f"素材选择完成,共 {len(materials)} 个素材")

            # 步骤5: 组装视频
            self._update_progress(progress_callback, "正在组装视频...", 50)
            self.logger.info("步骤5: 组装视频")
            video_without_audio_path = self._assemble_video(scenes, materials, task_id)
            temp_files.append(video_without_audio_path)
            self.logger.info(f"视频组装完成: {video_without_audio_path}")

            # 步骤6: 添加音频轨道
            self._update_progress(progress_callback, "正在添加音频...", 60)
            self.logger.info("步骤6: 添加音频轨道")
            video_with_audio_path = self._add_audio(video_without_audio_path, tts_audio_path, task_id)
            temp_files.append(video_with_audio_path)
            self.logger.info(f"音频添加完成: {video_with_audio_path}")

            # 步骤7: 生成字幕
            self._update_progress(progress_callback, "正在生成字幕...", 70)
            self.logger.info("步骤7: 基于分段TTS信息生成字幕")
            try:
                subtitle_path = self._generate_subtitles_from_segments(segments_info, task_id)
                temp_files.append(subtitle_path)
                self.logger.info(f"基于分段TTS信息生成字幕完成: {subtitle_path}")
            except Exception as e:
                self.logger.warning(f"基于分段TTS信息生成字幕失败，回退到Whisper: {str(e)}")
                subtitle_path = self._generate_subtitles(tts_audio_path, task_id)
                temp_files.append(subtitle_path)
                self.logger.info(f"Whisper字幕生成完成: {subtitle_path}")

            # 步骤8: 渲染字幕到视频
            self._update_progress(progress_callback, "正在渲染字幕...", 85)
            self.logger.info("步骤8: 渲染字幕到视频")
            final_video_path = self._render_subtitles(video_with_audio_path, subtitle_path, task_id)
            self.logger.info(f"字幕渲染完成: {final_video_path}")

            # 步骤9: 清理临时文件
            self._update_progress(progress_callback, "正在清理临时文件...", 95)
            self.logger.info("步骤9: 清理临时文件")
            self._cleanup_temp_files(temp_files)

            # 完成
            self._update_progress(progress_callback, "视频生成完成!", 100)
            self.logger.info(f"========== 视频生成任务完成 [Task ID: {task_id}] ==========")
            self.logger.info(f"最终视频路径: {final_video_path}")

            return final_video_path

        except Exception as e:
            self.logger.error(f"视频生成流水线执行失败: {str(e)}")
            self.logger.exception("详细错误信息:")

            # 清理临时文件
            self.logger.info("清理临时文件")
            self._cleanup_temp_files(temp_files)

            # 重新抛出异常
            if isinstance(e, AutoVideoException):
                raise
            else:
                raise AutoVideoException(f"视频生成失败: {str(e)}")

    def _cleanup_temp_files(self, temp_files: List[str]) -> None:
        """清理临时文件
        
        Args:
            temp_files: 临时文件路径列表
        """
        for file_path in temp_files:
            try:
                if Path(file_path).exists():
                    Path(file_path).unlink()
                    self.logger.debug(f"已删除临时文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"删除临时文件失败 {file_path}: {str(e)}")
    
    def _update_progress(
        self,
        callback: Optional[Callable[[str, int], None]],
        message: str,
        percentage: int
    ) -> None:
        """更新进度
        
        Args:
            callback: 进度回调函数
            message: 进度消息
            percentage: 进度百分比(0-100)
        """
        if callback:
            try:
                callback(message, percentage)
            except Exception as e:
                self.logger.warning(f"进度回调执行失败: {str(e)}")
    
    def get_task_info(self, task_id: str) -> Dict[str, Any]:
        """获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典
        """
        # 可以扩展为从数据库或文件中读取任务信息
        return {
            'task_id': task_id,
            'status': 'completed',
            'output_dir': str(self.output_dir)
        }
    
    def list_available_materials(self) -> List[Dict[str, Any]]:
        """列出可用素材
        
        Returns:
            素材列表
        """
        return list(self.material_searcher.material_index.values())
    
    def refresh_material_index(self) -> None:
        """刷新素材索引"""
        self.logger.info("刷新素材索引")
        self.material_searcher.build_index()
        self.random_material_selector.build_index()
        self.logger.info("素材索引刷新完成")

    def get_material_stats(self) -> Dict[str, Any]:
        """获取素材统计信息

        Returns:
            素材统计字典
        """
        random_stats = self.random_material_selector.get_material_stats()
        material_search_config = self.config_manager.get_section('material_search')
        semantic_stats = {
            'semantic_material_count': len(self.material_searcher.material_index),
            'semantic_enabled': not material_search_config.get('deprecated', False)
        }

        return {**random_stats, **semantic_stats}

    def _preprocess_subtitle_text(self, text: str) -> str:
        """预处理字幕文本，清理多余换行和空白

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        if not text:
            return text

        # 如果包含XML标记，使用保留标记的清理函数
        if has_xml_color_tags(text):
            text = clean_xml_preserving_tags(text)
        else:
            # 普通文本使用标准清理
            text = clean_text(text, remove_extra_spaces=True)

        return text

    def _final_text_cleanup(self, text: str) -> str:
        """最终文本清理，确保字幕显示质量

        Args:
            text: 待清理的文本

        Returns:
            最终清理后的文本
        """
        if not text:
            return text

        # 移除多余的连续换行符
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 移除行首行尾的空白字符
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        # 重新组合，保留合理的换行
        result = '\n'.join(cleaned_lines)

        # 如果结果为空，返回原始文本的清理版本
        if not result:
            result = clean_text(text, remove_extra_spaces=True)

        return result
