"""
核心模块包

包含配置管理、日志管理和异常处理等核心功能。
"""

from .config import ConfigManager
from .logger import Logger
from .exceptions import (
    AutoVideoException,
    ConfigError,
    LLMError,
    TTSError,
    VideoProcessingError,
    MaterialNotFoundError,
)

__all__ = [
    "ConfigManager",
    "Logger",
    "AutoVideoException",
    "ConfigError",
    "LLMError",
    "TTSError",
    "VideoProcessingError",
    "MaterialNotFoundError",
]