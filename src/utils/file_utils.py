"""
文件操作工具模块

提供文件和目录操作的辅助函数。
"""

import os
import re
from pathlib import Path
from typing import List, Optional


def ensure_dir(directory: str) -> Path:
    """确保目录存在,如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        Path对象
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(file_path: str, unit: str = 'MB') -> float:
    """获取文件大小
    
    Args:
        file_path: 文件路径
        unit: 单位('B', 'KB', 'MB', 'GB')
        
    Returns:
        文件大小
    """
    if not Path(file_path).exists():
        return 0.0
    
    size_bytes = Path(file_path).stat().st_size
    
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3
    }
    
    divisor = units.get(unit.upper(), 1)
    return size_bytes / divisor


def get_file_extension(file_path: str, with_dot: bool = True) -> str:
    """获取文件扩展名
    
    Args:
        file_path: 文件路径
        with_dot: 是否包含点号
        
    Returns:
        文件扩展名
    """
    ext = Path(file_path).suffix
    if not with_dot and ext.startswith('.'):
        ext = ext[1:]
    return ext.lower()


def clean_filename(filename: str, replace_char: str = '_') -> str:
    """清理文件名,移除非法字符
    
    Args:
        filename: 原始文件名
        replace_char: 替换字符
        
    Returns:
        清理后的文件名
    """
    # Windows文件名非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(illegal_chars, replace_char, filename)
    
    # 移除首尾空格和点号
    cleaned = cleaned.strip('. ')
    
    return cleaned


def list_files_by_extension(
    directory: str,
    extensions: List[str],
    recursive: bool = False
) -> List[Path]:
    """列出指定扩展名的文件
    
    Args:
        directory: 目录路径
        extensions: 扩展名列表(如['.mp4', '.avi'])
        recursive: 是否递归搜索
        
    Returns:
        文件路径列表
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    
    # 标准化扩展名
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                  for ext in extensions]
    
    files = []
    
    if recursive:
        for ext in extensions:
            files.extend(dir_path.rglob(f'*{ext}'))
    else:
        for ext in extensions:
            files.extend(dir_path.glob(f'*{ext}'))
    
    return sorted(files)


def get_relative_path(file_path: str, base_path: str) -> str:
    """获取相对路径
    
    Args:
        file_path: 文件路径
        base_path: 基础路径
        
    Returns:
        相对路径
    """
    return str(Path(file_path).relative_to(Path(base_path)))


def copy_file(src: str, dst: str, overwrite: bool = False) -> bool:
    """复制文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
        overwrite: 是否覆盖已存在的文件
        
    Returns:
        是否成功
    """
    import shutil
    
    src_path = Path(src)
    dst_path = Path(dst)
    
    if not src_path.exists():
        return False
    
    if dst_path.exists() and not overwrite:
        return False
    
    # 确保目标目录存在
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(src, dst)
    return True


def delete_file(file_path: str, safe: bool = True) -> bool:
    """删除文件
    
    Args:
        file_path: 文件路径
        safe: 安全模式(仅删除存在的文件)
        
    Returns:
        是否成功
    """
    path = Path(file_path)
    
    if safe and not path.exists():
        return False
    
    try:
        path.unlink()
        return True
    except Exception:
        return False


def get_temp_filename(prefix: str = 'temp', suffix: str = '', directory: str = None) -> str:
    """生成临时文件名
    
    Args:
        prefix: 文件名前缀
        suffix: 文件名后缀(扩展名)
        directory: 临时文件目录
        
    Returns:
        临时文件路径
    """
    import tempfile
    
    if directory:
        ensure_dir(directory)
        temp_dir = directory
    else:
        temp_dir = tempfile.gettempdir()
    
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=temp_dir)
    os.close(fd)
    
    return path


def read_text_file(file_path: str, encoding: str = 'utf-8') -> str:
    """读取文本文件
    
    Args:
        file_path: 文件路径
        encoding: 编码格式
        
    Returns:
        文件内容
    """
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


def write_text_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """写入文本文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 编码格式
        
    Returns:
        是否成功
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception:
        return False