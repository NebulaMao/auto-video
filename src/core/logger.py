"""
日志管理模块

提供统一的日志记录接口。
"""

import logging
import os
from typing import Any, Dict
from pathlib import Path
from logging.handlers import RotatingFileHandler
import colorlog


class Logger:
    """日志管理器类
    
    提供统一的日志记录接口,支持控制台和文件输出。
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """初始化日志管理器
        
        Args:
            name: 日志记录器名称
            config: 日志配置字典
        """
        self.name = name
        self.config = config
        self.logger = logging.getLogger(name)
        
        # 设置日志级别
        level = config.get('level', 'INFO')
        self.logger.setLevel(getattr(logging, level))
        
        # 防止日志重复
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """设置日志处理器"""
        # 控制台处理器(彩色输出)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        # 彩色格式化器
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        log_file = self.config.get('file', './logs/autovideo.log')
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析文件大小
        max_size = self._parse_size(self.config.get('max_size', '10MB'))
        backup_count = self.config.get('backup_count', 5)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 文件格式化器
        file_formatter = logging.Formatter(
            self.config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """解析文件大小字符串
        
        Args:
            size_str: 大小字符串,如"10MB"
            
        Returns:
            字节数
        """
        units = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
        
        for unit, multiplier in units.items():
            if size_str.upper().endswith(unit):
                number = float(size_str[:-len(unit)])
                return int(number * multiplier)
        
        return int(size_str)
    
    def debug(self, message: str, **kwargs) -> None:
        """记录调试信息
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """记录一般信息
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """记录警告信息
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """记录错误信息
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误信息
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """记录异常信息(包含堆栈跟踪)
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self.logger.exception(message, extra=kwargs)