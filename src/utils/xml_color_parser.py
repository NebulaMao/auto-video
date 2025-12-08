#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XML颜色标记解析器
支持解析字幕文本中的XML颜色标记，如 <yellow>文本</yellow>
提供文本清理和颜色分段功能

作者: AutoVideo项目
创建时间: 2025
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ColorSegment:
    """颜色分段数据结构"""
    text: str
    color: str = "default"  # default, yellow, red, blue, green, purple
    start_pos: int = 0
    end_pos: int = 0


class XMLColorParser:
    """XML颜色标记解析器"""

    # 支持的颜色映射（ASS格式颜色代码）
    COLOR_MAP = {
        "default": "",  # 使用默认颜色
        "yellow": r"{\c&H00FFFF&}",  # 黄色 (BGR格式)
        "red": r"{\c&H0000FF&}",     # 红色
        "blue": r"{\c&HFF0000&}",    # 蓝色
        "green": r"{\c&H00FF00&}",   # 绿色
        "purple": r"{\c&HFF00FF&}",  # 紫色
        "orange": r"{\c&H0080FF&}",  # 橙色
        "pink": r"{\c&HFFC0CB&}",    # 粉色
    }

    # 简化的颜色名称映射
    SIMPLE_COLOR_MAP = {
        "yellow": "yellow",
        "red": "red",
        "blue": "blue",
        "green": "green",
        "purple": "purple",
        "orange": "orange",
        "pink": "pink",
        "金色": "yellow",
        "黄色": "yellow",
        "红色": "red",
        "蓝色": "blue",
        "绿色": "green",
        "紫色": "purple",
        "橙色": "orange",
        "粉色": "pink",
    }

    def __init__(self):
        """初始化解析器"""
        # 编译正则表达式以提高性能
        self.tag_pattern = re.compile(r'<([^>]+)>(.*?)</\1>', re.DOTALL)
        self.all_tags_pattern = re.compile(r'<[^>]+>', re.DOTALL)

    def parse_text(self, text: str) -> Tuple[List[ColorSegment], str]:
        """
        解析包含XML颜色标记的文本

        Args:
            text: 输入文本，可能包含XML颜色标记

        Returns:
            Tuple: (颜色分段列表, 清理后的纯文本)

        Examples:
            >>> parser = XMLColorParser()
            >>> segments, clean_text = parser.parse_text("你好<yellow>世界</yellow>!")
            >>> len(segments)
            3
            >>> clean_text
            "你好世界!"
        """
        if not text or not isinstance(text, str):
            return [ColorSegment(text=text or "", start_pos=0, end_pos=len(text or ""))], text or ""

        # 检查是否包含XML标记
        if not self._has_xml_tags(text):
            return [ColorSegment(text=text, start_pos=0, end_pos=len(text))], text

        try:
            # 首先尝试使用正则表达式解析
            segments = self._parse_with_regex(text)
            if segments:
                clean_text = self._extract_clean_text(text)
                return segments, clean_text
        except Exception as e:
            # 如果正则解析失败，尝试XML解析
            try:
                segments = self._parse_with_xml(text)
                if segments:
                    clean_text = self._extract_clean_text(text)
                    return segments, clean_text
            except Exception:
                pass

        # 如果都失败，返回原文本
        return [ColorSegment(text=text, start_pos=0, end_pos=len(text))], self._extract_clean_text(text)

    def _has_xml_tags(self, text: str) -> bool:
        """检查文本是否包含XML标记"""
        return bool(self.tag_pattern.search(text))

    def _parse_with_regex(self, text: str) -> List[ColorSegment]:
        """使用正则表达式解析XML标记"""
        segments = []
        last_end = 0

        # 查找所有匹配的标记
        for match in self.tag_pattern.finditer(text):
            tag_name = match.group(1).lower()
            tag_content = match.group(2)
            tag_start = match.start()
            tag_end = match.end()

            # 检查标签名是否为有效颜色
            color = self._get_color_from_tag(tag_name)
            if color:
                # 添加标记前的文本
                if tag_start > last_end:
                    pre_text = text[last_end:tag_start]
                    # 清理前导和尾随空白
                    pre_text = re.sub(r'\s+', ' ', pre_text.strip())
                    if pre_text:
                        segments.append(ColorSegment(
                            text=pre_text,
                            color="default",
                            start_pos=last_end,
                            end_pos=tag_start
                        ))

                # 清理标签内容的空白
                tag_content = re.sub(r'\s+', ' ', tag_content.strip())

                # 添加带颜色的文本
                segments.append(ColorSegment(
                    text=tag_content,
                    color=color,
                    start_pos=tag_start,
                    end_pos=tag_end
                ))

                last_end = tag_end

        # 添加剩余文本
        if last_end < len(text):
            remaining_text = text[last_end:]
            # 清理剩余文本的空白
            remaining_text = re.sub(r'\s+', ' ', remaining_text.strip())
            if remaining_text:
                segments.append(ColorSegment(
                    text=remaining_text,
                    color="default",
                    start_pos=last_end,
                    end_pos=len(text)
                ))

        return segments if segments else [ColorSegment(text=text, start_pos=0, end_pos=len(text))]

    def _parse_with_xml(self, text: str) -> List[ColorSegment]:
        """使用XML解析器处理更复杂的XML结构"""
        try:
            # 包装在根元素中以创建有效的XML
            wrapped_text = f"<root>{text}</root>"
            root = ET.fromstring(wrapped_text)

            segments = []
            self._parse_xml_element(root, segments, "")
            return segments
        except ET.ParseError:
            return []

    def _parse_xml_element(self, element: ET.Element, segments: List[ColorSegment], current_color: str):
        """递归解析XML元素"""
        for child in element:
            if child.text:
                color = self._get_color_from_tag(child.tag.lower()) or current_color
                segments.append(ColorSegment(
                    text=child.text,
                    color=color or "default"
                ))

            # 处理子元素
            self._parse_xml_element(child, segments, current_color)

            # 处理尾部文本
            if child.tail:
                segments.append(ColorSegment(
                    text=child.tail,
                    color=current_color or "default"
                ))

    def _get_color_from_tag(self, tag_name: str) -> Optional[str]:
        """从标签名获取颜色"""
        return self.SIMPLE_COLOR_MAP.get(tag_name.lower())

    def _extract_clean_text(self, text: str) -> str:
        """提取不含XML标记的纯文本"""
        # 先清理XML标签周围的多余空白和换行
        text = re.sub(r'\s*<([^>]+)>\s*', r'<\1>', text)  # 开标签周围的空白
        text = re.sub(r'\s*</([^>]+)>\s*', r'</\1>', text)  # 闭标签周围的空白

        # 移除所有XML标记
        clean_text = self.all_tags_pattern.sub("", text)

        # 清理XML标签移除后可能产生的多余空白
        clean_text = re.sub(r'\s+', ' ', clean_text)  # 多个空白字符合并为一个空格

        # 移除可能出现在行首行尾的空格
        clean_text = clean_text.strip()

        return clean_text

    def to_ass_format(self, segments: List[ColorSegment]) -> str:
        """
        将颜色分段转换为ASS格式字符串

        Args:
            segments: 颜色分段列表

        Returns:
            ASS格式字符串
        """
        ass_text = ""

        for segment in segments:
            if segment.color == "default" or not segment.color:
                # 默认颜色，不添加颜色代码
                ass_text += segment.text
            else:
                # 获取颜色代码
                color_code = self.COLOR_MAP.get(segment.color, "")
                if color_code:
                    # 添加颜色代码、文本和颜色重置
                    ass_text += f"{color_code}{segment.text}" + r"{\c}"
                else:
                    ass_text += segment.text

        return ass_text

    def get_supported_colors(self) -> List[str]:
        """获取支持的颜色列表"""
        return list(self.COLOR_MAP.keys())

    def validate_color_tag(self, tag_name: str) -> bool:
        """验证颜色标签是否有效"""
        return tag_name.lower() in self.SIMPLE_COLOR_MAP


