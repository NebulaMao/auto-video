"""
AutoVideo - 自动化宣传视频生成工具
主入口文件

提供命令行接口和应用启动功能。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# 导入项目模块
from src.core.config import ConfigManager
from src.core.logger import Logger
from src.ui.gradio_app import GradioApp

# 版本信息
__version__ = "0.1.0"
__author__ = "nebulamao"
__description__ = "基于AI技术的自动化宣传视频生成工具"


def parse_args() -> argparse.Namespace:
    """解析命令行参数
    
    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        description=f"AutoVideo v{__version__} - {__description__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认配置启动
  python main.py
  
  # 指定配置文件
  python main.py --config my_config.toml
  
  # 自定义主机和端口
  python main.py --host 0.0.0.0 --port 8080
  
  # 启用调试模式
  python main.py --debug
  
  # 创建公共分享链接
  python main.py --share
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.toml",
        help="配置文件路径 (默认: config.toml)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Gradio服务器主机地址 (默认: 从配置文件读取)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Gradio服务器端口 (默认: 从配置文件读取)"
    )
    
    parser.add_argument(
        "--share",
        action="store_true",
        help="创建公共分享链接 (默认: False)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式 (默认: False)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"AutoVideo v{__version__}"
    )
    
    return parser.parse_args()


def create_directories(config: ConfigManager, logger: Logger) -> None:
    """创建必要的目录
    
    Args:
        config: 配置管理器
        logger: 日志记录器
    """
    # 获取路径配置
    paths = config.get_section('paths')
    
    # 需要创建的目录列表
    directories = [
        paths.get('materials_dir', './data/materials'),
        paths.get('output_dir', './data/output'),
        paths.get('temp_dir', './data/temp'),
        './data/materials/audio',
        './data/materials/images',
        './data/materials/videos',
        './logs'
    ]
    
    # 创建目录
    for dir_path in directories:
        path = Path(dir_path)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"创建目录: {path}")
            except Exception as e:
                logger.warning(f"创建目录失败 {path}: {e}")
        else:
            logger.debug(f"目录已存在: {path}")


def initialize_app(args: argparse.Namespace) -> tuple[ConfigManager, Logger, GradioApp]:
    """初始化应用组件
    
    Args:
        args: 命令行参数
        
    Returns:
        (配置管理器, 日志记录器, Gradio应用) 元组
        
    Raises:
        Exception: 初始化失败时抛出异常
    """
    # 1. 加载配置文件
    print(f"正在加载配置文件: {args.config}")
    try:
        config = ConfigManager(args.config)
        config.validate()
        print("[OK] 配置文件加载成功")
    except FileNotFoundError:
        print(f"[ERROR] 错误: 配置文件不存在: {args.config}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 错误: 配置文件加载失败: {e}")
        sys.exit(1)
    
    # 2. 初始化日志系统
    try:
        log_config = config.get_section('logging')
        
        # 如果启用调试模式,覆盖配置中的日志级别
        if args.debug:
            log_config['level'] = 'DEBUG'
        
        logger = Logger("autovideo", log_config)
        logger.info("=" * 60)
        logger.info(f"AutoVideo v{__version__} 启动中...")
        logger.info(f"作者: {__author__}")
        logger.info(f"配置文件: {Path(args.config).absolute()}")
        logger.info("=" * 60)
        
        if args.debug:
            logger.info("调试模式已启用")

        print("[OK] 日志系统初始化成功")
    except Exception as e:
        print(f"[ERROR] 错误: 日志系统初始化失败: {e}")
        sys.exit(1)
    
    # 3. 创建必要的目录
    try:
        logger.info("正在创建必要的目录...")
        create_directories(config, logger)
        logger.info("目录创建完成")
        print("[OK] 必要目录已创建")
    except Exception as e:
        logger.error(f"创建目录失败: {e}")
        print(f"[WARN] 警告: 部分目录创建失败: {e}")
    
    # 4. 初始化Gradio应用
    try:
        logger.info("正在初始化Gradio应用...")
        ui_config = config.get_section('ui')
        
        # 命令行参数覆盖配置文件
        if args.host is not None:
            ui_config['server_name'] = args.host
        if args.port is not None:
            ui_config['server_port'] = args.port
        if args.share:
            ui_config['share'] = True
        
        app = GradioApp(config, logger)
        logger.info("Gradio应用初始化成功")
        print("[OK] Gradio应用初始化成功")
    except Exception as e:
        logger.error(f"Gradio应用初始化失败: {e}")
        print(f"[ERROR] 错误: Gradio应用初始化失败: {e}")
        sys.exit(1)
    
    return config, logger, app


def main() -> int:
    """主函数
    
    Returns:
        退出码 (0表示成功, 非0表示失败)
    """
    # 解析命令行参数
    args = parse_args()
    
    print()
    print("=" * 60)
    print(f"  AutoVideo v{__version__}")
    print(f"  {__description__}")
    print("=" * 60)
    print()
    
    try:
        # 初始化应用组件
        config, logger, app = initialize_app(args)
        
        # 显示服务器信息
        server_name = config.get('ui', 'server_name', '127.0.0.1')
        server_port = config.get('ui', 'server_port', 7860)
        share = config.get('ui', 'share', False)
        
        print()
        print("=" * 60)
        print("  服务器信息")
        print("=" * 60)
        print(f"  本地地址: http://{server_name}:{server_port}")
        if share:
            print("  公共链接: 启动后显示")
        print("=" * 60)
        print()
        print("按 Ctrl+C 停止服务器")
        print()
        
        logger.info(f"启动Gradio服务器: {server_name}:{server_port}")
        if share:
            logger.info("公共分享链接已启用")
        
        # 启动Gradio应用
        app.launch()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n正在关闭服务器...")
        if 'logger' in locals():
            logger.info("收到中断信号,正在关闭...")
        return 0

    except Exception as e:
        print(f"\n[ERROR] 错误: 应用运行失败: {e}")
        if 'logger' in locals():
            logger.exception(f"应用运行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
