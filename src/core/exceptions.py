"""
自定义异常类模块

定义系统中使用的各种异常类型。
"""


class AutoVideoException(Exception):
    """AutoVideo系统基础异常类
    
    所有自定义异常的基类。
    """
    
    def __init__(self, message: str, error_code: str = None):
        """初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误码
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """返回异常的字符串表示"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigError(AutoVideoException):
    """配置错误异常
    
    当配置文件加载或验证失败时抛出。
    """
    pass


class LLMError(AutoVideoException):
    """LLM服务错误异常
    
    当LLM API调用失败或响应异常时抛出。
    """
    pass


class TTSError(AutoVideoException):
    """TTS服务错误异常
    
    当TTS语音合成失败时抛出。
    """
    pass


class VideoProcessingError(AutoVideoException):
    """视频处理错误异常
    
    当视频编辑、渲染或导出失败时抛出。
    """
    pass


class MaterialNotFoundError(AutoVideoException):
    """素材未找到异常
    
    当无法找到合适的素材时抛出。
    """
    pass


class SubtitleError(AutoVideoException):
    """字幕处理错误异常
    
    当字幕生成或渲染失败时抛出。
    """
    pass


class ValidationError(AutoVideoException):
    """数据验证错误异常
    
    当输入数据验证失败时抛出。
    """
    pass


class FileOperationError(AutoVideoException):
    """文件操作错误异常
    
    当文件读写操作失败时抛出。
    """
    pass
