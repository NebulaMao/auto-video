"""
Gradio Web界面模块

提供基于Gradio的Web用户界面。
"""

from typing import Any, Dict, Tuple, Optional
import os
import gradio as gr
from pathlib import Path
from ..core.config import ConfigManager
from ..core.logger import Logger
from ..core.workflow_manager import WorkflowManager
from ..modules.llm_client import LLMClient
from ..modules.material_searcher import MaterialSearcher
from ..modules.tts_engine import TTSEngine
from ..modules.video_editor import VideoEditor
from ..modules.subtitle_renderer import SubtitleRenderer


class GradioApp:
    """Gradio应用类
    
    构建和管理Web用户界面。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: Logger = None):
        """初始化Gradio应用
        
        Args:
            config_manager: 配置管理器
            logger: 日志记录器
        """
        self.config_manager = config_manager
        self.config = config_manager.get_section('ui')
        self.logger = logger
        
        self.title = self.config.get('title', 'AutoVideo - 自动化宣传视频生成系统')
        self.description = self.config.get('description', '基于AI技术的自动化宣传视频生成工具')
        self.theme = self.config.get('theme', 'default')
        self.share = self.config.get('share', False)
        self.server_port = self.config.get('server_port', 7860)
        self.server_name = self.config.get('server_name', '127.0.0.1')
        
        # 初始化工作流管理器
        self.workflow_manager = WorkflowManager(self.config_manager)
        
        # 初始化各功能模块(延迟加载)
        self.llm_client = LLMClient(config_manager.get_section('llm'), logger)
        self.material_searcher = None
        self.tts_engine = None
        self.video_editor = None
        self.subtitle_renderer = None
        
        if self.logger:
            self.logger.info("Gradio应用初始化完成")
    
    def build_interface(self) -> gr.Blocks:
        """构建用户界面
        
        Returns:
            Gradio Blocks对象
        """
        with gr.Blocks(title=self.title, theme=self.theme) as app:
            # 标题和描述
            gr.Markdown(f"# {self.title}")
            gr.Markdown(self.description)
            
            with gr.Tabs():
                # 视频生成标签页
                with gr.Tab("视频生成"):
                    self._build_video_generation_tab()
                
                # 素材管理标签页
                with gr.Tab("素材管理"):
                    self._build_material_management_tab()
                
                # 配置设置标签页
                with gr.Tab("配置设置"):
                    self._build_settings_tab()
            
            # 底部信息
            gr.Markdown("---")
            gr.Markdown("AutoVideo v0.1.0 | 基于AI技术的自动化视频生成系统")
        
        return app
    
    def _build_video_generation_tab(self):
        """构建视频生成标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                # 输入区域
                gr.Markdown("### 1. 输入视频描述")
                video_description = gr.Textbox(
                    label="视频主题和内容描述",
                    placeholder="例如: 创建一个介绍公司产品的宣传视频...",
                    lines=4
                )

                # 时长选择
                video_duration = gr.Slider(
                    minimum=10,
                    maximum=600,
                    value=60,
                    step=5,
                    label="视频时长（秒）",
                    info="选择您想要的视频长度"
                )

                # 生成口播文案按钮
                generate_script_btn = gr.Button("生成口播文案", variant="primary")

                gr.Markdown("### 2. 查看/编辑口播文案")
                script_output = gr.Textbox(
                    label="口播文案",
                    lines=8,
                    interactive=True,  # ✨ 改为可编辑
                    placeholder="点击上方按钮自动生成，或直接在此输入您的口播文案..."
                )

                # 生成视频按钮
                generate_video_btn = gr.Button("生成视频", variant="primary", size="lg")
            
            with gr.Column(scale=1):
                # 输出区域
                gr.Markdown("### 3. 生成结果")
                
                # 进度显示
                progress_text = gr.Textbox(
                    label="处理进度",
                    value="等待开始...",
                    interactive=False
                )
                
                # 视频预览
                video_output = gr.Video(
                    label="生成的视频",
                    interactive=False
                )
                
                # 下载按钮
                download_btn = gr.Button("下载视频", variant="secondary")
        
        # 绑定事件
        generate_script_btn.click(
            fn=self._generate_script,
            inputs=[video_description, video_duration],
            outputs=[script_output]
        )
        
        generate_video_btn.click(
            fn=self._generate_video,
            inputs=[video_description, video_duration, script_output],
            outputs=[progress_text, video_output]
        )
    
    def _build_material_management_tab(self):
        """构建素材管理标签页"""
        gr.Markdown("### 素材库管理")
        
        with gr.Row():
            with gr.Column():
                search_query = gr.Textbox(
                    label="搜索素材",
                    placeholder="输入关键词搜索素材..."
                )
                search_btn = gr.Button("搜索", variant="primary")
            
            material_type = gr.Radio(
                label="素材类型",
                choices=["全部", "视频", "图片", "音频"],
                value="全部"
            )
        
        # 搜索结果
        search_results = gr.DataFrame(
            label="搜索结果",
            headers=["文件名", "类型", "路径", "相似度"],
            interactive=False
        )
        
        # 绑定事件
        search_btn.click(
            fn=self.search_materials,
            inputs=[search_query, material_type],
            outputs=[search_results]
        )
    
    def _build_settings_tab(self):
        """构建配置设置标签页"""
        gr.Markdown("### 系统配置")
        
        with gr.Accordion("LLM配置", open=False):
            llm_api_key = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="输入DeepSeek API密钥"
            )
            llm_model = gr.Textbox(
                label="模型名称",
                value="deepseek-chat"
            )
        
        with gr.Accordion("TTS配置", open=False):
            tts_engine = gr.Dropdown(
                label="TTS引擎",
                choices=["edge-tts", "pyttsx3"],
                value="edge-tts"
            )
            tts_voice = gr.Textbox(
                label="语音名称",
                value="zh-CN-XiaoxiaoNeural"
            )
        
        with gr.Accordion("视频配置", open=False):
            video_resolution = gr.Dropdown(
                label="分辨率",
                choices=["1920x1080", "1280x720", "720x480"],
                value="1920x1080"
            )
            video_fps = gr.Slider(
                label="帧率",
                minimum=24,
                maximum=60,
                value=30,
                step=1
            )
        
        save_config_btn = gr.Button("保存配置", variant="primary")
        config_status = gr.Textbox(label="状态", value="", interactive=False)
        
        # 绑定保存配置事件
        save_config_btn.click(
            fn=lambda: "配置保存功能待实现",
            outputs=[config_status]
        )
    
    def _generate_script(self, description: str, duration: int, progress=gr.Progress()) -> str:
        """生成口播文案"""
        if not description or not description.strip():
            return "请输入有效的视频描述"

        try:
            # 使用LLM生成口播文案
            self.logger.info(f"开始生成口播文案: {description}, 时长: {duration}秒")
            script = self.llm_client.generate_script(description, duration)

            if script:
                self.logger.info("口播文案生成成功")
                return script
            else:
                return "口播文案生成失败,请重试"

        except Exception as e:
            self.logger.error(f"口播文案生成失败: {str(e)}")
            return f"口播文案生成失败: {str(e)}"
    
    def _generate_video(self, description: str, duration: int, script: str, progress=gr.Progress()) -> tuple:
        """生成视频"""
        if not description or not description.strip():
            return "请输入有效的视频描述", None

        # 检查口播文案是否为空，如果为空则自动重新生成
        if not script or not script.strip():
            self.logger.info("口播文案为空，正在自动重新生成...")
            try:
                script = self._generate_script(description, duration)
                if not script or not script.strip():
                    return "口播文案生成失败，请检查网络连接或API配置", None
                self.logger.info(f"自动重新生成口播文案成功，长度: {len(script)} 字符")
            except Exception as e:
                self.logger.error(f"自动重新生成口播文案失败: {str(e)}")
                return f"口播文案生成失败: {str(e)}", None

        try:
            self.logger.info(f"开始生成视频: {description}, 时长: {duration}秒")
            self.logger.info(f"使用口播文案，长度: {len(script)} 字符")

            # 定义进度回调函数
            def progress_callback(message: str, percentage: int):
                progress(percentage / 100, desc=message)
                self.logger.info(f"进度 {percentage}%: {message}")

            # 执行视频生成流水线，传入口播文案
            video_path = self.workflow_manager.execute_video_generation_pipeline_with_script(
                description=description,
                duration_seconds=duration,
                script=script,
                progress_callback=progress_callback
            )

            if video_path and os.path.exists(video_path):
                self.logger.info(f"视频生成成功: {video_path}")
                return f"视频生成成功!保存位置: {video_path}", video_path
            else:
                return "视频生成失败,请检查日志", None

        except Exception as e:
            self.logger.error(f"视频生成失败: {str(e)}")
            import traceback
            return f"视频生成失败: {str(e)}\n{traceback.format_exc()}", None
    
    def preview_script(self, prompt: str, duration: int = 60) -> str:
        """预览生成的口播文案(兼容旧接口)

        Args:
            prompt: 用户输入的描述
            duration: 视频时长（秒）

        Returns:
            生成的口播文案文本
        """
        script = self._generate_script(prompt, duration)
        return script

    def generate_video(self, description: str, script: str, duration: int = 60) -> Tuple[str, str]:
        """生成视频(兼容旧接口)

        Args:
            description: 视频描述
            script: 口播文案
            duration: 视频时长（秒）

        Returns:
            (视频文件路径, 进度信息)
        """
        progress_text, video_path = self._generate_video(description, duration, script)
        return video_path, progress_text
    
    def search_materials(self, query: str, material_type: str) -> list:
        """搜索素材
        
        Args:
            query: 搜索查询
            material_type: 素材类型
            
        Returns:
            搜索结果列表
        """
        try:
            if not query:
                return []
            
            if self.logger:
                self.logger.info(f"搜索素材: {query}")
            
            # TODO: 调用素材检索器
            results = []
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"素材搜索失败: {str(e)}")
            return []
    
    def launch(self) -> None:
        """启动Gradio应用"""
        if self.logger:
            self.logger.info(f"启动Gradio应用: {self.server_name}:{self.server_port}")
        
        app = self.build_interface()
        app.launch(
            server_name=self.server_name,
            server_port=self.server_port,
            share=self.share
        )
