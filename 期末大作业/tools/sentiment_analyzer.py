# -*- coding: utf-8 -*-
"""
情感分析器模块 - 基于 SnowNLP 实现中文情感分析
支持平台推荐的混合模型
"""
import asyncio
from typing import Dict, Any, List, Optional
from snownlp import SnowNLP


class SentimentAnalyzer:
    """
    情感分析器类
    使用 SnowNLP 和规则模型的混合方法进行中文文本情感分析
    """

    def __init__(self):
        """初始化情感分析器"""
        # 情感阈值配置
        self.positive_threshold = 0.6  # 正面情感阈值
        self.negative_threshold = 0.4  # 负面情感阈值
        
        # 平台推荐模型配置（基于测试结果）
        self.platform_models = {
            'zhihu': {'snow_weight': 0.6, 'rule_weight': 0.4},   # Hybrid_6_4
            'xhs': {'snow_weight': 0.7, 'rule_weight': 0.3},     # Hybrid_7_3
            'tieba': {'snow_weight': 0.6, 'rule_weight': 0.4}    # Hybrid_6_4
        }
        
        # 情感词典
        self.positive_words = {
            '好', '棒', '赞', '优秀', '喜欢', '爱', '美', '漂亮', '开心', '快乐',
            '满意', '完美', '惊艳', '精彩', '不错', '给力', '牛', '厉害', '强',
            '太好了', '喜爱', '支持', '推荐', '优质', '舒服', '温暖', '感动',
            '值得', '期待', '加油', '真棒', '666', '绝了', '可以', '舒适',
            '😊', '😄', '😍', '🥰', '👍', '❤️', '💕', '🎉', '✨', '👏'
        }
        
        self.negative_words = {
            '差', '烂', '糟', '垃圾', '失望', '讨厌', '恶心', '难看', '难受', '痛苦',
            '不好', '不行', '很烂', '太差', '糟糕', '恶劣', '坑', '骗', '假',
            '后悔', '不值', '不推荐', '难用', '不满', '生气', '愤怒', '郁闷',
            '无语', '崩溃', '吐了', '劝退', '拉黑', '退货', '差评', '坑爹',
            '😭', '😤', '😡', '💔', '👎', '🤮', '😞', '😒', '🙄', '💢'
        }
        
        self.intensifiers = {'很', '非常', '特别', '太', '超', '极', '十分', '相当', '格外'}
        self.negators = {'不', '没', '无', '未', '别', '莫', '勿', '非'}

    def _get_sentiment_label(self, score: float) -> str:
        """
        根据得分获取情感标签
        
        Args:
            score: SnowNLP 情感得分 (0-1)
            
        Returns:
            情感标签: positive/negative/neutral
        """
        if score >= self.positive_threshold:
            return "positive"
        elif score <= self.negative_threshold:
            return "negative"
        else:
            return "neutral"

    def _normalize_score(self, snownlp_score: float) -> float:
        """
        将 SnowNLP 的 0-1 分数转换为 -1 到 1 的范围
        
        Args:
            snownlp_score: SnowNLP 原始得分 (0-1)
            
        Returns:
            标准化得分 (-1 到 1)
        """
        return snownlp_score * 2 - 1

    def _calculate_confidence(self, score: float) -> float:
        """
        计算置信度
        置信度基于得分与中性点(0.5)的距离
        
        Args:
            score: SnowNLP 情感得分 (0-1)
            
        Returns:
            置信度 (0-1)
        """
        # 距离中性点越远,置信度越高
        return abs(score - 0.5) * 2

    def _predict_with_snownlp(self, text: str) -> tuple:
        """
        使用 SnowNLP 进行预测
        
        Returns:
            (raw_score, normalized_score) 其中 raw_score 为 0-1, normalized_score 为 -1~1
        """
        try:
            s = SnowNLP(text)
            raw_score = s.sentiments  # 0-1
            normalized_score = self._normalize_score(raw_score)  # -1~1
            return raw_score, normalized_score
        except:
            return 0.5, 0.0

    def _predict_with_rules(self, text: str) -> float:
        """
        使用规则模型进行预测
        
        Returns:
            normalized_score: -1~1 范围的情感分数
        """
        if not text:
            return 0.0
        
        positive_count = 0
        negative_count = 0
        
        # 计算情感词出现次数
        for word in self.positive_words:
            positive_count += text.count(word)
        
        for word in self.negative_words:
            negative_count += text.count(word)
        
        # 处理程度副词（加权）
        for intensifier in self.intensifiers:
            if intensifier in text:
                positive_count *= 1.2
                negative_count *= 1.2
        
        # 处理否定词（反转）
        negator_count = sum(text.count(neg) for neg in self.negators)
        if negator_count % 2 == 1:  # 奇数次否定，反转情感
            positive_count, negative_count = negative_count, positive_count
        
        # 计算总分
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        # 归一化分数 -1~1
        score = (positive_count - negative_count) / (total + 1)
        return score

    def _predict_hybrid(self, text: str, snow_weight: float, rule_weight: float) -> tuple:
        """
        使用混合模型进行预测
        
        Args:
            text: 文本内容
            snow_weight: SnowNLP 权重
            rule_weight: 规则模型权重
            
        Returns:
            (raw_score, normalized_score) 其中 raw_score 为等效的 0-1, normalized_score 为 -1~1
        """
        # SnowNLP 预测
        _, snow_score = self._predict_with_snownlp(text)  # -1~1
        
        # 规则预测
        rule_score = self._predict_with_rules(text)  # -1~1
        
        # 加权平均
        final_score = snow_score * snow_weight + rule_score * rule_weight  # -1~1
        
        # 转换回 0-1 用于标签判断
        raw_score_equiv = (final_score + 1) / 2  # 0-1
        
        return raw_score_equiv, final_score

    async def analyze_text(self, text: str, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        分析单个文本的情感
        
        Args:
            text: 待分析的文本
            platform: 平台名称 (zhihu/xhs/tieba)，用于选择推荐模型
            
        Returns:
            包含情感分析结果的字典:
            {
                'score': float,        # 标准化得分 (-1 到 1)
                'label': str,          # 情感标签
                'confidence': float,   # 置信度 (0-1)
                'raw_score': float     # SnowNLP 原始得分 (0-1)
            }
        """
        # 处理空文本或无效文本
        if not text or not isinstance(text, str):
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'raw_score': 0.5
            }

        # 清理文本
        text = text.strip()
        if not text:
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'raw_score': 0.5
            }

        try:
            # 根据平台选择推荐模型
            if platform and platform in self.platform_models:
                config = self.platform_models[platform]
                raw_score, normalized_score = self._predict_hybrid(
                    text,
                    config['snow_weight'],
                    config['rule_weight']
                )
            else:
                # 默认使用 Hybrid_6_4 模型
                raw_score, normalized_score = self._predict_hybrid(text, 0.6, 0.4)
            
            # 计算各项指标
            label = self._get_sentiment_label(raw_score)
            confidence = self._calculate_confidence(raw_score)
            
            return {
                'score': round(normalized_score, 4),
                'label': label,
                'confidence': round(confidence, 4),
                'raw_score': round(raw_score, 4)
            }
        except Exception as e:
            # 发生异常时返回中性结果
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'raw_score': 0.5,
                'error': str(e)
            }

    async def analyze_batch(self, texts: List[str], platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        批量分析文本情感
        
        Args:
            texts: 待分析的文本列表
            platform: 平台名称 (zhihu/xhs/tieba)，用于选择推荐模型
            
        Returns:
            情感分析结果列表
        """
        tasks = [self.analyze_text(text, platform) for text in texts]
        results = await asyncio.gather(*tasks)
        return results

    def merge_texts(self, *texts: Optional[str]) -> str:
        """
        合并多个文本字段用于综合分析
        
        Args:
            *texts: 可变数量的文本参数
            
        Returns:
            合并后的文本
        """
        # 过滤掉 None 和空字符串,然后合并
        valid_texts = [str(t).strip() for t in texts if t]
        return " ".join(valid_texts)

    async def analyze_merged_text(self, *texts: Optional[str]) -> Dict[str, Any]:
        """
        分析合并后的多个文本字段
        适用于分析帖子的 title + desc + content
        
        Args:
            *texts: 可变数量的文本参数
            
        Returns:
            情感分析结果
        """
        merged_text = self.merge_texts(*texts)
        return await self.analyze_text(merged_text)


# 创建全局单例
_sentiment_analyzer = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """
    获取情感分析器单例
    
    Returns:
        SentimentAnalyzer 实例
    """
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer
