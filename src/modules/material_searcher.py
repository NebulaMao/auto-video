"""
智能素材检索模块

基于语义匹配检索素材库中的视频、图片和音频文件。
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
from sentence_transformers import SentenceTransformer
import numpy as np
from ..core.exceptions import MaterialNotFoundError
from ..core.logger import Logger


class MaterialSearcher:
    """智能素材检索器类
    
    使用语义匹配算法检索素材库中最相关的素材。
    """
    
    def __init__(self, config: Dict[str, Any], logger: Logger = None):
        """初始化素材检索器
        
        Args:
            config: 素材检索配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger
        
        self.materials_dir = Path(config.get('materials_dir', './data/materials'))
        self.similarity_threshold = config.get('semantic_similarity_threshold', 0.7)
        self.max_results = config.get('max_results', 10)
        self.supported_formats = config.get('supported_formats', ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts', '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'])
        
        # 加载语义匹配模型
        model_name = config.get('embedding_model', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        if self.logger:
            self.logger.info(f"加载语义匹配模型: {model_name}")
        
        self.model = SentenceTransformer(model_name)
        
        # 素材索引
        self.material_index = {}
        self.material_embeddings = None
        
        if self.logger:
            self.logger.info("素材检索器初始化完成")
    
    def build_index(self, materials_dir: str = None) -> None:
        """构建素材库索引
        
        Args:
            materials_dir: 素材目录路径
        """
        if materials_dir:
            self.materials_dir = Path(materials_dir)
        
        if not self.materials_dir.exists():
            if self.logger:
                self.logger.warning(f"素材目录不存在: {self.materials_dir}")
            self.materials_dir.mkdir(parents=True, exist_ok=True)
            return
        
        if self.logger:
            self.logger.info(f"开始构建素材索引: {self.materials_dir}")
        
        materials = []
        descriptions = []
        
        # 遍历素材目录
        for file_path in self.materials_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                # 获取素材信息
                material_info = self._extract_material_info(file_path)
                materials.append(material_info)
                descriptions.append(material_info['description'])
        
        if materials:
            # 生成嵌入向量
            self.material_embeddings = self.model.encode(descriptions)
            self.material_index = {i: material for i, material in enumerate(materials)}
            
            if self.logger:
                self.logger.info(f"素材索引构建完成,共 {len(materials)} 个素材")
        else:
            if self.logger:
                self.logger.warning("未找到任何素材文件")
    
    def _extract_material_info(self, file_path: Path) -> Dict[str, Any]:
        """提取素材元信息
        
        Args:
            file_path: 素材文件路径
            
        Returns:
            素材信息字典
        """
        # 从文件名提取描述(简化实现)
        filename = file_path.stem
        description = filename.replace('_', ' ').replace('-', ' ')
        
        # 使用FFmpegWrapper的格式检测方法
        from ..utils.ffmpeg_wrapper import FFmpegWrapper
        ffmpeg_wrapper = FFmpegWrapper()
        
        if ffmpeg_wrapper.is_video_file(file_path):
            material_type = 'video'
        elif ffmpeg_wrapper.is_image_file(file_path):
            material_type = 'image'
        else:
            material_type = 'unknown'
        
        return {
            'path': str(file_path),
            'filename': file_path.name,
            'type': material_type,
            'description': description,
            'extension': file_path.suffix.lower()
        }
    
    def search(self, query: str, material_type: str = None, top_k: int = None) -> List[Dict[str, Any]]:
        """搜索相关素材
        
        Args:
            query: 搜索查询文本
            material_type: 素材类型过滤('video', 'image', 'audio')
            top_k: 返回结果数量
            
        Returns:
            相关素材列表,按相似度降序排列
            
        Raises:
            MaterialNotFoundError: 未找到合适素材时抛出
        """
        if not self.material_index:
            if self.logger:
                self.logger.warning("素材索引为空,尝试构建索引")
            self.build_index()
        
        if not self.material_index:
            raise MaterialNotFoundError("素材库为空,无法进行检索")
        
        if self.logger:
            self.logger.info(f"搜索素材: {query}")
        
        # 生成查询嵌入
        query_embedding = self.model.encode([query])[0]
        
        # 计算相似度
        similarities = np.dot(self.material_embeddings, query_embedding)
        
        # 获取top-k结果
        k = top_k or self.max_results
        top_indices = np.argsort(similarities)[::-1][:k]
        
        results = []
        for idx in top_indices:
            similarity = float(similarities[idx])
            if similarity >= self.similarity_threshold:
                material = self.material_index[idx].copy()
                material['similarity'] = similarity
                
                # 类型过滤
                if material_type is None or material['type'] == material_type:
                    results.append(material)
        
        if self.logger:
            self.logger.info(f"找到 {len(results)} 个相关素材")
        
        return results
    
    def get_material_info(self, file_path: str) -> Dict[str, Any]:
        """获取指定素材的详细信息
        
        Args:
            file_path: 素材文件路径
            
        Returns:
            素材信息字典
        """
        path = Path(file_path)
        if not path.exists():
            raise MaterialNotFoundError(f"素材文件不存在: {file_path}")
        
        return self._extract_material_info(path)
    
    def update_index(self) -> None:
        """更新素材索引
        
        重新扫描素材目录并更新索引。
        """
        if self.logger:
            self.logger.info("更新素材索引")
        self.build_index()
    
    def save_index(self, output_path: str) -> None:
        """保存索引到文件
        
        Args:
            output_path: 输出文件路径
        """
        index_data = {
            'materials': list(self.material_index.values()),
            'embeddings': self.material_embeddings.tolist() if self.material_embeddings is not None else []
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        if self.logger:
            self.logger.info(f"索引已保存到: {output_path}")
    
    def load_index(self, index_path: str) -> None:
        """从文件加载索引
        
        Args:
            index_path: 索引文件路径
        """
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        self.material_index = {i: material for i, material in enumerate(index_data['materials'])}
        self.material_embeddings = np.array(index_data['embeddings'])
        
        if self.logger:
            self.logger.info(f"索引已从文件加载: {index_path}")