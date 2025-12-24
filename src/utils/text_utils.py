"""
文本处理工具模块

提供文本清理、分割和处理的辅助函数。
新增XML颜色标记清理功能，支持字幕颜色标记处理。
"""

import re
import logging
from typing import List, Optional, Tuple, Dict


def clean_text(text: str, remove_extra_spaces: bool = True) -> str:
    """清理文本

    Args:
        text: 原始文本
        remove_extra_spaces: 是否移除多余空格

    Returns:
        清理后的文本
    """
    if not text:
        return ""

    # 移除控制字符（保留换行符）
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 移除多余空格
    if remove_extra_spaces:
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n +', '\n', text)
        text = re.sub(r' +\n', '\n', text)

    # 移除多余换行（更严格的清理）
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 移除标点符号前后的换行（防止字幕中出现不必要的换行）
    text = re.sub(r'\n+([。！？；：，、])', r'\1', text)  # 中文标点前
    text = re.sub(r'([。！？；：，、])\n+', r'\1', text)  # 中文标点后
    text = re.sub(r'\n+([.!?;:,])', r'\1', text)     # 英文标点前
    text = re.sub(r'([.!?;:,])\n+', r'\1', text)     # 英文标点后

    # 移除括号前后的换行
    text = re.sub(r'\n+(\()', r'\1', text)
    text = re.sub(r'(\))\n+', r'\1', text)
    text = re.sub(r'\n+(\[)', r'\1', text)
    text = re.sub(r'(\])\n+', r'\1', text)

    # 移除XML标签前后的换行
    text = re.sub(r'\n+(<[^>]+>)', r'\1', text)
    text = re.sub(r'(<[^>]+>)\n+', r'\1', text)

    # 移除开头和结尾的换行
    text = text.strip()

    # 最后检查：如果还有连续换行，减少到最多一个
    text = re.sub(r'\n{2,}', ' ', text)  # 将多余的换行转换为空格

    return text.strip()


def clean_xml_tags(text: str) -> str:
    """清理文本中的XML标记

    用于TTS处理前移除颜色标记等XML标签，确保语音合成不会读出标记。

    Args:
        text: 包含XML标记的文本（如：你好<yellow>世界</yellow>！）

    Returns:
        清理后的纯文本（如：你好世界！）

    Examples:
        >>> clean_xml_tags("你好<yellow>世界</yellow>！")
        "你好世界！"
        >>> clean_xml_tags("重要<red>提醒</red>：请<blue>注意</blue>")
        "重要提醒：请注意"
    """
    if not text:
        return ""

    # 先清理XML标签周围的多余空白和换行
    text = re.sub(r'\s*<([^>]+)>\s*', r'<\1>', text)  # 标签周围的空白
    text = re.sub(r'\s*</([^>]+)>\s*', r'</\1>', text)  # 闭标签周围的空白

    # 移除所有XML样式的标记
    xml_pattern = r'</?[^>]+>'
    clean_text = re.sub(xml_pattern, '', text)

    # 清理XML标签移除后可能产生的多余空白
    clean_text = re.sub(r'\s+', ' ', clean_text)  # 多个空白字符合并为一个空格

    # 移除可能出现在行首行尾的空格
    clean_text = clean_text.strip()

    return clean_text


def parse_color_segments(text: str) -> List[Dict[str, str]]:
    """解析文本中的颜色分段

    将包含XML颜色标记的文本解析为颜色分段列表，用于字幕渲染。

    Args:
        text: 包含XML颜色标记的文本

    Returns:
        颜色分段列表，每个分段包含text和color字段

    Examples:
        >>> parse_color_segments("你好<yellow>世界</yellow>！")
        [
            {"text": "你好", "color": "default"},
            {"text": "世界", "color": "yellow"},
            {"text": "！", "color": "default"}
        ]
    """
    if not text:
        return []

    # 使用专门的XML颜色解析器
    try:
        from .xml_color_parser import parse_xml_color_text
        segments, _ = parse_xml_color_text(text)

        # 转换为字典格式
        result = []
        for seg in segments:
            result.append({
                "text": seg.text,
                "color": seg.color
            })
        return result
    except ImportError:
        # 如果XML解析器不可用，返回默认分段
        return [{"text": clean_xml_tags(text), "color": "default"}]


