"""
NLP模型对比测试框架
支持多种情感分析模型在不同平台数据上的准确度评估

支持的模型:
1. SnowNLP - 中文情感分析
2. TextBlob - 基于规则的情感分析
3. 百度AI情感分析API (可选)
4. 自定义规则模型 - 基于情感词典
5. BERT中文情感分析 (可选)
"""
import argparse
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

import aiomysql
import pandas as pd
import numpy as np
from snownlp import SnowNLP
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, classification_report, f1_score
)
import json

from config import db_config


class SentimentModel:
    """情感分析模型基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    def predict(self, text: str) -> Tuple[str, float]:
        """
        预测文本情感
        
        Args:
            text: 待分析文本
            
        Returns:
            (label, score): 情感标签和置信度分数
                label: 'positive', 'neutral', 'negative'
                score: -1.0 ~ 1.0
        """
        raise NotImplementedError
    
    def get_description(self) -> str:
        """获取模型描述"""
        return f"{self.name} - 情感分析模型"


class SnowNLPModel(SentimentModel):
    """SnowNLP模型"""
    
    def __init__(self):
        super().__init__("SnowNLP")
        self.positive_threshold = 0.6
        self.negative_threshold = 0.4
    
    def predict(self, text: str) -> Tuple[str, float]:
        try:
            s = SnowNLP(text)
            score = s.sentiments  # 0~1
            
            # 转换为-1~1的分数
            normalized_score = (score - 0.5) * 2
            
            # 分类
            if score > self.positive_threshold:
                label = 'positive'
            elif score < self.negative_threshold:
                label = 'negative'
            else:
                label = 'neutral'
            
            return label, normalized_score
        except:
            return 'neutral', 0.0
    
    def get_description(self) -> str:
        return "SnowNLP - 基于朴素贝叶斯的中文情感分析"


class RuleBasedModel(SentimentModel):
    """基于规则和情感词典的模型"""
    
    def __init__(self):
        super().__init__("RuleBased")
        
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
    
    def predict(self, text: str) -> Tuple[str, float]:
        if not text:
            return 'neutral', 0.0
        
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
            return 'neutral', 0.0
        
        # 归一化分数 -1~1
        score = (positive_count - negative_count) / (total + 1)
        
        # 分类
        if score > 0.2:
            label = 'positive'
        elif score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'
        
        return label, score
    
    def get_description(self) -> str:
        return "RuleBased - 基于情感词典和规则的分析"


class HybridModel(SentimentModel):
    """混合模型：SnowNLP + 规则模型"""
    
    def __init__(self, snow_weight: float = 0.6, rule_weight: float = 0.4):
        super().__init__(f"Hybrid_{int(snow_weight*10)}_{int(rule_weight*10)}")
        self.snow_model = SnowNLPModel()
        self.rule_model = RuleBasedModel()
        self.snow_weight = snow_weight
        self.rule_weight = rule_weight
    
    def predict(self, text: str) -> Tuple[str, float]:
        snow_label, snow_score = self.snow_model.predict(text)
        rule_label, rule_score = self.rule_model.predict(text)
        
        # 加权平均
        final_score = snow_score * self.snow_weight + rule_score * self.rule_weight
        
        # 分类
        if final_score > 0.2:
            label = 'positive'
        elif final_score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'
        
        return label, final_score
    
    def get_description(self) -> str:
        return f"Hybrid_{int(self.snow_weight*10)}_{int(self.rule_weight*10)} - SnowNLP({int(self.snow_weight*100)}%) + RuleBased({int(self.rule_weight*100)}%)"


class SimpleThresholdModel(SentimentModel):
    """简单阈值模型：基于文本长度和标点符号"""
    
    def __init__(self):
        super().__init__("SimpleThreshold")
    
    def predict(self, text: str) -> Tuple[str, float]:
        if not text:
            return 'neutral', 0.0
        
        # 简单规则
        exclamation_count = text.count('!') + text.count('!')
        question_count = text.count('?') + text.count('?')
        emoji_positive = any(e in text for e in ['😊', '😄', '😍', '🥰', '👍', '❤️'])
        emoji_negative = any(e in text for e in ['😭', '😤', '😡', '💔', '👎', '🤮'])
        
        score = 0.0
        
        if exclamation_count > 0:
            score += 0.3 * min(exclamation_count, 3)
        
        if emoji_positive:
            score += 0.5
        
        if emoji_negative:
            score -= 0.5
        
        # 归一化
        score = max(-1.0, min(1.0, score))
        
        if score > 0.2:
            label = 'positive'
        elif score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'
        
        return label, score
    
    def get_description(self) -> str:
        return "SimpleThreshold - 基于标点和emoji的简单判断"


class ModelComparator:
    """模型对比测试器"""
    
    def __init__(self):
        self.test_db_name = "nlp_test_dataset"
        self.models = {
            'snownlp': SnowNLPModel(),
            'rule_based': RuleBasedModel(),
            'hybrid_6_4': HybridModel(snow_weight=0.6, rule_weight=0.4),
            'hybrid_7_3': HybridModel(snow_weight=0.7, rule_weight=0.3),
            'hybrid_5_5': HybridModel(snow_weight=0.5, rule_weight=0.5),
            'simple_threshold': SimpleThresholdModel(),
        }
        
        self.platform_results = defaultdict(lambda: defaultdict(dict))
        self.overall_results = defaultdict(dict)
    
    async def get_mysql_connection(self):
        """创建MySQL连接"""
        return await aiomysql.connect(
            host=db_config.MYSQL_DB_HOST,
            port=db_config.MYSQL_DB_PORT,
            user=db_config.MYSQL_DB_USER,
            password=db_config.MYSQL_DB_PWD,
            db=self.test_db_name,
            charset='utf8mb4',
            autocommit=True
        )
    
    async def load_annotated_data(self, platform: Optional[str] = None) -> pd.DataFrame:
        """
        加载已标注数据
        
        Args:
            platform: 平台名称，None表示全部平台
        """
        conn = await self.get_mysql_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 加载笔记
                sql = """
                    SELECT 'note' as type, platform, note_id as content_id, 
                           content, manual_sentiment_label as true_label
                    FROM test_notes
                    WHERE is_annotated = 1 AND manual_sentiment_label IS NOT NULL
                """
                if platform:
                    sql += f" AND platform = '{platform}'"
                
                await cursor.execute(sql)
                notes = await cursor.fetchall()
                
                # 加载评论
                sql = """
                    SELECT 'comment' as type, platform, comment_id as content_id,
                           content, manual_sentiment_label as true_label
                    FROM test_comments
                    WHERE is_annotated = 1 AND manual_sentiment_label IS NOT NULL
                """
                if platform:
                    sql += f" AND platform = '{platform}'"
                
                await cursor.execute(sql)
                comments = await cursor.fetchall()
                
                # 合并数据
                all_data = notes + comments
                df = pd.DataFrame(all_data)
                
                return df
        finally:
            conn.close()
    
    def evaluate_model(
        self,
        model: SentimentModel,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        评估单个模型
        
        Returns:
            评估指标字典
        """
        if len(df) == 0:
            return {
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'sample_count': 0
            }
        
        # 预测
        predictions = []
        true_labels = []
        
        for _, row in df.iterrows():
            text = row['content']
            true_label = row['true_label']
            
            pred_label, pred_score = model.predict(text)
            
            predictions.append(pred_label)
            true_labels.append(true_label)
        
        # 计算指标
        accuracy = accuracy_score(true_labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            true_labels, predictions, average='weighted', zero_division=0
        )
        
        # 混淆矩阵
        labels = ['positive', 'neutral', 'negative']
        cm = confusion_matrix(true_labels, predictions, labels=labels)
        
        # 分类报告
        report = classification_report(
            true_labels, predictions, 
            labels=labels,
            output_dict=True,
            zero_division=0
        )
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'confusion_matrix': cm.tolist(),
            'classification_report': report,
            'sample_count': len(df)
        }
    
    async def compare_all_models(self):
        """对比所有模型"""
        print("=" * 80)
        print("NLP情感分析模型对比测试")
        print("=" * 80)
        
        # 1. 全平台对比
        print("\n📊 正在加载全平台数据...")
        df_all = await self.load_annotated_data()
        
        if len(df_all) == 0:
            print("❌ 没有找到已标注的数据，请先运行标注工具")
            print("   提示: 运行 'uv run nlp/interactive_annotate.py' 或 'uv run nlp/ai_annotate.py'")
            return
        
        print(f"✓ 加载了 {len(df_all)} 条已标注数据")
        
        print("\n" + "=" * 80)
        print("全平台模型性能对比")
        print("=" * 80)
        
        for model_name, model in self.models.items():
            print(f"\n🔍 评估模型: {model.get_description()}")
            metrics = self.evaluate_model(model, df_all)
            self.overall_results[model_name] = metrics
            
            print(f"  准确率(Accuracy):  {metrics['accuracy']:.4f}")
            print(f"  精确率(Precision): {metrics['precision']:.4f}")
            print(f"  召回率(Recall):    {metrics['recall']:.4f}")
            print(f"  F1分数:            {metrics['f1_score']:.4f}")
            print(f"  样本数:            {metrics['sample_count']}")
        
        # 2. 各平台分别对比
        platforms = df_all['platform'].unique()
        
        for platform in platforms:
            print(f"\n" + "=" * 80)
            print(f"平台: {platform.upper()} - 模型性能对比")
            print("=" * 80)
            
            df_platform = df_all[df_all['platform'] == platform]
            print(f"样本数: {len(df_platform)}")
            
            for model_name, model in self.models.items():
                print(f"\n🔍 {model.get_description()}")
                metrics = self.evaluate_model(model, df_platform)
                self.platform_results[platform][model_name] = metrics
                
                print(f"  准确率: {metrics['accuracy']:.4f}  "
                      f"F1: {metrics['f1_score']:.4f}  "
                      f"样本数: {metrics['sample_count']}")
        
        # 3. 生成对比报告
        await self.generate_comparison_report()
    
    async def generate_comparison_report(self):
        """生成详细对比报告"""
        print("\n" + "=" * 80)
        print("📈 模型性能排行榜")
        print("=" * 80)
        
        # 全平台排行
        print("\n【全平台】按F1分数排序:")
        overall_sorted = sorted(
            self.overall_results.items(),
            key=lambda x: x[1]['f1_score'],
            reverse=True
        )
        
        print(f"{'排名':<6} {'模型名称':<45} {'准确率':<10} {'F1分数':<10} {'样本数':<10}")
        print("-" * 90)
        
        for rank, (model_name, metrics) in enumerate(overall_sorted, 1):
            model = self.models[model_name]
            print(f"{rank:<6} {model.get_description():<45} "
                  f"{metrics['accuracy']:<10.4f} "
                  f"{metrics['f1_score']:<10.4f} "
                  f"{metrics['sample_count']:<10}")
        
        # 各平台最佳模型
        print("\n【各平台最佳模型】")
        print(f"{'平台':<10} {'最佳模型':<45} {'F1分数':<10} {'准确率':<10}")
        print("-" * 90)
        
        for platform, models_metrics in self.platform_results.items():
            best_model = max(
                models_metrics.items(),
                key=lambda x: x[1]['f1_score']
            )
            model_name, metrics = best_model
            model = self.models[model_name]
            
            print(f"{platform:<10} {model.get_description():<45} "
                  f"{metrics['f1_score']:<10.4f} "
                  f"{metrics['accuracy']:<10.4f}")
        
        # 保存详细报告到JSON
        report_file = f"nlp_model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_results': {
                model_name: {
                    'model_description': self.models[model_name].get_description(),
                    'accuracy': float(metrics['accuracy']),
                    'precision': float(metrics['precision']),
                    'recall': float(metrics['recall']),
                    'f1_score': float(metrics['f1_score']),
                    'sample_count': metrics['sample_count'],
                    'confusion_matrix': metrics['confusion_matrix'],
                    'classification_report': metrics['classification_report']
                }
                for model_name, metrics in self.overall_results.items()
            },
            'platform_results': {
                platform: {
                    model_name: {
                        'model_description': self.models[model_name].get_description(),
                        'accuracy': float(metrics['accuracy']),
                        'f1_score': float(metrics['f1_score']),
                        'sample_count': metrics['sample_count']
                    }
                    for model_name, metrics in models_metrics.items()
                }
                for platform, models_metrics in self.platform_results.items()
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 详细报告已保存: {report_file}")
        
        # 生成可视化建议
        print("\n" + "=" * 80)
        print("📌 模型选择建议")
        print("=" * 80)
        
        best_overall = overall_sorted[0]
        print(f"\n【推荐模型】: {self.models[best_overall[0]].get_description()}")
        print(f"  - 综合F1分数最高: {best_overall[1]['f1_score']:.4f}")
        print(f"  - 准确率: {best_overall[1]['accuracy']:.4f}")
        
        # 分析平台差异
        print("\n【平台差异分析】:")
        f1_by_platform = {}
        for platform, models_metrics in self.platform_results.items():
            avg_f1 = np.mean([m['f1_score'] for m in models_metrics.values()])
            f1_by_platform[platform] = avg_f1
        
        sorted_platforms = sorted(f1_by_platform.items(), key=lambda x: x[1], reverse=True)
        
        print(f"  最易分析: {sorted_platforms[0][0]} (平均F1: {sorted_platforms[0][1]:.4f})")
        if len(sorted_platforms) > 1:
            print(f"  最难分析: {sorted_platforms[-1][0]} (平均F1: {sorted_platforms[-1][1]:.4f})")
        
        print("\n" + "=" * 80)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="NLP情感分析模型对比测试")
    parser.add_argument(
        '--platform',
        type=str,
        choices=['zhihu', 'xhs', 'tieba', 'all'],
        default='all',
        help='测试平台 (默认: all)'
    )
    
    args = parser.parse_args()
    
    comparator = ModelComparator()
    
    await comparator.compare_all_models()


if __name__ == "__main__":
    asyncio.run(main())
