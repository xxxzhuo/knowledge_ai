"""重排序器实现 - 对检索结果进行重新排序。"""

import logging
from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Reranker(ABC):
    """重排序器基类"""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[Tuple[float, str, Dict[str, Any]]],
        top_k: int = 5
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        对检索结果重新排序
        
        参数:
            query: 查询文本
            documents: 检索结果 [(score, text, metadata), ...]
            top_k: 返回的文档数量
            
        返回:
            重排序后的文档列表
        """
        pass


class SimpleReranker(Reranker):
    """
    简单重排序器 - 基于相似度分数
    
    特性:
        - 基于原始相似度分数排序
        - 可配置最小相似度阈值
        - 去重处理
    """
    
    def __init__(self, min_similarity: float = 0.0):
        """
        初始化简单重排序器
        
        参数:
            min_similarity: 最小相似度阈值 (0-1)
        """
        self.min_similarity = min_similarity
        logger.info(f"初始化简单重排序器，最小相似度: {min_similarity}")
    
    def rerank(
        self,
        query: str,
        documents: List[Tuple[float, str, Dict[str, Any]]],
        top_k: int = 5
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        对检索结果重新排序
        
        Args:
            query: 查询文本
            documents: 检索结果 [(similarity, text, metadata), ...]
                       注意：VectorRetriever 已将 L2 距离转换为相似度
            top_k: 返回的文档数量
            
        Returns:
            重排序后的文档列表 [(similarity, text, metadata), ...]
        """
        if not documents:
            return []
        
        # 输入已经是 (similarity, text, metadata) 格式
        # VectorRetriever.retrieve_with_embedding() 已完成 L2 -> similarity 转换
        scored_docs = []
        seen_texts = set()
        
        for similarity, text, metadata in documents:
            # 去重
            if text in seen_texts:
                continue
            seen_texts.add(text)
            
            # 过滤低分文档
            if similarity >= self.min_similarity:
                scored_docs.append((similarity, text, metadata))
        
        # 按相似度降序排序
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # 返回 top_k
        result = scored_docs[:top_k]
        
        logger.debug(
            f"重排序完成: 输入 {len(documents)} 个文档, "
            f"过滤后 {len(scored_docs)} 个, 返回 {len(result)} 个"
        )
        
        return result