def has_xml_color_tags(text: str) -> bool:
    """检查文本是否包含XML颜色标记

    Args:
        text: 输入文本

    Returns:
        是否包含XML颜色标记

    Examples:
        >>> has_xml_color_tags("你好<yellow>世界</yellow>！")
        True
        >>> has_xml_color_tags("普通文本没有标记")
        False
    """
    if not text:
        return False

    # 检查是否包含常见的颜色标记
    color_tags_pattern = r'<(?:yellow|red|blue|green|purple|orange|pink|金色|黄色|红色|蓝色|绿色|紫色|橙色|粉色)>'
    return bool(re.search(color_tags_pattern, text, re.IGNORECASE))


def clean_xml_preserving_tags(text: str) -> str:
    """清理包含XML标记的文本，但保留标记本身

    专门用于处理包含颜色标记的文本，清理多余的换行和空白，
    但保留XML颜色标记不被破坏。

    Args:
        text: 包含XML标记的文本

    Returns:
        清理后仍保留XML标记的文本

    Examples:
        >>> clean_xml_preserving_tags("你好<yellow>世界</yellow>！\n\n")
        "你好<yellow>世界</yellow>！"
    """
    if not text:
        return ""

    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 清理XML标记内的多余空白（但保留标记结构）
    # 移除开标签前的换行
    text = re.sub(r'\n+(<[^/>]+>)', r'\1', text)
    # 移除闭标签后的换行
    text = re.sub(r'(</[^>]+>)\n+', r'\1', text)

    # 清理文本内容中的多余换行和空格（在标记之外）
    # 将多个连续换行替换为单个空格
    text = re.sub(r'\n{2,}', ' ', text)
    # 将多个连续空格合并为单个空格
    text = re.sub(r' +', ' ', text)

    # 移除开头和结尾的空白
    text = text.strip()

    return text


def extract_plain_text(text: str) -> str:
    """提取纯文本（移除所有标记和特殊字符）

    综合清理函数，移除XML标记、多余空格和特殊字符。

    Args:
        text: 输入文本

    Returns:
        清理后的纯文本

    Examples:
        >>> extract_plain_text("你好<yellow>世界</yellow>！  ")
        "你好世界！"
    """
    # 首先清理XML标记
    text = clean_xml_tags(text)

    # 然后应用标准文本清理
    text = clean_text(text, remove_extra_spaces=True)

    return text


def split_text_by_sentences(text: str, language: str = 'zh') -> List[str]:
    """按句子分割文本
    
    Args:
        text: 输入文本
        language: 语言('zh'中文, 'en'英文)
        
    Returns:
        句子列表
    """
    if not text:
        return []
    
    if language == 'zh':
        # 中文句子分割
        pattern = r'[。！？\!?;；]+'
    else:
        # 英文句子分割
        pattern = r'[.!?;]+'
    
    sentences = re.split(pattern, text)
    
    # 过滤空句子并清理
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


