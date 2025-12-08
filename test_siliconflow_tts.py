#!/usr/bin/env python3
"""
SiliconFlow TTS 集成测试脚本

用于测试 SiliconFlow TTS 服务的集成是否正常工作。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import ConfigManager
from src.core.logger import Logger
from src.modules.siliconflow_tts import SiliconFlowTTS


def test_siliconflow_tts():
    """测试 SiliconFlow TTS 功能"""
    print("=" * 60)
    print("SiliconFlow TTS 集成测试")
    print("=" * 60)

    try:
        # 1. 加载配置
        print("\n1. 加载配置文件...")
        config_path = "config.toml"
        if not Path(config_path).exists():
            print(f"配置文件 {config_path} 不存在，请先创建配置文件")
            print("可以参考 config.toml.siliconflow_example")
            return False

        config_manager = ConfigManager(config_path)
        tts_config = config_manager.get_section('tts')
        siliconflow_config = config_manager.get_section('siliconflow_tts')

        # 合并配置
        tts_config.update(siliconflow_config)

        print("✓ 配置文件加载成功")

        # 2. 检查 API Key
        print("\n2. 检查 API 配置...")
        api_key = tts_config.get('api_key', '')
        if not api_key or api_key == 'your-siliconflow-api-key-here':
            print("✗ 请在配置文件中设置有效的 SiliconFlow API Key")
            return False

        print("✓ API Key 配置正确")

        # 3. 初始化日志
        print("\n3. 初始化日志系统...")
        log_config = config_manager.get_section('logging')
        logger = Logger('SiliconFlowTTSTest', log_config)
        print("✓ 日志系统初始化成功")

        # 4. 初始化 SiliconFlow TTS
        print("\n4. 初始化 SiliconFlow TTS 引擎...")
        tts_engine = SiliconFlowTTS(tts_config, logger)
        print("✓ SiliconFlow TTS 引擎初始化成功")

        # 5. 测试 API 连接
        print("\n5. 测试 API 连接...")
        if tts_engine.test_connection():
            print("✓ API 连接测试成功")
        else:
            print("✗ API 连接测试失败")
            return False

        # 6. 获取可用模型和语音
        print("\n6. 获取可用模型和语音...")
        models = tts_engine.get_available_models()
        voices = tts_engine.get_available_voices()

        print(f"可用模型数量: {len(models)}")
        for model in models:
            print(f"  - {model['display_name']}: {model['description']}")

        print(f"可用语音数量: {len(voices)}")
        for voice in voices:
            print(f"  - {voice['display_name']} ({voice['gender']})")

        # 7. 测试语音合成
        print("\n7. 测试语音合成...")
        test_text = "这是 SiliconFlow TTS 的测试语音。"
        output_path = "test_output_siliconflow.mp3"

        try:
            result_path = tts_engine.synthesize(test_text, output_path)
            if Path(result_path).exists():
                print(f"✓ 语音合成成功: {result_path}")

                # 获取音频时长
                duration = tts_engine.get_audio_duration(result_path)
                print(f"  音频时长: {duration:.2f} 秒")

                # 清理测试文件
                Path(result_path).unlink()
                print("  测试文件已清理")
            else:
                print("✗ 语音合成失败: 未生成文件")
                return False

        except Exception as e:
            print(f"✗ 语音合成失败: {str(e)}")
            return False

        # 8. 测试分段合成
        print("\n8. 测试分段语音合成...")
        text_segments = [
            "这是第一段测试文本。",
            "这是第二段测试文本。",
            "这是第三段测试文本。"
        ]

        try:
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                segments_info = tts_engine.synthesize_segments(text_segments, temp_dir)

                print(f"✓ 分段合成成功，共 {len(segments_info)} 个段落")
                total_duration = sum(seg['duration'] for seg in segments_info)
                print(f"  总时长: {total_duration:.2f} 秒")

        except Exception as e:
            print(f"✗ 分段合成失败: {str(e)}")
            return False

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！SiliconFlow TTS 集成正常工作")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    success = test_siliconflow_tts()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()