class CrossEncoderReranker(Reranker):
    """
    Cross-Encoder 重排序器 - 使用交叉编码器模型
    
    特性:
        - 使用 sentence-transformers 的 cross-encoder
        - 更精确的语义相似度计算
        - 支持多种预训练模型
    """
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu"
    ):
        """
        初始化 Cross-Encoder 重排序器
        
        参数:
            model_name: 预训练模型名称
            device: 计算设备 (cpu/cuda)
        """
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name, max_length=512, device=device)
            self.model_name = model_name
            logger.info(f"初始化 Cross-Encoder 重排序器: {model_name}")
        except ImportError:
            logger.error("请安装 sentence-transformers: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"加载 Cross-Encoder 模型失败: {str(e)}")
            raise
    
    def rerank(
        self,
        query: str,
        documents: List[Tuple[float, str, Dict[str, Any]]],
        top_k: int = 5
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        使用 Cross-Encoder 重排序
        
        Args:
            query: 查询文本
            documents: 检索结果 [(score, text, metadata), ...]
            top_k: 返回的文档数量
            
        Returns:
            重排序后的文档列表 [(cross_encoder_score, text, metadata), ...]
        """
        if not documents:
            return []
        
        try:
            # 准备输入对
            pairs = [(query, text) for _, text, _ in documents]
            
            # 计算 cross-encoder 分数
            scores = self.model.predict(pairs)
            
            # 组合分数、文本和元数据
            scored_docs = [
                (float(score), text, metadata)
                for score, (_, text, metadata) in zip(scores, documents)
            ]
            
            # 按分数降序排序
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            
            # 返回 top_k
            result = scored_docs[:top_k]
            
            logger.debug(
                f"Cross-Encoder 重排序完成: "
                f"输入 {len(documents)} 个文档, 返回 {len(result)} 个"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Cross-Encoder 重排序失败: {str(e)}")
            # 降级到简单排序
            logger.warning("降级到简单重排序")
            simple_reranker = SimpleReranker()
            return simple_reranker.rerank(query, documents, top_k)


class HybridReranker(Reranker):
    """
    混合重排序器 - 结合多种排序策略
    
    特性:
        - 结合向量相似度和 cross-encoder 分数
        - 可配置权重
        - 支持多样性控制
    """
    
    def __init__(
        self,
        vector_weight: float = 0.4,
        cross_encoder_weight: float = 0.6,
        diversity_penalty: float = 0.1,
        cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        """
        初始化混合重排序器
        
        参数:
            vector_weight: 向量相似度权重
            cross_encoder_weight: Cross-encoder 分数权重
            diversity_penalty: 多样性惩罚 (0-1)
            cross_encoder_model: Cross-encoder 模型名称
        """
        self.vector_weight = vector_weight
        self.cross_encoder_weight = cross_encoder_weight
        self.diversity_penalty = diversity_penalty
        
        # 初始化 cross-encoder
        try:
            self.cross_encoder = CrossEncoderReranker(cross_encoder_model)
        except Exception as e:
            logger.warning(f"Cross-Encoder 初始化失败，使用简单重排序: {str(e)}")
            self.cross_encoder = None
        
        logger.info(
            f"初始化混合重排序器 - "
            f"向量权重: {vector_weight}, "
            f"CE权重: {cross_encoder_weight}, "
            f"多样性惩罚: {diversity_penalty}"
        )
    
    def rerank(
        self,
        query: str,
        documents: List[Tuple[float, str, Dict[str, Any]]],
        top_k: int = 5
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        使用混合策略重排序
        
        Args:
            query: 查询文本
            documents: 检索结果 [(similarity, text, metadata), ...]
                       注意：VectorRetriever 已将 L2 距离转换为相似度
            top_k: 返回的文档数量
            
        Returns:
            重排序后的文档列表 [(combined_score, text, metadata), ...]
        """
        if not documents:
            return []
        
        # 输入已经是 similarity（VectorRetriever 已转换），直接使用
        vector_scores = [similarity for similarity, _, _ in documents]
        
        # 建立文本到原始索引的映射，用于对齐 CE 分数
        text_to_idx = {text: i for i, (_, text, _) in enumerate(documents)}
        
        # 获取 cross-encoder 分数
        if self.cross_encoder:
            ce_results = self.cross_encoder.rerank(query, documents, len(documents))
            # CE rerank 会改变顺序，需要按文本重新对齐到原始顺序
            ce_score_map = {text: score for score, text, _ in ce_results}
            ce_scores = [ce_score_map.get(text, 0.0) for _, text, _ in documents]
        else:
            ce_scores = vector_scores  # 降级
        
        # 归一化分数
        def normalize(scores):
            if not scores:
                return []
            min_s, max_s = min(scores), max(scores)
            if max_s - min_s == 0:
                return [0.5] * len(scores)
            return [(s - min_s) / (max_s - min_s) for s in scores]
        
        norm_vector = normalize(vector_scores)
        norm_ce = normalize(ce_scores)
        
        # 计算组合分数
        combined_docs = []
        for i, (_, text, metadata) in enumerate(documents):
            combined_score = (
                self.vector_weight * norm_vector[i] +
                self.cross_encoder_weight * norm_ce[i]
            )
            combined_docs.append((combined_score, text, metadata))
        
        # 排序
        combined_docs.sort(key=lambda x: x[0], reverse=True)
        
        # 应用多样性惩罚（可选）
        if self.diversity_penalty > 0:
            combined_docs = self._apply_diversity(combined_docs, top_k)
        
        result = combined_docs[:top_k]
        
        logger.debug(
            f"混合重排序完成: "
            f"输入 {len(documents)} 个文档, 返回 {len(result)} 个"
        )
        
        return result
    
    def _apply_diversity(
        self,
        documents: List[Tuple[float, str, Dict[str, Any]]],
        top_k: int
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        应用多样性惩罚（MMR-like）
        
        Args:
            documents: 排序后的文档
            top_k: 目标数量
            
        Returns:
            应用多样性后的文档列表
        """
        if not documents or top_k <= 0:
            return documents
        
        selected = []
        remaining = list(documents)
        
        # 选择第一个（得分最高的）
        selected.append(remaining.pop(0))
        
        # MMR selection
        while len(selected) < top_k and remaining:
            best_idx = 0
            best_score = -float('inf')
            
            for i, (score, text, metadata) in enumerate(remaining):
                # 计算与已选文档的最大相似度
                max_sim = max(
                    self._text_similarity(text, sel_text)
                    for _, sel_text, _ in selected
                )
                
                # MMR 分数
                mmr_score = score - self.diversity_penalty * max_sim
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        return selected
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        简单的文本相似度计算（基于 Jaccard）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数 (0-1)
        """
        # 对中文文本使用字符级 n-gram（bigram）而非空格分词
        def char_ngrams(text: str, n: int = 2) -> set:
            text = text.lower().strip()
            if len(text) < n:
                return {text} if text else set()
            return {text[i:i+n] for i in range(len(text) - n + 1)}
        
        ngrams1 = char_ngrams(text1)
        ngrams2 = char_ngrams(text2)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        
        return intersection / union if union > 0 else 0.0


def get_reranker(reranker_type: str = "simple", **kwargs) -> Reranker:
    """
    获取重排序器实例
    
    Args:
        reranker_type: 重排序器类型 (simple/cross_encoder/hybrid)
        **kwargs: 重排序器参数
        
    Returns:
        Reranker 实例
    """
    if reranker_type == "simple":
        return SimpleReranker(**kwargs)
    elif reranker_type == "cross_encoder":
        return CrossEncoderReranker(**kwargs)
    elif reranker_type == "hybrid":
        return HybridReranker(**kwargs)
    else:
        logger.warning(f"未知的重排序器类型: {reranker_type}，使用 simple")
        return SimpleReranker()
