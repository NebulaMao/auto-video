"""
UI组件模块

提供可复用的UI组件。
"""

import gradio as gr
from typing import Any, Dict, List, Optional


class ComponentFactory:
    """UI组件工厂类
    
    创建常用的UI组件。
    """
    
    @staticmethod
    def create_file_upload(
        label: str = "上传文件",
        file_types: List[str] = None,
        **kwargs
    ) -> gr.File:
        """创建文件上传组件
        
        Args:
            label: 标签文本
            file_types: 允许的文件类型
            **kwargs: 额外参数
            
        Returns:
            文件上传组件
        """
        return gr.File(
            label=label,
            file_types=file_types,
            **kwargs
        )
    
    @staticmethod
    def create_progress_bar(
        label: str = "进度",
        **kwargs
    ) -> gr.Textbox:
        """创建进度条组件
        
        Args:
            label: 标签文本
            **kwargs: 额外参数
            
        Returns:
            进度显示组件
        """
        return gr.Textbox(
            label=label,
            value="0%",
            interactive=False,
            **kwargs
        )
    
    @staticmethod
    def create_video_player(
        label: str = "视频预览",
        **kwargs
    ) -> gr.Video:
        """创建视频播放器组件
        
        Args:
            label: 标签文本
            **kwargs: 额外参数
            
        Returns:
            视频播放器组件
        """
        return gr.Video(
            label=label,
            interactive=False,
            **kwargs
        )
    
    @staticmethod
    def create_config_panel(
        config: Dict[str, Any]
    ) -> gr.Accordion:
        """创建配置面板
        
        Args:
            config: 配置字典
            
        Returns:
            配置面板组件
        """
        with gr.Accordion("配置选项", open=False) as accordion:
            for key, value in config.items():
                if isinstance(value, bool):
                    gr.Checkbox(label=key, value=value)
                elif isinstance(value, int):
                    gr.Number(label=key, value=value)
                elif isinstance(value, float):
                    gr.Number(label=key, value=value)
                elif isinstance(value, str):
                    gr.Textbox(label=key, value=value)
                elif isinstance(value, list):
                    gr.Dropdown(label=key, choices=value, value=value[0] if value else None)
        
        return accordion


class ProgressTracker:
    """进度跟踪器类
    
    跟踪和显示任务进度。
    """
    
    def __init__(self):
        """初始化进度跟踪器"""
        self.current_step = 0
        self.total_steps = 0
        self.status_message = ""
    
    def start(self, total_steps: int, initial_message: str = "开始处理..."):
        """开始跟踪进度
        
        Args:
            total_steps: 总步骤数
            initial_message: 初始消息
        """
        self.current_step = 0
        self.total_steps = total_steps
        self.status_message = initial_message
    
    def update(self, step: int = None, message: str = None):
        """更新进度
        
        Args:
            step: 当前步骤(可选,默认递增1)
            message: 状态消息
        """
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
        
        if message:
            self.status_message = message
    
    def get_progress(self) -> float:
        """获取进度百分比
        
        Returns:
            进度(0-1)
        """
        if self.total_steps == 0:
            return 0.0
        return min(1.0, self.current_step / self.total_steps)
    
    def get_status(self) -> str:
        """获取状态信息
        
        Returns:
            状态文本
        """
        progress_pct = int(self.get_progress() * 100)
        return f"[{progress_pct}%] {self.status_message}"
    
    def is_complete(self) -> bool:
        """检查是否完成
        
        Returns:
            是否完成
        """
        return self.current_step >= self.total_steps


def create_header(title: str, description: str = None):
    """创建页面标题
    
    Args:
        title: 标题文本
        description: 描述文本
    """
    gr.Markdown(f"# {title}")
    if description:
        gr.Markdown(description)
    gr.Markdown("---")


def create_footer(version: str = "0.1.0"):
    """创建页面底部
    
    Args:
        version: 版本号
    """
    gr.Markdown("---")
    gr.Markdown(f"AutoVideo v{version} | © 2024")