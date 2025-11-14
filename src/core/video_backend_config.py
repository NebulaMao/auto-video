"""
视频后端配置模块

提供视频处理后端的配置和工厂类
"""

from typing import Dict, Any, Protocol
from .logger import Logger


class VideoBackendProtocol(Protocol):
    """视频后端协议接口"""

    def concat_videos(self, video_paths: list, output_path: str, **kwargs) -> str:
        """拼接视频"""
        ...

    def merge_audio_video(self, video_path: str, audio_path: str, output_path: str, **kwargs) -> str:
        """合并音频和视频"""
        ...

    def cut_video(self, input_path: str, output_path: str, start_time: float, duration: float, **kwargs) -> str:
        """截取视频片段"""
        ...


class VideoBackendConfig:
    """视频后端配置类"""

    # 支持的后端类型
    BACKEND_FFMPEG = "ffmpeg"
    BACKEND_MOVIEPY = "moviepy"

    def __init__(self, backend_type: str, resolution: list = None, fps: int = 30,
                 codec: str = "libx264", bitrate: str = "2000k",
                 audio_codec: str = "aac", audio_bitrate: str = "128k",
                 output_format: str = "mp4", logger: Logger = None):
        """初始化后端配置

        Args:
            backend_type: 后端类型 ("ffmpeg" 或 "moviepy")
            resolution: 视频分辨率 [width, height]
            fps: 帧率
            codec: 视频编解码器
            bitrate: 视频比特率
            audio_codec: 音频编解码器
            audio_bitrate: 音频比特率
            output_format: 输出格式
            logger: 日志记录器
        """
        self.backend = backend_type
        self.resolution = resolution or [1920, 1080]
        self.fps = fps
        self.codec = codec
        self.bitrate = bitrate
        self.audio_codec = audio_codec
        self.audio_bitrate = audio_bitrate
        self.output_format = output_format
        self.logger = logger

    def to_dict(self) -> Dict[str, Any]:
        """转换为配置字典

        Returns:
            配置字典
        """
        return {
            "backend": self.backend,
            "resolution": self.resolution,
            "fps": self.fps,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "audio_codec": self.audio_codec,
            "audio_bitrate": self.audio_bitrate,
            "format": self.output_format
        }

    def get_backend_name(self) -> str:
        """获取当前后端名称

        Returns:
            后端名称
        """
        return self.backend

    def is_moviepy_backend(self) -> bool:
        """检查是否使用MoviePy后端

        Returns:
            是否使用MoviePy后端
        """
        return self.backend == self.BACKEND_MOVIEPY

    def is_ffmpeg_backend(self) -> bool:
        """检查是否使用FFmpeg后端

        Returns:
            是否使用FFmpeg后端
        """
        return self.backend == self.BACKEND_FFMPEG


class VideoBackendFactory:
    """视频后端工厂类"""

    @staticmethod
    def create_backend(config: VideoBackendConfig, logger: Logger = None) -> VideoBackendProtocol:
        """创建视频处理后端实例

        Args:
            config: 后端配置对象
            logger: 日志记录器

        Returns:
            视频后端实例
        """
        if config.is_moviepy_backend():
            # 延迟导入避免循环依赖
            from ..modules.video_editor_moviepy import MoviePyVideoEditor
            if logger:
                logger.info("使用MoviePy作为视频处理后端")
            return MoviePyVideoEditor(config.to_dict(), logger)
        else:
            # 延迟导入避免循环依赖
            from ..utils.ffmpeg_wrapper import FFmpegWrapper
            if logger:
                logger.info("使用FFmpeg作为视频处理后端")
            return FFmpegWrapper(logger=logger)

    @staticmethod
    def create_backend_from_dict(config_dict: Dict[str, Any], logger: Logger = None) -> VideoBackendProtocol:
        """从配置字典创建视频处理后端实例

        Args:
            config_dict: 配置字典
            logger: 日志记录器

        Returns:
            视频后端实例
        """
        config = VideoBackendConfig(
            backend_type=config_dict.get("backend", "ffmpeg"),
            resolution=config_dict.get("resolution", [1920, 1080]),
            fps=config_dict.get("fps", 30),
            codec=config_dict.get("codec", "libx264"),
            bitrate=config_dict.get("bitrate", "2000k"),
            audio_codec=config_dict.get("audio_codec", "aac"),
            audio_bitrate=config_dict.get("audio_bitrate", "128k"),
            output_format=config_dict.get("format", "mp4"),
            logger=logger
        )

        return VideoBackendFactory.create_backend(config, logger)


def create_video_backend(config: Dict[str, Any], logger: Logger = None) -> VideoBackendProtocol:
    """创建视频后端实例的便捷函数

    Args:
        config: 配置字典
        logger: 日志记录器

    Returns:
        视频后端实例
    """
    backend_type = config.get("backend", "ffmpeg")

    # 特殊处理：如果使用FFmpeg后端，返回FFmpegWrapper实例
    if backend_type == "ffmpeg":
        from ..utils.ffmpeg_wrapper import FFmpegWrapper
        if logger:
            logger.info("使用FFmpeg作为视频处理后端")
        return FFmpegWrapper(logger=logger)
    else:
        return VideoBackendFactory.create_backend_from_dict(config, logger)