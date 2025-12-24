"""
配置管理模块

负责加载和管理系统配置文件。
"""

import os
from typing import Any, Dict, Optional
import toml
from pathlib import Path


class ConfigManager:
    """配置管理器类
    
    负责加载、验证和提供配置项的访问接口。
    """
    
    def __init__(self, config_path: str = "config.toml"):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = toml.load(f)
        except Exception as e:
            raise ValueError(f"配置文件加载失败: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置项
        
        Args:
            section: 配置节名称
            key: 配置项键名
            default: 默认值
            
        Returns:
            配置项的值
        """
        try:
            return self._config[section][key]
        except KeyError:
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取整个配置节
        
        Args:
            section: 配置节名称
            
        Returns:
            配置节的字典
        """
        return self._config.get(section, {})
    
    def reload(self) -> None:
        """重新加载配置文件"""
        self._load_config()
    
    def validate(self) -> bool:
        """验证配置文件的有效性
        
        Returns:
            配置是否有效
        """
        required_sections = ['app', 'llm', 'tts', 'video', 'paths']
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"缺少必需的配置节: {section}")
        
        # 验证路径配置
        paths = self.get_section('paths')
        for path_key, path_value in paths.items():
            if path_key.endswith('_dir'):
                path_obj = Path(path_value)
                if not path_obj.exists():
                    os.makedirs(path_obj, exist_ok=True)
        
        return True
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问
        
        Args:
            key: 配置节名称
            
        Returns:
            配置节内容
        """
        return self._config[key]
    
    def __contains__(self, key: str) -> bool:
        """支持in操作符
        
        Args:
            key: 配置节名称
            
        Returns:
            是否包含该配置节
        """
        return key in self._config