def split_text_by_length(
    text: str,
    max_length: int,
    split_by_sentence: bool = True,
    overlap: int = 0
) -> List[str]:
    """按长度分割文本
    
    Args:
        text: 输入文本
        max_length: 最大长度
        split_by_sentence: 是否按句子分割(尽量不破坏句子)
        overlap: 重叠字符数
        
    Returns:
        文本片段列表
    """
    if not text:
        return []
    
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    
    if split_by_sentence:
        sentences = split_text_by_sentences(text)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
    else:
        start = 0
        while start < len(text):
            end = start + max_length
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
    
    return chunks


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """截断文本
    
    Args:
        text: 输入文本
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def word_count(text: str, language: str = 'zh') -> int:
    """统计字数
    
    Args:
        text: 输入文本
        language: 语言('zh'中文, 'en'英文)
        
    Returns:
        字数
    """
    if not text:
        return 0
    
    if language == 'zh':
        # 中文字符统计
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        return len(chinese_chars)
    else:
        # 英文单词统计
        words = re.findall(r'\b\w+\b', text)
        return len(words)


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """提取关键词(简单实现)
    
    Args:
        text: 输入文本
        top_n: 返回前N个关键词
        
    Returns:
        关键词列表
    """
    if not text:
        return []
    
    # 简单的词频统计
    words = re.findall(r'[\u4e00-\u9fff]+', text)
    
    # 过滤停用词(简化)
    stopwords = {'的', '了', '在', '是', '和', '有', '我', '你', '他', '她', '它'}
    words = [w for w in words if w not in stopwords and len(w) > 1]
    
    # 统计词频
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # 排序并返回前N个
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:top_n]]


def remove_punctuation(text: str, language: str = 'zh') -> str:
    """移除标点符号
    
    Args:
        text: 输入文本
        language: 语言('zh'中文, 'en'英文)
        
    Returns:
        移除标点后的文本
    """
    if not text:
        return ""
    
    if language == 'zh':
        # 中文标点
        pattern = r'[，。！？；：""''（）《》【】、]'
    else:
        # 英文标点
        pattern = r'[,\.!?;:\'"()\[\]{}]'
    
    return re.sub(pattern, '', text)


def normalize_whitespace(text: str) -> str:
    """标准化空白字符
    
    Args:
        text: 输入文本
        
    Returns:
        标准化后的文本
    """
    if not text:
        return ""
    
    # 将所有空白字符统一为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def contains_chinese(text: str) -> bool:
    """检查文本是否包含中文
    
    Args:
        text: 输入文本
        
    Returns:
        是否包含中文
    """
    if not text:
        return False
    
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def remove_urls(text: str) -> str:
    """移除URL链接
    
    Args:
        text: 输入文本
        
    Returns:
        移除URL后的文本
    """
    if not text:
        return ""
    
    # 匹配URL模式
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    
    return re.sub(url_pattern, '', text)


def format_time(seconds: float) -> str:
    """格式化时间
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串(HH:MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def parse_time(time_str: str) -> float:
    """解析时间字符串
    
    Args:
        time_str: 时间字符串(HH:MM:SS或MM:SS)
        
    Returns:
        秒数
    """
    parts = time_str.split(':')
    
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(parts[0])
    
    
def split_text_by_punctuation(
    text: str,
    language: str = 'zh',
    min_length: int = 10,
    max_length: int = 100,
    include_comma: bool = False
) -> List[str]:
    """按标点符号分割文本
    
    Args:
        text: 输入文本
        language: 语言('zh'中文, 'en'英文)
        min_length: 最小段落长度(字符)
        max_length: 最大段落长度(字符)
        include_comma: 是否将逗号也视为分段标点
        
    Returns:
        按标点符号分割的文本段落列表
    """
    # 添加调试日志
    logging.debug(f"split_text_by_punctuation: 输入文本长度={len(text)}")
    logging.debug(f"split_text_by_punctuation: 输入文本前100字符={text[:100]}")
    
    if not text:
        logging.debug("split_text_by_punctuation: 输入文本为空，返回空列表")
        return []
    
    # 清理文本
    original_text = text
    text = clean_text(text)
    logging.debug(f"split_text_by_punctuation: 清理后文本长度={len(text)}")
    if len(text) != len(original_text):
        logging.debug(f"split_text_by_punctuation: 文本被清理，清理前后长度差={len(original_text)-len(text)}")
    
    if language == 'zh':
        # 中文标点符号（使用捕获组保留标点）
        if include_comma:
            punctuation_pattern = r'([。！？；：，])'
        else:
            punctuation_pattern = r'([。！？；：])'
    else:
        # 英文标点符号（使用捕获组保留标点）
        if include_comma:
            punctuation_pattern = r'([.!?;:,])'
        else:
            punctuation_pattern = r'([.!?;:])'

    logging.debug(f"split_text_by_punctuation: 使用标点符号模式={punctuation_pattern}")

    # 按标点符号分割（保留标点符号）
    parts = re.split(punctuation_pattern, text)
    logging.debug(f"split_text_by_punctuation: 初始分割得到{len(parts)}个部分（含标点）")

    # 重组：将文本片段与标点符号组合
    segments = []
    for i in range(0, len(parts) - 1, 2):
        if i + 1 < len(parts):
            # 组合文本和标点：text + punctuation
            segment = parts[i].strip() + parts[i + 1]
            if segment.strip():
                segments.append(segment)

    # 处理最后一个部分（如果没有标点结尾）
    if len(parts) % 2 == 1 and parts[-1].strip():
        segments.append(parts[-1].strip())

    logging.debug(f"split_text_by_punctuation: 重组后得到{len(segments)}个段落（含标点）")
    logging.debug(f"split_text_by_punctuation: 过滤空段落后剩余{len(segments)}个段落")
    
    # 打印每个段落的详细信息
    for i, seg in enumerate(segments):
        logging.debug(f"split_text_by_punctuation: 段落{i+1} 长度={len(seg)} 内容={seg[:50]}...")
    
    # 处理过长的段落
    processed_segments = []
    for segment in segments:
        if len(segment) <= max_length:
            processed_segments.append(segment)
        else:
            logging.debug(f"split_text_by_punctuation: 段落过长({len(segment)}字符)，进行进一步分割")
            # 如果段落过长，按句子进一步分割
            sentences = split_text_by_sentences(segment, language)
            logging.debug(f"split_text_by_punctuation: 分割为{len(sentences)}个句子")
            current_chunk = ""
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) <= max_length:
                    current_chunk += sentence
                else:
                    if current_chunk:
                        processed_segments.append(current_chunk.strip())
                        logging.debug(f"split_text_by_punctuation: 添加段落块，长度={len(current_chunk.strip())}")
                    current_chunk = sentence
            
            if current_chunk:
                processed_segments.append(current_chunk.strip())
                logging.debug(f"split_text_by_punctuation: 添加最后段落块，长度={len(current_chunk.strip())}")
    
    # 智能处理短段落，避免文本丢失
    final_segments = []
    short_segments = []
    
    # 首先分离长段落和短段落
    for seg in processed_segments:
        if len(seg) >= min_length:
            final_segments.append(seg)
        else:
            short_segments.append(seg)
    
    logging.debug(f"split_text_by_punctuation: 长段落={len(final_segments)}个，短段落={len(short_segments)}个")
    
    # 如果有短段落，尝试智能合并
    if short_segments:
        logging.debug(f"split_text_by_punctuation: 发现短段落，尝试智能合并以避免文本丢失")
        
        # 重新构建包含所有段落的列表
        all_segments = processed_segments.copy()
        merged_segments = []
        i = 0
        
        while i < len(all_segments):
            current_seg = all_segments[i]
            
            if len(current_seg) >= min_length:
                # 长段落直接保留
                merged_segments.append(current_seg)
                i += 1
            else:
                # 短段落需要处理
                if i == 0 and len(all_segments) > 1:
                    # 第一个短段落，合并到下一个段落
                    merged_seg = current_seg + all_segments[i+1]
                    merged_segments.append(merged_seg)
                    logging.debug(f"split_text_by_punctuation: 将第一个短段落合并到下一个段落")
                    i += 2  # 跳过下一个段落，因为已经合并了
                elif i == len(all_segments) - 1 and len(merged_segments) > 0:
                    # 最后一个短段落，合并到前一个段落
                    merged_segments[-1] += current_seg
                    logging.debug(f"split_text_by_punctuation: 将最后一个短段落合并到前一个段落")
                    i += 1
                else:
                    # 中间的短段落，优先合并到前一个段落
                    if len(merged_segments) > 0:
                        merged_segments[-1] += current_seg
                        logging.debug(f"split_text_by_punctuation: 将中间短段落合并到前一个段落")
                        i += 1
                    else:
                        # 异常情况，直接保留
                        merged_segments.append(current_seg)
                        logging.debug(f"split_text_by_punctuation: 异常情况，保留短段落")
                        i += 1
        
        final_segments = merged_segments
    
    logging.debug(f"split_text_by_punctuation: 最终段落数量={len(final_segments)}个")
    
    # 打印最终结果
    total_chars = sum(len(seg) for seg in final_segments)
    logging.debug(f"split_text_by_punctuation: 最终段落总字符数={total_chars}，原始文本字符数={len(text)}")
    
    # 检查文本完整性
    if total_chars < len(text) * 0.95:  # 如果总字符数明显少于原始文本
        lost_chars = len(text) - total_chars
        logging.debug(f"split_text_by_punctuation: 警告！可能存在文本丢失，丢失{lost_chars}个字符")
        
        # 如果丢失太多，回退到简单分段
        if lost_chars > 20:  # 丢失超过20个字符
            logging.debug(f"split_text_by_punctuation: 文本丢失过多，回退到简单分段模式")
            # 简单按标点分割，不过滤短段落
            simple_segments = re.split(r'[。！？；：]' if language == 'zh' else r'[.!?;:]', text)
            simple_segments = [s.strip() for s in simple_segments if s.strip()]
            return simple_segments
    else:
        logging.debug(f"split_text_by_punctuation: 文本完整性良好")
    
    return final_segments