def parse_xml_color_text(text: str) -> Tuple[List[ColorSegment], str]:
    """
    便捷函数：解析XML颜色文本

    Args:
        text: 输入文本

    Returns:
        (颜色分段列表, 清理后的文本)
    """
    parser = XMLColorParser()
    return parser.parse_text(text)


def clean_xml_tags(text: str) -> str:
    """
    便捷函数：清理文本中的XML标记

    Args:
        text: 包含XML标记的文本

    Returns:
        清理后的纯文本
    """
    parser = XMLColorParser()
    return parser._extract_clean_text(text)


def text_to_ass_format(text: str) -> str:
    """
    便捷函数：将带XML颜色的文本转换为ASS格式

    Args:
        text: 输入文本

    Returns:
        ASS格式字符串
    """
    parser = XMLColorParser()
    segments, _ = parser.parse_text(text)
    return parser.to_ass_format(segments)


# 测试函数
def test_xml_parser():
    """测试XML解析器功能"""
    parser = XMLColorParser()

    test_cases = [
        "大家好！今天我要介绍<yellow>这款优秀的产品</yellow>，它真的很棒。",
        "<red>重要提醒</red>：请记得<blue>按时完成任务</blue>！",
        "普通文本没有任何标记",
        "混合<yellow>黄色</yellow>和<red>红色</red>的文本",
        "开始<yellow>中间</yellow>结束",
        "<invalid>无效颜色</invalid>的测试",
        "",  # 空文本
        "<yellow>只有标记</yellow>",
    ]

    sys.stdout.write("=== XML颜色解析器测试 ===\n")

    for i, test_text in enumerate(test_cases, 1):
        sys.stdout.write(f"测试用例 {i}: {test_text}\n")

        try:
            segments, clean_text = parser.parse_text(test_text)
            ass_format = parser.to_ass_format(segments)

            sys.stdout.write(f"  清理文本: {clean_text}\n")
            sys.stdout.write(f"  分段数量: {len(segments)}\n")

            for j, seg in enumerate(segments):
                sys.stdout.write(f"    分段{j+1}: [{seg.color}] '{seg.text}'\n")

            sys.stdout.write(f"  ASS格式: {ass_format}\n\n")

        except Exception as e:
            sys.stderr.write(f"  错误: {e}\n\n")


if __name__ == "__main__":
    test_xml_parser()