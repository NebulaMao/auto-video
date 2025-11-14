#!/usr/bin/env python3
"""
检查ASS文件内容
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_ass_file():
    """检查最新的ASS文件内容"""
    print("=" * 80)
    print("检查ASS文件内容")
    print("=" * 80)

    # 查找最新的ASS文件
    import glob
    ass_files = glob.glob("data/output/final_video_*.ass")

    if not ass_files:
        print("没有找到ASS文件")
        return

    # 找到最新的文件
    latest_file = max(ass_files, key=lambda x: Path(x).stat().st_mtime)
    print(f"检查文件: {latest_file}")

    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"\n文件内容:")
        print(content)

        # 分析样式
        print(f"\n样式分析:")
        lines = content.split('\n')
        for line in lines:
            if line.startswith('Style:'):
                print(f"样式: {line}")
                parts = line.split(',')
                if len(parts) >= 18:
                    alignment = parts[17]  # Alignment是第18个字段（从0开始计数）
                    font_size = parts[2]
                    margin_v = parts[16]
                    print(f"  - 字体大小: {font_size}")
                    print(f"  - 对齐方式: {alignment}")
                    print(f"  - 底部边距: {margin_v}")

        # 分析对话
        print(f"\n对话分析:")
        dialogue_lines = [line for line in lines if line.startswith('Dialogue:')]
        print(f"对话条数: {len(dialogue_lines)}")

        for i, dialogue in enumerate(dialogue_lines[:5]):  # 只显示前5条
            parts = dialogue.split(',')
            if len(parts) >= 10:
                text = ','.join(parts[9:])
                print(f"\n对话 {i+1}:")
                print(f"  文本: {text}")

                if '\\N' in text:
                    lines = text.split('\\N')
                    print(f"  分为 {len(lines)} 行:")
                    for j, line_text in enumerate(lines):
                        print(f"    行 {j+1}: {line_text}")

    except Exception as e:
        print(f"读取文件失败: {e}")

if __name__ == "__main__":
    check_ass_file()