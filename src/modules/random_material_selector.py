"""
随机素材选择器模块

从素材库中随机选择合适的视频和图片素材。
"""

import random
from typing import Any, Dict, List
from pathlib import Path
from ..core.exceptions import MaterialNotFoundError
from ..core.logger import Logger


class RandomMaterialSelector:
    """随机素材选择器类

    从素材库中随机选择指定数量和类型的素材。
    """

    def __init__(self, config: Dict[str, Any], logger: Logger = None):
        """初始化随机素材选择器

        Args:
            config: 素材选择配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger

        self.materials_dir = Path(config.get('materials_dir', './data/materials'))
        self.supported_formats = config.get(
            'supported_formats',
            ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts', '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        )
        
        # 使用FFmpegWrapper的格式检测方法
        from ..utils.ffmpeg_wrapper import FFmpegWrapper
        self.ffmpeg_wrapper = FFmpegWrapper()
        self.video_formats = self.ffmpeg_wrapper.get_supported_video_formats()
        self.image_formats = self.ffmpeg_wrapper.get_supported_image_formats()

        # 每个场景需要的素材数量配置
        self.materials_per_scene = max(1, int(config.get('materials_per_scene', 1)))
        self.video_priority = config.get('video_priority', True)  # 优先选择视频
        self.min_material_usage = max(1, int(config.get('min_material_usage', 10)))  # 默认每个素材至少使用10秒
        self.allow_reuse = bool(config.get('allow_reuse', True))

        # 素材索引
        self.video_materials = []
        self.image_materials = []

        if self.logger:
            self.logger.info("随机素材选择器初始化完成")

    def build_index(self, materials_dir: str = None) -> None:
        """构建素材库索引

        Args:
            materials_dir: 素材目录路径
        """
        if materials_dir:
            self.materials_dir = Path(materials_dir)

        if not self.materials_dir.exists():
            if self.logger:
                self.logger.warning(f"素材目录不存在: {self.materials_dir}")
            self.materials_dir.mkdir(parents=True, exist_ok=True)
            return

        if self.logger:
            self.logger.info(f"开始扫描素材目录: {self.materials_dir}")

        # 清空现有索引
        self.video_materials = []
        self.image_materials = []

        # 遍历素材目录
        for file_path in self.materials_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                material_info = self._extract_material_info(file_path)

                if material_info['type'] == 'video':
                    self.video_materials.append(material_info)
                elif material_info['type'] == 'image':
                    self.image_materials.append(material_info)

        if self.logger:
            self.logger.info(f"素材索引构建完成: 视频素材 {len(self.video_materials)} 个, 图片素材 {len(self.image_materials)} 个")

    def _extract_material_info(self, file_path: Path) -> Dict[str, Any]:
        """提取素材元信息

        Args:
            file_path: 素材文件路径

        Returns:
            素材信息字典
        """
        filename = file_path.stem
        description = filename.replace('_', ' ').replace('-', ' ')

        file_ext = file_path.suffix.lower()
        material_type = 'video' if file_ext in self.video_formats else 'image'

        return {
            'path': str(file_path),
            'filename': file_path.name,
            'type': material_type,
            'description': description,
            'extension': file_ext
        }

    def select_materials(self, scene_count: int, total_duration: int) -> List[str]:
        """随机选择素材

        Args:
            scene_count: 场景数量
            total_duration: 总时长（秒）

        Returns:
            选择的素材文件路径列表

        Raises:
            MaterialNotFoundError: 素材不足时抛出
        """
        if not self.video_materials and not self.image_materials:
            if self.logger:
                self.logger.warning("素材索引为空,尝试构建索引")
            self.build_index()

        if not self.video_materials and not self.image_materials:
            raise MaterialNotFoundError("素材库为空,无法进行选择")

        scene_count = max(scene_count, 0)
        total_duration = max(total_duration, 0)

        materials_by_scene = max(1, scene_count * self.materials_per_scene)
        materials_by_duration = max(1, (total_duration + self.min_material_usage - 1) // self.min_material_usage)
        total_materials_needed = max(materials_by_scene, materials_by_duration)

        if self.logger:
            self.logger.info(
                f"需要选择 {total_materials_needed} 个素材 (场景数: {scene_count}, 每场景: {self.materials_per_scene}, "
                f"时长: {total_duration}秒, 单素材最短使用: {self.min_material_usage}秒)"
            )

        selected_materials = []

        available_videos = self.video_materials.copy()
        available_images = self.image_materials.copy()
        random.shuffle(available_videos)
        random.shuffle(available_images)
        combined_materials = available_videos + available_images

        if not combined_materials:
            raise MaterialNotFoundError("素材库为空,无法进行选择")

        if self.video_priority:
            video_count = min(len(available_videos), total_materials_needed)
            selected_materials = [m['path'] for m in available_videos[:video_count]]

            remaining_needed = total_materials_needed - len(selected_materials)
            if remaining_needed > 0:
                selected_materials.extend([m['path'] for m in available_images[:remaining_needed]])
        else:
            random.shuffle(combined_materials)
            selected_materials = [m['path'] for m in combined_materials[:total_materials_needed]]

        if len(selected_materials) < total_materials_needed:
            if not self.allow_reuse:
                raise MaterialNotFoundError("素材数量不足且配置禁止复用")

            if self.logger:
                self.logger.warning(
                    f"选中素材不足 ({len(selected_materials)}/{total_materials_needed}), 根据配置允许复用, 将循环素材填充"
                )

            reuse_pool = combined_materials
            if not reuse_pool:
                raise MaterialNotFoundError("没有可复用的素材")

            reuse_index = 0
            while len(selected_materials) < total_materials_needed:
                material = reuse_pool[reuse_index % len(reuse_pool)]
                selected_materials.append(material['path'])
                reuse_index += 1

            if len(selected_materials) < total_materials_needed:
                raise MaterialNotFoundError("素材库内容不足以满足需求")

        if self.logger:
            video_count = sum(1 for m in selected_materials if Path(m).suffix.lower() in self.video_formats)
            image_count = len(selected_materials) - video_count
            self.logger.info(f"素材选择完成: 视频 {video_count} 个, 图片 {image_count} 个, 总计 {len(selected_materials)} 个")

        return selected_materials[:total_materials_needed]

    def get_material_stats(self) -> Dict[str, Any]:
        """获取素材统计信息

        Returns:
            素材统计字典
        """
        return {
            'video_count': len(self.video_materials),
            'image_count': len(self.image_materials),
            'total_count': len(self.video_materials) + len(self.image_materials),
            'materials_dir': str(self.materials_dir)
        }

    def refresh_index(self) -> None:
        """刷新素材索引

        重新扫描素材目录并更新索引。
        """
        if self.logger:
            self.logger.info("刷新素材索引")
        self.build_index()

    def validate_materials(self, material_paths: List[str]) -> List[str]:
        """验证素材文件是否存在

        Args:
            material_paths: 素材文件路径列表

        Returns:
            有效的素材文件路径列表
        """
        valid_materials = []

        for material_path in material_paths:
            if Path(material_path).exists():
                valid_materials.append(material_path)
            else:
                if self.logger:
                    self.logger.warning(f"素材文件不存在: {material_path}")

        if self.logger:
            self.logger.info(f"素材验证完成: {len(valid_materials)}/{len(material_paths)} 个有效")

        return valid_materials
