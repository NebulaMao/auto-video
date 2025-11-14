"""
LLM客户端模块

负责与DeepSeek API交互,生成视频脚本和场景描述。
"""

from typing import Any, Dict, List
import openai
from ..core.exceptions import LLMError
from ..core.logger import Logger


class LLMClient:
    """LLM客户端类
    
    封装DeepSeek API调用,提供脚本生成和内容分析功能。
    """
    
    def __init__(self, config: Dict[str, Any], logger: Logger = None):
        """初始化LLM客户端
        
        Args:
            config: LLM配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger
        
        # 配置OpenAI客户端(兼容DeepSeek API)
        self.client = openai.OpenAI(
            api_key=config.get('api_key'),
            base_url=config.get('base_url', 'https://api.deepseek.com')
        )
        
        self.model = config.get('model', 'deepseek-chat')
        self.max_tokens = config.get('max_tokens', 4000)
        self.temperature = config.get('temperature', 0.7)
        self.timeout = config.get('timeout', 30)
        
        if self.logger:
            self.logger.info(f"LLM客户端初始化完成,使用模型: {self.model}")
    
    def generate_script(self, prompt: str, duration_seconds: int = 60, **kwargs) -> str:
        """生成口播文案

        Args:
            prompt: 用户输入的视频描述
            duration_seconds: 视频时长（秒）
            **kwargs: 额外的生成参数

        Returns:
            生成的口播文案文本

        Raises:
            LLMError: API调用失败时抛出
        """
        try:
            if self.logger:
                self.logger.info(f"开始生成口播文案,输入长度: {len(prompt)}, 目标时长: {duration_seconds}秒")

            # 根据时长计算合适的字数（按照正常语速每分钟200-300字计算）
            target_words = int(duration_seconds * 4)  # 平均每秒4个字

            system_prompt = f"""你是一个专业的口播文案编写助手。
请根据用户的描述,生成一个适合口头播报的纯文本文案。

要求:
1. 语言通俗易懂,适合口语表达
2. 内容流畅自然,便于朗读
3. 结构清晰: 开场引入 → 主体内容 → 结尾总结
4. 控制字数在{target_words}字左右（误差±50字）
5. 使用短句和段落,便于呼吸和停顿
6. 避免复杂的书面语和专业术语
7. 可以适当使用设问、感叹等口语化表达

【重要】文案格式要求:
- 生成纯文本内容,使用XML颜色标记为重点字词着yellow色
- 使用<yellow></yellow>颜色标签
- 对于需要强调的内容,可以用词语重述或加粗提示
- 保持文案简洁易读,避免复杂格式
- 每段控制在20-40字,便于字幕分行显示

请直接输出纯文本文案内容,不要包含场景描述、画面指示等非口播内容。"""

            user_prompt = f"请为以下主题生成一个{duration_seconds}秒左右的口播文案:\n\n{prompt}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=kwargs.get('max_tokens', min(self.max_tokens, target_words * 3)),
                temperature=kwargs.get('temperature', self.temperature),
                timeout=self.timeout
            )

            script = response.choices[0].message.content

            if self.logger:
                actual_words = len(script.replace(' ', '').replace('\n', ''))
                self.logger.info(f"口播文案生成成功,输出长度: {len(script)}字符, {actual_words}字")

            return script

        except Exception as e:
            error_msg = f"LLM口播文案生成失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise LLMError(error_msg)
    
    def generate_scene_descriptions(self, script: str, duration_seconds: int = 60) -> List[Dict[str, Any]]:
        """从口播文案中提取场景描述

        Args:
            script: 口播文案文本
            duration_seconds: 视频时长（秒）

        Returns:
            场景描述列表,每个场景包含画面描述和口播内容

        Raises:
            LLMError: 场景提取失败时抛出
        """
        try:
            if self.logger:
                self.logger.info("开始提取场景描述")

            # 计算场景数量（每15-20秒一个场景）
            scene_count = max(3, min(8, duration_seconds // 18))
            avg_duration = duration_seconds // scene_count

            system_prompt = f"""请分析以下口播文案,将其分割为{scene_count}个场景。
对每个场景,请提供:
1. scene_id: 场景编号(从1开始)
2. visual_description: 适合该段口播内容的画面描述(用于随机素材匹配,不需要太具体)
3. narration: 该段的口播文本内容
4. duration_estimate: 该场景的预估时长(秒)

要求:
- 场景分割要自然,符合口播节奏
- 每个场景的口播内容要相对完整
- 画面描述简洁明了,便于素材匹配
- 确保所有场景的总时长接近{duration_seconds}秒

请以JSON数组格式返回,格式如下:
[
  {{
    "scene_id": 1,
    "visual_description": "适合的开场画面描述",
    "narration": "第一段的口播内容",
    "duration_estimate": {avg_duration}
  }},
  ...
]"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"口播文案内容:\n{script}"}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,
                timeout=self.timeout
            )

            # 解析JSON响应
            import json
            content = response.choices[0].message.content

            try:
                # 尝试直接解析JSON
                scenes = json.loads(content)
                if isinstance(scenes, list):
                    if self.logger:
                        self.logger.info(f"场景提取完成,共{len(scenes)}个场景")
                    return scenes
            except json.JSONDecodeError:
                # 如果JSON解析失败,返回空列表,使用简单分割
                if self.logger:
                    self.logger.warning("JSON解析失败,将使用简单场景分割")
                return []

        except Exception as e:
            error_msg = f"场景描述提取失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise LLMError(error_msg)
    
    def extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
            
        Raises:
            LLMError: 关键词提取失败时抛出
        """
        try:
            if self.logger:
                self.logger.info("开始提取关键词")
            
            system_prompt = "请从以下文本中提取5-10个最重要的关键词,用逗号分隔。"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=200,
                temperature=0.3,
                timeout=self.timeout
            )
            
            keywords_str = response.choices[0].message.content
            keywords = [kw.strip() for kw in keywords_str.split(',')]
            
            if self.logger:
                self.logger.info(f"关键词提取完成: {keywords}")
            
            return keywords
            
        except Exception as e:
            error_msg = f"关键词提取失败: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise LLMError(error_msg)