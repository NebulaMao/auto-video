"""
Edge TTS服务状态检查工具

用于检测Edge TTS服务是否可用
"""
import edge_tts
import asyncio
import sys
from datetime import datetime


async def check_edge_tts_status():
    """检查Edge TTS服务状态"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查Edge TTS服务状态...")

    try:
        # 尝试合成一个短音频
        communicate = edge_tts.Communicate(
            text="测试",
            voice="zh-CN-XiaoxiaoNeural"
        )

        # 使用超时控制
        await asyncio.wait_for(
            communicate.save("data/temp/status_check.mp3"),
            timeout=10.0
        )

        print("[OK] Edge TTS服务正常")
        return True

    except asyncio.TimeoutError:
        print("[FAIL] Edge TTS服务超时")
        return False

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            print("[FAIL] Edge TTS服务认证失败（401错误）")
            print("  原因：微软服务端认证机制变更")
            print("  建议：稍后重试（通常几分钟到几小时后恢复）")
        else:
            print(f"[FAIL] Edge TTS服务错误: {error_msg}")
        return False


if __name__ == "__main__":
    result = asyncio.run(check_edge_tts_status())
    sys.exit(0 if result else 1)
