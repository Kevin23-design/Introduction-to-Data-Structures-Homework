"""
使用平台推荐模型进行智能标注
根据模型对比测试结果,为不同平台使用最佳模型:
- zhihu: Hybrid_6_4 (SnowNLP 60% + RuleBased 40%)
- xhs: Hybrid_7_3 (SnowNLP 70% + RuleBased 30%)
- tieba: Hybrid_6_4 (SnowNLP 60% + RuleBased 40%)
"""
import argparse
import asyncio
from datetime import datetime
from typing import Tuple

import aiomysql
from snownlp import SnowNLP

from config import db_config


class PlatformSpecificAnnotator:
    """平台特定模型标注器"""
    
    def __init__(self, batch_size: int = 50, annotator: str = "AI_Platform_Optimized"):
        self.test_db_name = "nlp_test_dataset"
        self.batch_size = batch_size
        self.annotator = annotator
        
        # 情感词典 (与compare_nlp_models.py中的RuleBasedModel保持一致)
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
        
        # 平台推荐模型配置
        self.platform_models = {
            'zhihu': {'snow_weight': 0.6, 'rule_weight': 0.4, 'name': 'Hybrid_6_4'},
            'xhs': {'snow_weight': 0.7, 'rule_weight': 0.3, 'name': 'Hybrid_7_3'},
            'tieba': {'snow_weight': 0.6, 'rule_weight': 0.4, 'name': 'Hybrid_6_4'}
        }
        
        self.stats = {
            'zhihu': {'notes': 0, 'comments': 0},
            'xhs': {'notes': 0, 'comments': 0},
            'tieba': {'notes': 0, 'comments': 0}
        }
    
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
    
    def _predict_hybrid(
        self, 
        text: str, 
        snow_weight: float, 
        rule_weight: float
    ) -> Tuple[str, float]:
        """混合模型预测"""
        snow_label, snow_score = self._predict_with_snownlp(text)
        rule_label, rule_score = self._predict_with_rules(text)
        
        # 加权平均
        final_score = snow_score * snow_weight + rule_score * rule_weight
        
        if final_score > 0.2:
            label = 'positive'
        elif final_score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'
        
        return label, final_score
    
    def _predict_for_platform(self, text: str, platform: str) -> Tuple[str, float]:
        """根据平台使用对应的最佳模型预测"""
        model_config = self.platform_models.get(platform, {'snow_weight': 0.6, 'rule_weight': 0.4})
        return self._predict_hybrid(
            text,
            model_config['snow_weight'],
            model_config['rule_weight']
        )
    
    async def annotate_notes(self, platform: str = None):
        """标注笔记"""
        conn = await self.get_mysql_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 构建查询条件
                where_clause = "WHERE is_annotated = 0 OR is_annotated IS NULL"
                if platform:
                    where_clause += f" AND platform = '{platform}'"
                
                # 获取未标注的笔记
                await cursor.execute(f"""
                    SELECT id, platform, title, content
                    FROM test_notes
                    {where_clause}
                    LIMIT {self.batch_size}
                """)
                notes = await cursor.fetchall()
                
                if not notes:
                    return 0
                
                # 标注每条笔记
                for note in notes:
                    note_platform = note['platform']
                    text = f"{note['title'] or ''} {note['content'] or ''}"
                    
                    # 使用平台推荐模型预测
                    label, score = self._predict_for_platform(text, note_platform)
                    model_name = self.platform_models[note_platform]['name']
                    
                    # 更新数据库
                    await cursor.execute("""
                        UPDATE test_notes
                        SET 
                            manual_sentiment_label = %s,
                            manual_sentiment_score = %s,
                            annotator = %s,
                            annotation_time = NOW(),
                            annotation_notes = %s,
                            is_annotated = 1
                        WHERE id = %s
                    """, (
                        label,
                        float(score),
                        self.annotator,
                        f"使用{model_name}模型自动标注",
                        note['id']
                    ))
                    
                    self.stats[note_platform]['notes'] += 1
                
                return len(notes)
        
        finally:
            conn.close()
    
    async def annotate_comments(self, platform: str = None):
        """标注评论"""
        conn = await self.get_mysql_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 构建查询条件
                where_clause = "WHERE is_annotated = 0 OR is_annotated IS NULL"
                if platform:
                    where_clause += f" AND platform = '{platform}'"
                
                # 获取未标注的评论
                await cursor.execute(f"""
                    SELECT id, platform, content
                    FROM test_comments
                    {where_clause}
                    LIMIT {self.batch_size}
                """)
                comments = await cursor.fetchall()
                
                if not comments:
                    return 0
                
                # 标注每条评论
                for comment in comments:
                    comment_platform = comment['platform']
                    text = comment['content'] or ''
                    
                    # 使用平台推荐模型预测
                    label, score = self._predict_for_platform(text, comment_platform)
                    model_name = self.platform_models[comment_platform]['name']
                    
                    # 更新数据库
                    await cursor.execute("""
                        UPDATE test_comments
                        SET 
                            manual_sentiment_label = %s,
                            manual_sentiment_score = %s,
                            annotator = %s,
                            annotation_time = NOW(),
                            annotation_notes = %s,
                            is_annotated = 1
                        WHERE id = %s
                    """, (
                        label,
                        float(score),
                        self.annotator,
                        f"使用{model_name}模型自动标注",
                        comment['id']
                    ))
                    
                    self.stats[comment_platform]['comments'] += 1
                
                return len(comments)
        
        finally:
            conn.close()
    
    async def run_annotation(self, platform: str = None, reset: bool = False):
        """执行标注"""
        start_time = datetime.now()
        
        print("=" * 80)
        print("平台优化模型智能标注")
        print("=" * 80)
        
        # 显示使用的模型配置
        print("\n📋 平台推荐模型配置:")
        for plat, config in self.platform_models.items():
            if platform and plat != platform:
                continue
            print(f"  {plat:6s}: {config['name']} "
                  f"(SnowNLP {int(config['snow_weight']*100)}% + "
                  f"RuleBased {int(config['rule_weight']*100)}%)")
        
        # 如果需要重置
        if reset:
            print("\n⚠️  重置标注...")
            conn = await self.get_mysql_connection()
            try:
                async with conn.cursor() as cursor:
                    reset_clause = ""
                    if platform:
                        reset_clause = f"WHERE platform = '{platform}'"
                    
                    await cursor.execute(f"""
                        UPDATE test_notes 
                        SET is_annotated = 0, 
                            manual_sentiment_label = NULL,
                            manual_sentiment_score = NULL,
                            annotator = NULL,
                            annotation_time = NULL,
                            annotation_notes = NULL
                        {reset_clause}
                    """)
                    
                    await cursor.execute(f"""
                        UPDATE test_comments 
                        SET is_annotated = 0,
                            manual_sentiment_label = NULL,
                            manual_sentiment_score = NULL,
                            annotator = NULL,
                            annotation_time = NULL,
                            annotation_notes = NULL
                        {reset_clause}
                    """)
                    
                    print("✓ 标注已重置")
            finally:
                conn.close()
        
        try:
            # 标注笔记
            print(f"\n🔍 开始标注笔记...")
            total_notes = 0
            while True:
                count = await self.annotate_notes(platform)
                if count == 0:
                    break
                total_notes += count
                print(f"  已标注 {total_notes} 条笔记...")
            
            # 标注评论
            print(f"\n🔍 开始标注评论...")
            total_comments = 0
            while True:
                count = await self.annotate_comments(platform)
                if count == 0:
                    break
                total_comments += count
                print(f"  已标注 {total_comments} 条评论...")
            
            # 显示统计
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print("\n" + "=" * 80)
            print("标注完成统计")
            print("=" * 80)
            
            total_all_notes = sum(s['notes'] for s in self.stats.values())
            total_all_comments = sum(s['comments'] for s in self.stats.values())
            
            print(f"\n按平台统计:")
            for plat in ['zhihu', 'xhs', 'tieba']:
                if platform and plat != platform:
                    continue
                model_name = self.platform_models[plat]['name']
                print(f"  {plat:6s} ({model_name}): "
                      f"{self.stats[plat]['notes']:3d} 笔记, "
                      f"{self.stats[plat]['comments']:3d} 评论")
            
            print(f"\n总计:")
            print(f"  笔记:   {total_all_notes} 条")
            print(f"  评论:   {total_all_comments} 条")
            print(f"  耗时:   {duration:.2f} 秒")
            
            print(f"\n数据库: {self.test_db_name}")
            print("=" * 80)
            
            print("\n✨ 下一步:")
            print("  运行模型对比测试查看新标注的效果:")
            print("  uv run compare_nlp_models.py")
            
        except Exception as e:
            print(f"\n❌ 标注失败: {e}")
            import traceback
            traceback.print_exc()
            raise


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="使用平台推荐模型进行智能标注")
    parser.add_argument(
        '--platform',
        type=str,
        choices=['zhihu', 'xhs', 'tieba'],
        help='指定平台 (不指定则标注所有平台)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='每批处理数量 (默认: 50)'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='重置现有标注并重新标注'
    )
    
    args = parser.parse_args()
    
    annotator = PlatformSpecificAnnotator(
        batch_size=args.batch_size,
        annotator=f"AI_Platform_Optimized_{datetime.now().strftime('%Y%m%d')}"
    )
    
    await annotator.run_annotation(
        platform=args.platform,
        reset=args.reset
    )


if __name__ == "__main__":
    asyncio.run(main())
