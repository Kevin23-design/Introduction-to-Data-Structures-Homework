"""
评估情感分析模型性能
对比人工标注与模型预测结果
"""
import argparse
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple

import aiomysql
from snownlp import SnowNLP
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, classification_report
)
import pandas as pd
import numpy as np

from config import db_config


class SentimentModelEvaluator:
    """情感分析模型评估器"""
    
    def __init__(self, model_name: str = 'SnowNLP', use_platform_model: bool = False):
        """
        Args:
            model_name: 模型名称
            use_platform_model: 是否使用平台推荐模型
        """
        self.model_name = model_name
        self.use_platform_model = use_platform_model
        self.test_db_name = "nlp_test_dataset"
        self.results = {
            'notes': {'total': 0, 'annotated': 0, 'predictions': []},
            'comments': {'total': 0, 'annotated': 0, 'predictions': []}
        }
        
        # 平台推荐模型配置 (基于测试结果)
        self.platform_models = {
            'zhihu': {'model': 'Hybrid_6_4', 'snow_weight': 0.6, 'rule_weight': 0.4},
            'xhs': {'model': 'Hybrid_7_3', 'snow_weight': 0.7, 'rule_weight': 0.3},
            'tieba': {'model': 'Hybrid_6_4', 'snow_weight': 0.6, 'rule_weight': 0.4}
        }
        
        # 情感词典 (用于规则模型和混合模型)
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
    
    def _predict_with_snownlp(self, text: str) -> Tuple[str, float]:
        """SnowNLP预测"""
        try:
            s = SnowNLP(text)
            score = s.sentiments  # 0~1
            normalized_score = (score - 0.5) * 2  # -1~1
            
            if score > 0.6:
                label = 'positive'
            elif score < 0.4:
                label = 'negative'
            else:
                label = 'neutral'
            
            return label, normalized_score
        except:
            return 'neutral', 0.0
    
    def _predict_with_rules(self, text: str) -> Tuple[str, float]:
        """基于规则预测"""
        if not text:
            return 'neutral', 0.0
        
        positive_count = 0
        negative_count = 0
        
        for word in self.positive_words:
            positive_count += text.count(word)
        
        for word in self.negative_words:
            negative_count += text.count(word)
        
        # 处理程度副词
        for intensifier in self.intensifiers:
            if intensifier in text:
                positive_count *= 1.2
                negative_count *= 1.2
        
        # 处理否定词
        negator_count = sum(text.count(neg) for neg in self.negators)
        if negator_count % 2 == 1:
            positive_count, negative_count = negative_count, positive_count
        
        total = positive_count + negative_count
        if total == 0:
            return 'neutral', 0.0
        
        score = (positive_count - negative_count) / (total + 1)
        
        if score > 0.2:
            label = 'positive'
        elif score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'
        
        return label, score
    
    def _predict_hybrid(self, text: str, snow_weight: float, rule_weight: float) -> Tuple[str, float]:
        """混合模型预测"""
        snow_label, snow_score = self._predict_with_snownlp(text)
        rule_label, rule_score = self._predict_with_rules(text)
        
        final_score = snow_score * snow_weight + rule_score * rule_weight
        
        if final_score > 0.2:
            label = 'positive'
        elif final_score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'
        
        return label, final_score
    
    def _predict_sentiment(self, text: str, platform: str = None) -> tuple:
        """
        根据模型名称选择预测方法
        
        Args:
            text: 文本内容
            platform: 平台名称 (zhihu/xhs/tieba)
        
        Returns:
            (label, score, confidence)
        """
        if not text or not text.strip():
            return ('neutral', 0.0, 0.0)
        
        try:
            # 如果启用平台推荐模型,使用平台特定的最佳模型
            if self.use_platform_model and platform and platform in self.platform_models:
                config = self.platform_models[platform]
                label, normalized_score = self._predict_hybrid(
                    text,
                    config['snow_weight'],
                    config['rule_weight']
                )
                confidence = abs(normalized_score)
            # 否则根据指定的模型名称选择预测方法
            elif self.model_name == 'SnowNLP':
                label, normalized_score = self._predict_with_snownlp(text)
                confidence = abs(normalized_score)
            elif self.model_name == 'RuleBased':
                label, normalized_score = self._predict_with_rules(text)
                confidence = abs(normalized_score)
            elif self.model_name.startswith('Hybrid'):
                # 解析权重: Hybrid_6_4 表示 60% SnowNLP + 40% RuleBased
                if '_' in self.model_name:
                    parts = self.model_name.split('_')
                    if len(parts) >= 3:
                        snow_weight = int(parts[1]) / 10.0
                        rule_weight = int(parts[2]) / 10.0
                    else:
                        snow_weight, rule_weight = 0.6, 0.4
                else:
                    snow_weight, rule_weight = 0.6, 0.4
                
                label, normalized_score = self._predict_hybrid(text, snow_weight, rule_weight)
                confidence = abs(normalized_score)
            else:
                # 默认使用SnowNLP
                label, normalized_score = self._predict_with_snownlp(text)
                confidence = abs(normalized_score)
            
            return (label, normalized_score, confidence)
        except Exception as e:
            print(f"预测失败: {e}")
            return ('neutral', 0.0, 0.0)
    
    async def create_evaluation_table(self):
        """创建模型评估结果表"""
        conn = await self.get_mysql_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS model_predictions (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        model_name VARCHAR(50) NOT NULL,
                        content_type VARCHAR(20) NOT NULL,
                        content_id INT NOT NULL,
                        platform VARCHAR(20),
                        predicted_label VARCHAR(20),
                        predicted_score FLOAT,
                        predicted_confidence FLOAT,
                        manual_label VARCHAR(20),
                        manual_score FLOAT,
                        is_correct BOOLEAN,
                        prediction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        KEY idx_model (model_name),
                        KEY idx_content (content_type, content_id),
                        KEY idx_prediction_time (prediction_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS model_evaluation_summary (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        model_name VARCHAR(50) NOT NULL,
                        content_type VARCHAR(20) NOT NULL,
                        evaluation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_samples INT,
                        accuracy FLOAT,
                        precision_score FLOAT,
                        recall FLOAT,
                        f1_score FLOAT,
                        confusion_matrix TEXT,
                        classification_report TEXT,
                        KEY idx_model (model_name),
                        KEY idx_eval_time (evaluation_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                print("✓ 评估表创建成功")
        finally:
            conn.close()
    
    async def load_annotated_notes(self) -> List[Dict]:
        """加载已标注的笔记数据"""
        conn = await self.get_mysql_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 检查总数
                await cursor.execute("SELECT COUNT(*) as total FROM test_notes")
                result = await cursor.fetchone()
                self.results['notes']['total'] = result['total']
                
                # 加载已标注数据
                await cursor.execute("""
                    SELECT id, platform, title, content, 
                           manual_sentiment_label, manual_sentiment_score
                    FROM test_notes 
                    WHERE is_annotated = TRUE
                    ORDER BY id
                """)
                notes = await cursor.fetchall()
                self.results['notes']['annotated'] = len(notes)
                
                return notes
        finally:
            conn.close()
    
    async def load_annotated_comments(self) -> List[Dict]:
        """加载已标注的评论数据"""
        conn = await self.get_mysql_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 检查总数
                await cursor.execute("SELECT COUNT(*) as total FROM test_comments")
                result = await cursor.fetchone()
                self.results['comments']['total'] = result['total']
                
                # 加载已标注数据
                await cursor.execute("""
                    SELECT id, platform, content,
                           manual_sentiment_label, manual_sentiment_score
                    FROM test_comments 
                    WHERE is_annotated = TRUE
                    ORDER BY id
                """)
                comments = await cursor.fetchall()
                self.results['comments']['annotated'] = len(comments)
                
                return comments
        finally:
            conn.close()
    
    async def evaluate_content(self, content_type: str, data: List[Dict]):
        """评估内容情感预测"""
        if not data:
            print(f"\n⚠️  没有已标注的{content_type}数据")
            return
        
        print(f"\n开始评估 {content_type} (共 {len(data)} 条已标注数据)...")
        
        predictions = []
        conn = await self.get_mysql_connection()
        
        try:
            async with conn.cursor() as cursor:
                # 清除该模型的旧预测记录
                await cursor.execute("""
                    DELETE FROM model_predictions 
                    WHERE model_name = %s AND content_type = %s
                """, (self.model_name, content_type))
                
                for item in data:
                    # 获取文本内容
                    if content_type == 'notes':
                        text = f"{item.get('title', '')} {item.get('content', '')}"
                    else:
                        text = item.get('content', '')
                    
                    # 获取平台信息
                    platform = item.get('platform', '')
                    
                    # 模型预测 (传递平台信息以支持平台推荐模型)
                    pred_label, pred_score, pred_confidence = self._predict_sentiment(text, platform)
                    
                    # 人工标注
                    manual_label = item['manual_sentiment_label']
                    manual_score = float(item['manual_sentiment_score']) if item['manual_sentiment_score'] else None
                    
                    # 判断是否正确
                    is_correct = (pred_label == manual_label)
                    
                    # 保存预测结果
                    await cursor.execute("""
                        INSERT INTO model_predictions
                        (model_name, content_type, content_id, platform,
                         predicted_label, predicted_score, predicted_confidence,
                         manual_label, manual_score, is_correct)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.model_name, content_type, item['id'], item['platform'],
                        pred_label, pred_score, pred_confidence,
                        manual_label, manual_score, is_correct
                    ))
                    
                    predictions.append({
                        'predicted': pred_label,
                        'actual': manual_label,
                        'correct': is_correct
                    })
                
                self.results[content_type]['predictions'] = predictions
                print(f"✓ {content_type} 预测完成")
        
        finally:
            conn.close()
    
    def _calculate_metrics(self, predictions: List[Dict]) -> Dict[str, Any]:
        """计算评估指标"""
        if not predictions:
            return None
        
        y_true = [p['actual'] for p in predictions]
        y_pred = [p['predicted'] for p in predictions]
        
        # 基础指标
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )
        
        # 混淆矩阵
        labels = ['positive', 'neutral', 'negative']
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        
        # 分类报告
        report = classification_report(y_true, y_pred, labels=labels, zero_division=0)
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'confusion_matrix': cm,
            'classification_report': report
        }
    
    async def save_evaluation_summary(self, content_type: str, metrics: Dict):
        """保存评估摘要"""
        if not metrics:
            return
        
        conn = await self.get_mysql_connection()
        try:
            async with conn.cursor() as cursor:
                # 转换混淆矩阵为JSON字符串
                cm_json = str(metrics['confusion_matrix'].tolist())
                
                await cursor.execute("""
                    INSERT INTO model_evaluation_summary
                    (model_name, content_type, total_samples,
                     accuracy, precision_score, recall, f1_score,
                     confusion_matrix, classification_report)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.model_name,
                    content_type,
                    len(self.results[content_type]['predictions']),
                    metrics['accuracy'],
                    metrics['precision'],
                    metrics['recall'],
                    metrics['f1'],
                    cm_json,
                    metrics['classification_report']
                ))
                
                print(f"✓ {content_type} 评估摘要已保存")
        finally:
            conn.close()
    
    def _print_metrics(self, content_type: str, metrics: Dict):
        """打印评估指标"""
        print(f"\n{'='*60}")
        print(f"{content_type.upper()} 评估结果 - {self.model_name}")
        print(f"{'='*60}")
        
        print(f"\n📊 基础指标:")
        print(f"准确率 (Accuracy):  {metrics['accuracy']:.2%}")
        print(f"精确率 (Precision): {metrics['precision']:.2%}")
        print(f"召回率 (Recall):    {metrics['recall']:.2%}")
        print(f"F1分数:             {metrics['f1']:.4f}")
        
        print(f"\n📈 混淆矩阵:")
        cm_df = pd.DataFrame(
            metrics['confusion_matrix'],
            index=['真·正面', '真·中性', '真·负面'],
            columns=['预测·正面', '预测·中性', '预测·负面']
        )
        print(cm_df)
        
        print(f"\n📋 详细分类报告:")
        print(metrics['classification_report'])
    
    async def run_evaluation(self):
        """执行完整评估流程"""
        start_time = datetime.now()
        
        print("="*60)
        if self.use_platform_model:
            print(f"开始评估模型: {self.model_name} (使用平台推荐模型)")
            print("="*60)
            print("平台推荐模型配置:")
            for platform, config in self.platform_models.items():
                print(f"  {platform}: {config['model']} (SnowNLP {config['snow_weight']*100:.0f}% + RuleBased {config['rule_weight']*100:.0f}%)")
        else:
            print(f"开始评估模型: {self.model_name}")
        print("="*60)
        
        try:
            # 创建评估表
            await self.create_evaluation_table()
            
            # 加载已标注数据
            print("\n正在加载已标注数据...")
            notes = await self.load_annotated_notes()
            comments = await self.load_annotated_comments()
            
            print(f"\n数据统计:")
            print(f"笔记: {self.results['notes']['annotated']}/{self.results['notes']['total']} 已标注")
            print(f"评论: {self.results['comments']['annotated']}/{self.results['comments']['total']} 已标注")
            
            if self.results['notes']['annotated'] == 0 and self.results['comments']['annotated'] == 0:
                print("\n❌ 没有已标注的数据，请先进行人工标注！")
                print("\n标注示例SQL:")
                print("""
UPDATE test_notes 
SET 
    manual_sentiment_label = 'positive',
    manual_sentiment_score = 0.8,
    annotator = '您的姓名',
    annotation_time = NOW(),
    is_annotated = TRUE
WHERE id = 1;
                """)
                return
            
            # 评估笔记
            if notes:
                await self.evaluate_content('notes', notes)
                metrics = self._calculate_metrics(self.results['notes']['predictions'])
                if metrics:
                    self._print_metrics('notes', metrics)
                    await self.save_evaluation_summary('notes', metrics)
            
            # 评估评论
            if comments:
                await self.evaluate_content('comments', comments)
                metrics = self._calculate_metrics(self.results['comments']['predictions'])
                if metrics:
                    self._print_metrics('comments', metrics)
                    await self.save_evaluation_summary('comments', metrics)
            
            # 总结
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print("\n"+"="*60)
            print("评估完成")
            print("="*60)
            print(f"总耗时: {duration:.2f} 秒")
            print(f"数据库: {self.test_db_name}")
            print("\n查询预测结果:")
            print(f"SELECT * FROM model_predictions WHERE model_name = '{self.model_name}';")
            print("\n查询评估摘要:")
            print(f"SELECT * FROM model_evaluation_summary WHERE model_name = '{self.model_name}';")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ 评估失败: {e}")
            import traceback
            traceback.print_exc()
            raise


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="评估情感分析模型性能")
    parser.add_argument(
        '--model',
        type=str,
        default='SnowNLP',
        help='模型名称 (默认: SnowNLP)'
    )
    parser.add_argument(
        '--use-platform-model',
        action='store_true',
        help='使用平台推荐的最佳模型 (zhihu: Hybrid_6_4, xhs: Hybrid_7_3, tieba: Hybrid_6_4)'
    )
    
    args = parser.parse_args()
    
    # 创建评估器并执行
    evaluator = SentimentModelEvaluator(
        model_name=args.model,
        use_platform_model=args.use_platform_model
    )
    await evaluator.run_evaluation()


if __name__ == "__main__":
    asyncio.run(main())
