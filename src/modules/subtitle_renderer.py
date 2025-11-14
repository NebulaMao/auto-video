"""
字幕渲染模块

负责将字幕叠加到视频上,支持自定义样式。
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from ..core.exceptions import SubtitleError
from ..core.logger import Logger
from ..utils.ffmpeg_wrapper import FFmpegWrapper
from ..utils.text_utils import has_xml_color_tags, parse_color_segments


class SubtitleRenderer:
    """字幕渲染器类
    
    提供字幕样式设置和渲染功能。
    """
    
    def __init__(self, config: Dict[str, Any], logger: Logger = None):
        """初始化字幕渲染器

        Args:
            config: 字幕样式配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger

        # 初始化 FFmpeg 封装器
        self.ffmpeg = FFmpegWrapper(logger=logger)

        # 字幕样式配置
        self.font_family = config.get('font_family', 'SimHei')
        self.font_size = config.get('font_size', 36)
        self.font_color = config.get('font_color', '#FFFFFF')
        self.background_color = config.get('background_color', '#000000')
        self.background_alpha = config.get('background_alpha', 0.7)
        self.position = config.get('position', 'bottom')
        self.margin = config.get('margin', 50)
        self.alignment = config.get('alignment', 'center')
        self.outline_color = config.get('outline_color', '#000000')
        self.outline_width = config.get('outline_width', 2)
        self.max_width = config.get('max_width', 0.8)

        # 查找字体文件路径
        self.font_file = self._find_font_file(self.font_family)

        # 提取字体真实名称（用于ASS字幕）
        self.font_real_name = self._get_font_real_name(self.font_file) if self.font_file else self.font_family

        # Windows临时注册字体
        self.font_registered = False
        if self.font_file:
            self.font_registered = self._register_font_windows(self.font_file)

        if self.logger:
            self.logger.info("字幕渲染器初始化完成")
            if self.font_file:
                self.logger.info(f"找到字体文件: {self.font_file}")
                self.logger.info(f"字体名称: {self.font_real_name}")
                if self.font_registered:
                    self.logger.info(f"字体已临时注册到系统")
    
    def render_subtitles(
        self,
        video_path: str,
        subtitles: List[Dict[str, Any]],
        output_path: str,
        **kwargs
    ) -> str:
        """渲染字幕到视频

        Args:
            video_path: 视频文件路径
            subtitles: 字幕列表,每个字幕包含start、end和text
            output_path: 输出视频文件路径
            **kwargs: 额外的渲染参数

        Returns:
            带字幕的视频文件路径

        Raises:
            SubtitleError: 字幕渲染失败时抛出
        """
        if self.logger:
            self.logger.info(f"开始渲染字幕,字幕数量: {len(subtitles)}")

        try:
            if not subtitles:
                if self.logger:
                    self.logger.warning("没有有效的字幕需要渲染")
                return video_path

            use_ass = any(has_xml_color_tags(sub.get('text', '')) for sub in subtitles)

            if use_ass:
                return self._render_with_ass(video_path, subtitles, output_path, **kwargs)

            return self._render_with_drawtext(video_path, subtitles, output_path, **kwargs)

        except Exception as e:
            error_msg = f"字幕渲染失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise SubtitleError(error_msg)

    def _register_font_windows(self, font_path: str) -> bool:
        """在Windows上临时注册字体（进程级别）

        Args:
            font_path: 字体文件路径

        Returns:
            是否成功注册
        """
        import platform
        if platform.system() != "Windows":
            return False

        try:
            import ctypes
            from ctypes import wintypes

            # 加载 gdi32.dll
            gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

            # AddFontResourceExW 函数
            # https://docs.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-addfontresourceexw
            AddFontResourceEx = gdi32.AddFontResourceExW
            AddFontResourceEx.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID]
            AddFontResourceEx.restype = ctypes.c_int

            FR_PRIVATE = 0x10  # 私有字体，仅对当前进程可见
            FR_NOT_ENUM = 0x20  # 不枚举字体

            # 注册字体
            font_path_abs = str(Path(font_path).resolve())
            result = AddFontResourceEx(font_path_abs, FR_PRIVATE | FR_NOT_ENUM, 0)

            if result > 0:
                if self.logger:
                    self.logger.info(f"成功临时注册字体: {font_path_abs}")
                return True
            else:
                if self.logger:
                    self.logger.warning(f"字体注册失败: {font_path_abs}")
                return False

        except Exception as e:
            if self.logger:
                self.logger.warning(f"无法注册字体: {e}")
            return False

    def _unregister_font_windows(self, font_path: str) -> bool:
        """取消注册Windows字体

        Args:
            font_path: 字体文件路径

        Returns:
            是否成功取消注册
        """
        import platform
        if platform.system() != "Windows":
            return False

        try:
            import ctypes
            from ctypes import wintypes

            gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

            # RemoveFontResourceExW 函数
            RemoveFontResourceEx = gdi32.RemoveFontResourceExW
            RemoveFontResourceEx.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID]
            RemoveFontResourceEx.restype = wintypes.BOOL

            FR_PRIVATE = 0x10
            FR_NOT_ENUM = 0x20

            font_path_abs = str(Path(font_path).resolve())
            result = RemoveFontResourceEx(font_path_abs, FR_PRIVATE | FR_NOT_ENUM, 0)

            return bool(result)

        except Exception as e:
            if self.logger:
                self.logger.warning(f"无法取消注册字体: {e}")
            return False

    def __del__(self):
        """析构函数：清理临时注册的字体"""
        if hasattr(self, 'font_registered') and self.font_registered and hasattr(self, 'font_file'):
            if self.font_file:
                self._unregister_font_windows(self.font_file)

    def _get_font_real_name(self, font_file_path: str) -> str:
        """从字体文件中提取真实字体名称

        Args:
            font_file_path: 字体文件路径

        Returns:
            字体的真实名称，如果提取失败则返回文件名
        """
        try:
            from fontTools.ttLib import TTFont

            font = TTFont(font_file_path)
            name_table = font['name']

            # 尝试获取英文字体家族名称（ID 1，平台 ID 3，编码 ID 1）
            for record in name_table.names:
                if record.nameID == 1 and record.platformID == 3 and record.platEncID == 1:
                    font_name = record.toUnicode()
                    if font_name and not any(ord(c) > 127 for c in font_name):  # 确保是英文名称
                        return font_name

            # 如果没有找到英文名称，使用第一个字体家族名称
            for record in name_table.names:
                if record.nameID == 1:
                    font_name = record.toUnicode()
                    if font_name:
                        return font_name

            # 如果都失败了，返回文件名（不带扩展名）
            return Path(font_file_path).stem

        except Exception as e:
            if self.logger:
                self.logger.warning(f"无法提取字体名称: {e}，使用文件名")
            return Path(font_file_path).stem

    def _find_font_file(self, font_name: str) -> Optional[str]:
        """查找字体文件路径

        Args:
            font_name: 字体名称或字体文件路径

        Returns:
            字体文件的完整路径，如果找不到则返回None
        """
        import platform

        # 如果已经是一个有效的文件路径，直接返回
        font_path = Path(font_name)
        if font_path.exists() and font_path.is_file():
            return str(font_path.absolute())

        # Windows 系统字体映射
        if platform.system() == "Windows":
            windows_fonts_dir = Path("C:/Windows/Fonts")

            # 字体名称到文件名的映射
            font_mapping = {
                "Microsoft YaHei": ["msyh.ttc", "msyh.ttf", "msyhbd.ttc"],
                "SimHei": ["simhei.ttf"],
                "SimSun": ["simsun.ttc", "simsun.ttf"],
                "KaiTi": ["simkai.ttf"],
                "FangSong": ["simfang.ttf"],
                "Arial": ["arial.ttf"],
                "Times New Roman": ["times.ttf"],
            }

            # 查找匹配的字体文件
            possible_files = font_mapping.get(font_name, [])
            for font_file in possible_files:
                full_path = windows_fonts_dir / font_file
                if full_path.exists():
                    return str(full_path)

            # 如果映射中没有，尝试直接在字体目录中查找
            font_file = windows_fonts_dir / f"{font_name.lower().replace(' ', '')}.ttf"
            if font_file.exists():
                return str(font_file)

        # Linux/Mac 系统字体路径
        elif platform.system() in ["Linux", "Darwin"]:
            font_dirs = [
                Path("/usr/share/fonts"),
                Path.home() / ".fonts",
                Path.home() / "Library/Fonts",
            ]

            for font_dir in font_dirs:
                if font_dir.exists():
                    # 搜索字体文件
                    for ext in ['.ttf', '.otf', '.ttc']:
                        for font_file in font_dir.rglob(f"*{ext}"):
                            if font_name.lower() in font_file.name.lower():
                                return str(font_file.absolute())

        # 如果找不到，返回None
        if self.logger:
            self.logger.warning(f"未找到字体文件: {font_name}, 将使用FFmpeg默认字体")
        return None

    def _render_with_drawtext(
        self,
        video_path: str,
        subtitles: List[Dict[str, Any]],
        output_path: str,
        **kwargs
    ) -> str:
        """使用drawtext滤镜渲染字幕（向后兼容）"""
        # 确保输出目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 获取视频信息用于计算位置
        video_info = self.ffmpeg.get_video_info(video_path)
        video_width = video_info['width']
        video_height = video_info['height']

        # 构建复杂的 drawtext 滤镜链
        drawtext_filters = []

        for sub in subtitles:
            start = sub.get('start', 0)
            end = sub.get('end', start + 3)
            text = sub.get('text', '')

            if not text.strip():
                continue

            # 转义文本中的特殊字符
            text = text.replace("\\", "\\\\").replace("'", "'\\''").replace(":", r"\:")
            text = text.replace("%", "\\%").replace(",", "\\,")

            # 计算位置
            x_pos, y_pos = self._get_ffmpeg_position(video_width, video_height)

            # 转换颜色格式
            font_color = self._convert_color_to_ffmpeg(self.font_color)
            bg_color = self._convert_color_to_ffmpeg(self.background_color)

            # 添加透明度到背景颜色
            bg_color_with_alpha = f"{bg_color}@{self.background_alpha}"

            # 构建 drawtext 参数
            drawtext_parts = [
                f"text='{text}'",
                f"fontsize={self.font_size}",
                f"fontcolor={font_color}",
                f"x={x_pos}",
                f"y={y_pos}",
                f"enable='between(t,{start},{end})'",
                f"box=1",
                f"boxcolor={bg_color_with_alpha}",
                f"boxborderw=5"
            ]

            # 添加字体文件(如果找到)
            if self.font_file:
                # 转义字体路径 - Windows路径需要特殊处理
                font_file_escaped = str(self.font_file).replace('\\', '/').replace(':', r'\:')
                drawtext_parts.insert(1, f"fontfile='{font_file_escaped}'")

            # 添加描边效果
            if self.outline_width > 0:
                outline_color = self._convert_color_to_ffmpeg(self.outline_color)
                drawtext_parts.extend([
                    f"borderw={self.outline_width}",
                    f"bordercolor={outline_color}"
                ])

            drawtext_filter = "drawtext=" + ":".join(drawtext_parts)
            drawtext_filters.append(drawtext_filter)

        if not drawtext_filters:
            if self.logger:
                self.logger.warning("没有有效的字幕需要渲染")
            return video_path

        # 组合所有滤镜
        filter_chain = ",".join(drawtext_filters)

        # 使用 FFmpeg 渲染字幕
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', filter_chain,
            '-c:a', 'copy',  # 保持音频不变
            '-y',
            str(output_file)
        ]

        self.ffmpeg.error_handler.execute_command(cmd)

        if self.logger:
            self.logger.info(f"字幕渲染完成 (drawtext): {output_path}")

        return str(output_file)

    def _render_with_ass(
        self,
        video_path: str,
        subtitles: List[Dict[str, Any]],
        output_path: str,
        **kwargs
    ) -> str:
        """使用ASS字幕文件渲染字幕（支持颜色标记）"""
        # 确保输出目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 生成临时ASS文件路径
        ass_path = output_file.with_suffix('.ass')

        # 获取视频信息
        video_info = self.ffmpeg.get_video_info(video_path)

        # 创建ASS字幕文件
        ass_file = self.create_ass_subtitle_file(subtitles, str(ass_path), video_info)

        if self.logger:
            self.logger.info(f"已创建ASS字幕文件: {ass_file}")

        # 使用ASS字幕渲染视频
        # 使用相对路径，避免Windows路径问题
        ass_path_for_ffmpeg = str(ass_file)

        if self.logger:
            self.logger.debug(f"ASS文件路径 (FFmpeg): {ass_path_for_ffmpeg}")

        # 使用 subtitles 滤镜
        # 设置 FONTCONFIG_PATH 环境变量，让 libass 找到字体
        import os
        env = os.environ.copy()

        if self.font_file:
            font_dir = str(Path(self.font_file).parent.resolve())
            # 创建临时 fontconfig 配置
            fontconfig_dir = Path('data/temp/fontconfig')
            fontconfig_dir.mkdir(parents=True, exist_ok=True)

            fonts_conf = fontconfig_dir / 'fonts.conf'
            with open(fonts_conf, 'w', encoding='utf-8') as f:
                f.write(f'''<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <dir>{font_dir}</dir>
</fontconfig>
''')
            env['FONTCONFIG_FILE'] = str(fonts_conf.absolute())

        # 使用ASS字幕渲染视频
        # 确保路径使用正斜杠，避免FFmpeg路径问题
        ass_path_for_ffmpeg = str(ass_file).replace('\\', '/')

        if self.logger:
            self.logger.debug(f"ASS文件路径 (FFmpeg): {ass_path_for_ffmpeg}")

        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"subtitles='{ass_path_for_ffmpeg}'",
            '-c:a', 'copy',  # 保持音频不变
            '-y',
            str(output_file)
        ]

        # 执行命令，传递自定义环境变量
        import subprocess
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            if self.logger:
                self.logger.debug(f"FFmpeg 输出: {result.stdout}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            if self.logger:
                self.logger.error(f"FFmpeg 错误: {error_msg}")
            from ..core.exceptions import SubtitleError
            raise SubtitleError(f"字幕渲染失败: {error_msg}")

        # 清理临时ASS文件
        try:
            Path(ass_file).unlink()
        except Exception as e:
            if self.logger:
                self.logger.warning(f"无法删除临时ASS文件 {ass_file}: {str(e)}")

        if self.logger:
            self.logger.info(f"字幕渲染完成 (ASS): {output_path}")

        return str(output_file)
    
    def _get_ffmpeg_position(self, video_width: int, video_height: int) -> tuple:
        """计算 FFmpeg 字幕位置表达式
        
        Args:
            video_width: 视频宽度
            video_height: 视频高度
            
        Returns:
            (x表达式, y表达式) 元组
        """
        # x 位置：居中
        x_expr = '(w-text_w)/2'
        
        # y 位置：根据配置计算
        if self.position == 'top':
            y_expr = str(self.margin)
        elif self.position == 'center':
            y_expr = '(h-text_h)/2'
        elif self.position == 'bottom':
            y_expr = f'h-text_h-{self.margin}'
        else:
            # 默认底部
            y_expr = f'h-text_h-{self.margin}'
        
        return (x_expr, y_expr)
    
    def _convert_color_to_ffmpeg(self, color: str) -> str:
        """将颜色转换为 FFmpeg 格式
        
        Args:
            color: 颜色值 (#RRGGBB 或颜色名称)
            
        Returns:
            FFmpeg 颜色字符串
        """
        # 颜色名称映射
        color_map = {
            'white': 'white',
            'black': 'black',
            'red': 'red',
            'green': 'green',
            'blue': 'blue',
            'yellow': 'yellow',
            'cyan': 'cyan',
            'magenta': 'magenta'
        }
        
        color_lower = color.lower()
        if color_lower in color_map:
            return color_map[color_lower]
        
        # 处理 #RRGGBB 格式
        if color.startswith('#') and len(color) == 7:
            return color  # FFmpeg 支持 #RRGGBB 格式
        
        return 'white'  # 默认白色

    def create_ass_subtitle_file(self, subtitles: List[Dict[str, Any]], output_path: str, video_info: Dict[str, Any]) -> str:
        """创建ASS字幕文件

        Args:
            subtitles: 字幕列表，每个字幕包含start、end、text字段
            output_path: 输出ASS文件路径
            video_info: 视频信息（宽高等）

        Returns:
            ASS字幕文件路径
        """
        ass_path = Path(output_path)
        ass_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用字体真实名称
        font_name = self.font_real_name

        # 获取视频分辨率
        video_width = video_info.get('width', 1920)
        video_height = video_info.get('height', 1080)

        # 计算最大字符数（基于视频宽度和字体大小）
        max_chars_per_line = self._calculate_max_chars_per_line(video_width)

        # 根据配置确定ASS对齐方式
        # ASS Alignment值: 1=左下(上延), 2=中下(上延), 3=右下(上延),
        # 4=左中, 5=中中, 6=右中, 7=左上, 8=中上, 9=右上
        if self.position == 'top':
            alignment = 8  # 中上部，向下延伸
        elif self.position == 'center':
            alignment = 5  # 中部居中
        else:  # bottom
            alignment = 2  # 底部居中，向上延伸

        # ASS文件头部 - 添加视频分辨率信息和换行设置
        # WrapStyle: 0=智能换行, 1=行末换行, 2=不换行, 3=智能换行(下行更宽)
        # 使用WrapStyle: 0确保只在\N处换行，避免自动换行导致的显示问题
        ass_header = f"""[Script Info]
Title: AutoVideo Generated Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0
PlayDepth: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{self.font_size},{self._convert_to_ass_color(self.font_color)},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,{self.outline_width},0,{alignment},{self.margin},{self.margin},1

Style: Highlight,{font_name},{self.font_size},&H0000FFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,{self.outline_width},0,{alignment},10,10,{self.margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        # 生成字幕事件
        events = []
        for sub in subtitles:
            start_time = self._seconds_to_ass_time(sub.get('start', 0))
            end_time = self._seconds_to_ass_time(sub.get('end', 0))
            text = sub.get('text', '')

            if not text.strip():
                continue

            # 检查是否需要颜色处理
            if has_xml_color_tags(text):
                # 对XML文本进行智能分行（保留颜色标记），基于字符长度而非ASS代码长度
                from ..utils.xml_color_parser import clean_xml_tags
                clean_text = clean_xml_tags(text)

                if len(clean_text) > max_chars_per_line:
                    # 需要分行，使用改进的XML分割方法
                    text_with_breaks = self._split_xml_text_by_line_length(text, max_chars_per_line)
                    ass_text = self._convert_xml_to_ass(text_with_breaks)
                else:
                    # 不需要分行，直接转换
                    ass_text = self._convert_xml_to_ass(text)

                # 将真实换行符转换为ASS换行，避免破坏颜色标记
                ass_text = ass_text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\N')

                events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,{self.margin},,{ass_text}")
            else:
                # 普通文本，先智能分行
                # 转义特殊字符
                text = text.replace('\\', '\\\\').replace('\n', '\\N')

                # 智能分行处理
                text = self._split_text_by_line_length(text, max_chars_per_line)

                events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,{self.margin},,{text}")

        # 写入ASS文件
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ass_header)
            f.write('\n'.join(events))

        return str(ass_path)

    def _convert_to_ass_color(self, color: str) -> str:
        """将颜色转换为ASS格式 (&HBBGGRR&)"""
        # 颜色名称映射
        color_map = {
            'white': '&H00FFFFFF&',
            'black': '&H00000000&',
            'red': '&H000000FF&',
            'green': '&H0000FF00&',
            'blue': '&H00FF0000&',
            'yellow': '&H0000FFFF&',
            'cyan': '&H00FFFF00&',
            'magenta': '&H00FF00FF&'
        }

        color_lower = color.lower()
        if color_lower in color_map:
            return color_map[color_lower]

        # 处理 #RRGGBB 格式，转换为BGR
        if color.startswith('#') and len(color) == 7:
            r = color[1:3]
            g = color[3:5]
            b = color[5:7]
            return f'&H00{b}{g}{r}&'

        return '&H00FFFFFF&'  # 默认白色

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """将秒数转换为ASS时间格式 (H:MM:SS.cc)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)

        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

    def _convert_xml_to_ass(self, text: str) -> str:
        """将XML颜色标记转换为ASS格式"""
        try:
            # 使用XML颜色解析器
            from ..utils.xml_color_parser import text_to_ass_format
            return text_to_ass_format(text)
        except ImportError:
            # 如果解析器不可用，回退到基础处理
            import re

            # 简单的颜色标记替换
            color_map = {
                'yellow': '{\\c&H0000FFFF&}',
                'red': '{\\c&H000000FF&}',
                'blue': '{\\c&H00FF0000&}',
                'green': '{\\c&H0000FF00&}',
                'purple': '{\\c&H00FF00FF&}',
            }

            result = text
            for color, ass_code in color_map.items():
                # 替换开始标记
                result = re.sub(f'<{color}>', ass_code, result, flags=re.IGNORECASE)
                # 替换结束标记
                result = re.sub(f'</{color}>', '{\\c}', result, flags=re.IGNORECASE)

            # 移除未识别的标记
            result = re.sub(r'<[^>]+>', '', result)

            return result

    def _calculate_max_chars_per_line(self, video_width: int) -> int:
        """计算每行最大字符数

        Args:
            video_width: 视频宽度（像素）

        Returns:
            每行建议的最大字符数
        """
        # 计算公式：考虑视频宽度、字体大小和最大宽度比例
        # 实测发现中文字符宽度约为字体大小的0.7-0.75倍（字体本身+字间距）
        # 使用0.75作为字符宽度系数，确保显示安全

        # 可用宽度 = 视频宽度 * 最大宽度比例
        available_width = video_width * self.max_width

        # 每行字符数 = 可用宽度 / (字体大小 * 字符宽度系数)
        # 使用0.75系数：对于48px字体，每个中文字符约占36px宽度
        char_width_factor = 0.75
        chars_per_line = int(available_width / (self.font_size * char_width_factor))

        # 为了更安全，再减少5%的容量（避免临界情况）
        chars_per_line = int(chars_per_line * 0.95)

        # 设置合理的最小值和最大值
        chars_per_line = max(10, min(chars_per_line, 60))

        if self.logger:
            self.logger.debug(f"计算每行最大字符数: 视频宽度={video_width}, 字体大小={self.font_size}, "
                            f"可用宽度={available_width:.0f}px, 字符宽度系数={char_width_factor}, 最大字符数={chars_per_line}")

        return chars_per_line

    def _split_text_by_line_length(self, text: str, max_chars: int) -> str:
        r"""根据最大字符数智能分割文本，并尽量避免标点单独成行

        Args:
            text: 原始文本
            max_chars: 每行最大字符数

        Returns:
            包含换行标记(\N)的文本
        """
        if max_chars <= 0 or len(text) <= max_chars:
            return text

        paragraphs = text.split('\\N')
        wrapped_paragraphs = []
        for para in paragraphs:
            lines = self._split_plain_text_lines(para, max_chars)
            wrapped_paragraphs.append('\\N'.join(lines))

        result = '\\N'.join(wrapped_paragraphs)

        if self.logger and any('\\N' in para for para in wrapped_paragraphs):
            debug_lines = [line for para in wrapped_paragraphs for line in para.split('\\N')]
            self.logger.debug(f"文本已分成 {len(debug_lines)} 行: {debug_lines}")

        return result

    def _split_xml_text_by_line_length(self, xml_text: str, max_chars: int) -> str:
        r"""根据最大字符数智能分割带XML颜色标记的文本

        Args:
            xml_text: 带XML颜色标记的文本
            max_chars: 每行最大字符数

        Returns:
            在适当位置插入换行的XML文本
        """
        if max_chars <= 0:
            return xml_text

        from ..utils.xml_color_parser import parse_xml_color_text

        segments, _ = parse_xml_color_text(xml_text)
        plain_text = ''.join(seg.text for seg in segments)

        if len(plain_text) <= max_chars or not segments:
            return xml_text

        target_lines = self._split_plain_text_lines(plain_text, max_chars)
        if len(target_lines) <= 1:
            return xml_text

        line_segments: List[List[Tuple[str, str]]] = [[] for _ in target_lines]
        line_index = 0
        remaining = len(target_lines[line_index]) if target_lines[line_index] else 0

        for segment in segments:
            text = segment.text
            pos = 0
            while pos < len(text) and line_index < len(target_lines):
                if remaining == 0:
                    line_index += 1
                    if line_index >= len(target_lines):
                        break
                    remaining = len(target_lines[line_index])
                    continue

                take = min(len(text) - pos, remaining)
                chunk = text[pos:pos + take]
                line_segments[line_index].append((chunk, segment.color))
                pos += take
                remaining -= take

                if remaining == 0 and line_index < len(target_lines) - 1:
                    line_index += 1
                    remaining = len(target_lines[line_index])

        xml_lines: List[str] = []
        for segs in line_segments:
            line_text = ""
            for chunk, color in segs:
                if not chunk:
                    continue
                if color == 'default':
                    line_text += chunk
                else:
                    line_text += f"<{color}>{chunk}</{color}>"
            xml_lines.append(line_text)

        result = '\\N'.join(xml_lines)

        if self.logger:
            self.logger.debug(
                f"XML文本分行: 纯文本长度={len(plain_text)}, 生成 {len(xml_lines)} 行"
            )

        return result

    def _split_plain_text_lines(self, text: str, max_chars: int) -> List[str]:
        """将文本拆分为若干行，控制每行字符数并避免标点独立成行"""
        if text == "":
            return [""]

        if max_chars <= 0 or len(text) <= max_chars:
            return [text]

        lines: List[str] = []
        current_line = ""

        for char in text:
            current_line += char
            if len(current_line) >= max_chars:
                break_pos = self._find_break_position(current_line, max_chars)
                lines.append(current_line[:break_pos])
                current_line = current_line[break_pos:]

        if current_line:
            lines.append(current_line)

        return self._merge_leading_punctuation(lines)

    def _find_break_position(self, text: str, max_chars: int) -> int:
        """寻找合适的断点，优先在标点或空格处换行"""
        punctuation = '，。、；：！？,.!? '
        search_limit = max(len(text) - 10, 0)
        for idx in range(len(text) - 1, search_limit - 1, -1):
            if text[idx] in punctuation and idx != len(text) - 1:
                return idx + 1
        return min(max_chars, len(text))

    def _merge_leading_punctuation(self, lines: List[str]) -> List[str]:
        """将新行开头的标点移动到上一行，避免孤立标点"""
        if not lines:
            return []

        punctuation = '，。、；：！？,.!? '
        normalized = lines[:]

        for i in range(1, len(normalized)):
            while normalized[i] and normalized[i][0] in punctuation:
                normalized[i - 1] += normalized[i][0]
                normalized[i] = normalized[i][1:]

        # 清理因标点移动造成的空行（保留首个空行以支持手动换行）
        cleaned: List[str] = []
        for line in normalized:
            if not line and cleaned:
                continue
            cleaned.append(line)

        return cleaned or [""]
    
    def load_font(self, font_path: str) -> None:
        """加载字体文件
        
        Args:
            font_path: 字体文件路径
        """
        if not Path(font_path).exists():
            raise SubtitleError(f"字体文件不存在: {font_path}")
        
        self.font_family = font_path
        
        if self.logger:
            self.logger.info(f"字体已加载: {font_path}")
    
    def set_style(self, style: Dict[str, Any]) -> None:
        """设置字幕样式
        
        Args:
            style: 样式配置字典
        """
        for key, value in style.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        if self.logger:
            self.logger.info("字幕样式已更新")
    
    def add_subtitle_effects(
        self,
        video_path: str,
        output_path: str,
        effects: List[str],
        fade_duration: float = 0.5
    ) -> str:
        """为视频字幕添加特效
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            effects: 特效列表 ['fade_in', 'fade_out']
            fade_duration: 淡入淡出时长(秒)
            
        Returns:
            应用特效后的视频路径
        """
        if not effects:
            return video_path
        
        try:
            filters = []
            
            if 'fade_in' in effects:
                filters.append(f"fade=in:st=0:d={fade_duration}")
            
            if 'fade_out' in effects:
                # 获取视频时长
                video_info = self.ffmpeg.get_video_info(video_path)
                duration = video_info['duration']
                fade_start = duration - fade_duration
                filters.append(f"fade=out:st={fade_start}:d={fade_duration}")
            
            if filters:
                filter_chain = ",".join(filters)
                cmd = [
                    'ffmpeg', '-i', video_path,
                    '-vf', filter_chain,
                    '-c:a', 'copy',
                    '-y',
                    output_path
                ]
                self.ffmpeg.error_handler.execute_command(cmd)
                return output_path
            
            return video_path
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"添加特效失败: {str(e)}")
            raise SubtitleError(f"添加特效失败: {str(e)}")
    
    def render_from_srt(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        **kwargs
    ) -> str:
        """从SRT文件渲染字幕
        
        Args:
            video_path: 视频文件路径
            srt_path: SRT字幕文件路径
            output_path: 输出视频文件路径
            **kwargs: 额外的渲染参数
            
        Returns:
            带字幕的视频文件路径
            
        Raises:
            SubtitleError: 字幕渲染失败时抛出
        """
        if not Path(srt_path).exists():
            raise SubtitleError(f"字幕文件不存在: {srt_path}")
        
        # 解析SRT文件
        subtitles = self._parse_srt(srt_path)
        
        # 渲染字幕
        return self.render_subtitles(video_path, subtitles, output_path, **kwargs)
    
    def _parse_srt(self, srt_path: str) -> List[Dict[str, Any]]:
        """解析SRT字幕文件
        
        Args:
            srt_path: SRT文件路径
            
        Returns:
            字幕列表
        """
        subtitles = []
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 分割字幕块
        blocks = content.split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # 解析时间轴
                time_line = lines[1]
                times = time_line.split(' --> ')
                if len(times) == 2:
                    start = self._parse_time(times[0])
                    end = self._parse_time(times[1])
                    text = '\n'.join(lines[2:])
                    
                    subtitles.append({
                        'start': start,
                        'end': end,
                        'text': text
                    })
        
        return subtitles
    
    def _parse_time(self, time_str: str) -> float:
        """解析SRT时间格式
        
        Args:
            time_str: 时间字符串(HH:MM:SS,mmm)
            
        Returns:
            秒数
        """
        time_str = time_str.strip().replace(',', '.')
        parts = time_str.split(':')
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, 'ffmpeg'):
                self.ffmpeg.cleanup()
        except Exception:
            pass  # 忽略清理错误
