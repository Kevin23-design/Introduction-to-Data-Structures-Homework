# -*- coding: utf-8 -*-
"""
数据分析器模块 - 情感趋势分析
支持关键词过滤、时间范围、自定义时间间隔的情感分析可视化
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import json
import os

from sqlalchemy import select, and_, or_
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from database.db_session import get_session
from database.models import (
    ZhihuContent, ZhihuComment,
    XhsNote, XhsNoteComment,
    TiebaNote, TiebaComment
)
from tools.utils import logger


# 设置中文字体（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class SentimentDataAnalyzer:
    """
    情感数据分析器
    支持多维度的情感趋势分析和可视化
    """

    def __init__(self):
        """初始化分析器"""
        # 平台配置
        self.platform_config = {
            'zhihu': {
                'name': '知乎',
                'content_model': ZhihuContent,
                'comment_model': ZhihuComment,
                'content_time_field': 'created_time',
                'comment_time_field': 'publish_time',
                'content_text_fields': ['title', 'desc', 'content_text'],
                'comment_text_field': 'content',
                'time_format': 'timestamp_s',
                'color': '#0084FF',
            },
            'xhs': {
                'name': '小红书',
                'content_model': XhsNote,
                'comment_model': XhsNoteComment,
                'content_time_field': 'time',
                'comment_time_field': 'create_time',
                'content_text_fields': ['title', 'desc'],
                'comment_text_field': 'content',
                'time_format': 'timestamp_ms',
                'color': '#FF2442',
            },
            'tieba': {
                'name': '贴吧',
                'content_model': TiebaNote,
                'comment_model': TiebaComment,
                'content_time_field': 'publish_time',
                'comment_time_field': 'publish_time',
                'content_text_fields': ['title', 'desc'],
                'comment_text_field': 'content',
                'time_format': 'string',
                'color': '#3F51B5',
            }
        }

        # 时间间隔配置
        self.interval_config = {
            'day': {'days': 1, 'label': '日', 'format': '%Y-%m-%d'},
            'week': {'days': 7, 'label': '周', 'format': '%Y-W%W'},
            'month': {'days': 30, 'label': '月', 'format': '%Y-%m'},
        }

    def _parse_chinese_number(self, value: str) -> float:
        """
        解析中文数字格式 (如 "9.1万", "1千+")
        
        Args:
            value: 字符串格式的数字
            
        Returns:
            解析后的浮点数
        """
        if not value or not isinstance(value, str):
            return 0.0
        
        value = value.strip()
        if not value:
            return 0.0
        
        try:
            # 尝试直接转换为数字
            return float(value)
        except ValueError:
            pass
        
        # 处理中文数字格式
        try:
            # 移除 '+' 号
            value = value.replace('+', '')
            
            # 处理 "万" 单位
            if '万' in value:
                num_str = value.replace('万', '').strip()
                return float(num_str) * 10000
            
            # 处理 "千" 单位
            if '千' in value:
                num_str = value.replace('千', '').strip()
                return float(num_str) * 1000
            
            # 如果没有单位，尝试直接转换
            return float(value)
            
        except (ValueError, AttributeError):
            return 0.0

    def _calculate_heat_score(self, platform: str, record: Any, record_type: str) -> float:
        """
        计算单条数据的讨论热度得分 (使用对数平滑)
        
        对数平滑公式: heat = w1·log(x1+1) + w2·log(x2+1) + ...
        - 消除量纲差异，压缩数量级 (如将50000→500的100倍差距降为约2倍)
        - 避免爆款内容完全主导统计，使各层级内容均具可见性
        - 更符合人类对数字的感知特性 (韦伯-费希纳定律)
        
        Args:
            platform: 平台名称
            record: 数据记录对象
            record_type: 记录类型 ('post' or 'comment')
            
        Returns:
            对数热度得分 (float，通常在 0-50 范围)
        """
        import math
        
        try:
            if platform == 'zhihu':
                if record_type == 'post':
                    # 知乎帖子: log(点赞+1)*1.0 + log(评论数+1)*2.0
                    voteup = int(getattr(record, 'voteup_count', 0) or 0)
                    comment = int(getattr(record, 'comment_count', 0) or 0)
                    return math.log(voteup + 1) * 1.0 + math.log(comment + 1) * 2.0
                else:
                    # 知乎评论: log(点赞+1)*1.0 + log(子评论+1)*1.5
                    likes = int(getattr(record, 'like_count', 0) or 0)
                    sub_comment = int(getattr(record, 'sub_comment_count', 0) or 0)
                    return math.log(likes + 1) * 1.0 + math.log(sub_comment + 1) * 1.5
                    
            elif platform == 'xhs':
                if record_type == 'post':
                    # 小红书帖子: log(点赞+1)*1.0 + log(收藏+1)*1.5 + log(评论+1)*2.0 + log(分享+1)*2.5
                    liked = self._parse_chinese_number(getattr(record, 'liked_count', '0') or '0')
                    collected = self._parse_chinese_number(getattr(record, 'collected_count', '0') or '0')
                    comment = self._parse_chinese_number(getattr(record, 'comment_count', '0') or '0')
                    share = self._parse_chinese_number(getattr(record, 'share_count', '0') or '0')
                    return (math.log(liked + 1) * 1.0 + 
                           math.log(collected + 1) * 1.5 + 
                           math.log(comment + 1) * 2.0 + 
                           math.log(share + 1) * 2.5)
                else:
                    # 小红书评论: log(点赞+1)*1.0 + log(子评论+1)*1.5
                    likes = self._parse_chinese_number(getattr(record, 'like_count', '0') or '0')
                    sub_comment = int(getattr(record, 'sub_comment_count', 0) or 0)
                    return math.log(likes + 1) * 1.0 + math.log(sub_comment + 1) * 1.5
                    
            elif platform == 'tieba':
                if record_type == 'post':
                    # 贴吧帖子: log(回复数+1)*1.0
                    replay = int(getattr(record, 'total_replay_num', 0) or 0)
                    return math.log(replay + 1) * 1.0
                else:
                    # 贴吧评论: log(子评论+1)*1.0
                    sub_comment = int(getattr(record, 'sub_comment_count', 0) or 0)
                    return math.log(sub_comment + 1) * 1.0
                    
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"计算热度失败 ({platform}, {record_type}): {e}")
            return 0.0  # 对数默认返回0
        
        return 0.0

    def _parse_timestamp(self, timestamp: Any, time_format: str) -> Optional[datetime]:
        """
        解析不同格式的时间戳
        
        Args:
            timestamp: 时间戳（可能是字符串或数字）
            time_format: 时间格式类型 ('string'、'timestamp_s' 或 'timestamp_ms')
            
        Returns:
            datetime 对象或 None
        """
        try:
            if time_format == 'timestamp_ms':
                # 小红书使用毫秒时间戳
                if isinstance(timestamp, (int, float)):
                    return datetime.fromtimestamp(timestamp / 1000)
                elif isinstance(timestamp, str):
                    return datetime.fromtimestamp(int(timestamp) / 1000)
            elif time_format == 'timestamp_s':
                # 知乎使用秒级时间戳
                if isinstance(timestamp, (int, float)):
                    return datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, str):
                    return datetime.fromtimestamp(int(timestamp))
            else:  # string format
                # 贴吧使用字符串时间
                if isinstance(timestamp, str):
                    # 尝试多种时间格式
                    formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d %H:%M',
                        '%Y-%m-%d',
                        '%Y/%m/%d %H:%M:%S',
                        '%Y/%m/%d',
                    ]
                    for fmt in formats:
                        try:
                            return datetime.strptime(timestamp, fmt)
                        except ValueError:
                            continue
        except Exception as e:
            logger.warning(f"解析时间失败: {timestamp}, 错误: {e}")
        return None

    def _format_time_bucket(self, dt: datetime, interval: str) -> str:
        """
        根据时间间隔格式化时间桶
        
        Args:
            dt: datetime 对象
            interval: 时间间隔（day/week/month）
            
        Returns:
            格式化后的时间字符串
        """
        fmt = self.interval_config[interval]['format']
        return dt.strftime(fmt)

    def _generate_time_buckets(
        self,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> List[str]:
        """
        生成时间桶列表
        
        Args:
            start_date: 开始时间
            end_date: 结束时间
            interval: 时间间隔
            
        Returns:
            时间桶列表
        """
        buckets = []
        current = start_date
        delta = timedelta(days=self.interval_config[interval]['days'])
        
        while current <= end_date:
            bucket = self._format_time_bucket(current, interval)
            if bucket not in buckets:
                buckets.append(bucket)
            current += delta
        
        return buckets

    async def _fetch_platform_data(
        self,
        platform: str,
        keywords: Optional[List[str]],
        start_date: datetime,
        end_date: datetime,
        content_type: str = 'all'
    ) -> List[Dict[str, Any]]:
        """
        从数据库获取指定平台的数据（帖子和/或评论）
        
        Args:
            platform: 平台名称
            keywords: 关键词列表
            start_date: 开始时间
            end_date: 结束时间
            content_type: 内容类型 (post/comment/all)
            
        Returns:
            数据列表，每条数据包含: {time, sentiment_score, sentiment_label, text, type}
        """
        config = self.platform_config[platform]
        data = []
        
        async with get_session() as session:
            # 处理帖子数据
            if content_type in ['post', 'all']:
                model = config['content_model']
                stmt = select(model).where(
                    model.sentiment_label != None
                )
                
                # 添加关键词过滤 - 使用 source_keyword 字段
                if keywords:
                    keyword_conditions = [model.source_keyword.contains(kw) for kw in keywords]
                    stmt = stmt.where(or_(*keyword_conditions))
                
                result = await session.execute(stmt)
                records = result.scalars().all()
                
                time_field = config['content_time_field']
                time_format = config['time_format']
                
                for record in records:
                    timestamp = getattr(record, time_field)
                    dt = self._parse_timestamp(timestamp, time_format)
                    
                    if dt and start_date <= dt <= end_date:
                        # 获取文本内容
                        text_parts = [str(getattr(record, field, '')) for field in config['content_text_fields']]
                        text = ' '.join(text_parts)
                        
                        # 转换 sentiment_score (TEXT -> float)
                        try:
                            score = float(record.sentiment_score) if record.sentiment_score else 0.0
                        except (ValueError, TypeError):
                            score = 0.0
                        
                        # 计算讨论热度
                        heat_score = self._calculate_heat_score(platform, record, 'post')
                        
                        data.append({
                            'time': dt,
                            'sentiment_score': score,
                            'sentiment_label': record.sentiment_label,
                            'text': text,
                            'type': 'post',
                            'heat_score': heat_score
                        })
            
            # 处理评论数据
            if content_type in ['comment', 'all']:
                model = config['comment_model']
                stmt = select(model).where(
                    model.sentiment_label != None
                )
                
                # 添加关键词过滤 - 使用 source_keyword 字段
                if keywords:
                    keyword_conditions = [model.source_keyword.contains(kw) for kw in keywords]
                    stmt = stmt.where(or_(*keyword_conditions))
                
                result = await session.execute(stmt)
                records = result.scalars().all()
                
                time_field = config['comment_time_field']
                time_format = config['time_format']
                
                for record in records:
                    timestamp = getattr(record, time_field)
                    dt = self._parse_timestamp(timestamp, time_format)
                    
                    if dt and start_date <= dt <= end_date:
                        # 转换 sentiment_score (TEXT -> float)
                        try:
                            score = float(record.sentiment_score) if record.sentiment_score else 0.0
                        except (ValueError, TypeError):
                            score = 0.0
                        
                        # 计算讨论热度
                        heat_score = self._calculate_heat_score(platform, record, 'comment')
                        
                        data.append({
                            'time': dt,
                            'sentiment_score': score,
                            'sentiment_label': record.sentiment_label,
                            'text': getattr(record, config['comment_text_field'], ''),
                            'type': 'comment',
                            'heat_score': heat_score
                        })
        
        logger.info(f"平台 {config['name']} 获取到 {len(data)} 条数据")
        return data

    def _aggregate_by_time(
        self,
        data: List[Dict[str, Any]],
        interval: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        按时间间隔聚合数据
        
        Args:
            data: 原始数据列表
            interval: 时间间隔
            
        Returns:
            聚合后的数据 {time_bucket: {avg_score, positive_count, negative_count, neutral_count, total}}
        """
        aggregated = defaultdict(lambda: {
            'scores': [],
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'total': 0,
            'heat_scores': []  # 新增热度得分列表
        })
        
        for item in data:
            bucket = self._format_time_bucket(item['time'], interval)
            aggregated[bucket]['scores'].append(item['sentiment_score'])
            aggregated[bucket][item['sentiment_label']] += 1
            aggregated[bucket]['total'] += 1
            aggregated[bucket]['heat_scores'].append(item.get('heat_score', 1.0))  # 收集热度得分
        
        # 计算平均分和热度统计
        result = {}
        for bucket, stats in aggregated.items():
            heat_scores = stats['heat_scores']
            result[bucket] = {
                'avg_score': sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0,
                'positive_count': stats['positive'],
                'negative_count': stats['negative'],
                'neutral_count': stats['neutral'],
                'total_count': stats['total'],
                'positive_ratio': stats['positive'] / stats['total'] if stats['total'] > 0 else 0,
                'negative_ratio': stats['negative'] / stats['total'] if stats['total'] > 0 else 0,
                'avg_heat': sum(heat_scores) / len(heat_scores) if heat_scores else 0,  # 平均热度
                'total_heat': sum(heat_scores) if heat_scores else 0,  # 总热度
            }
        
        return result

    def _plot_single_platform(
        self,
        platform: str,
        aggregated_data: Dict[str, Dict[str, Any]],
        time_buckets: List[str],
        interval: str,
        keywords: Optional[List[str]],
        save_path: str
    ):
        """
        绘制单个平台的情感趋势图
        
        Args:
            platform: 平台名称
            aggregated_data: 聚合数据
            time_buckets: 时间桶列表
            interval: 时间间隔
            keywords: 关键词列表
            save_path: 保存路径
        """
        config = self.platform_config[platform]
        
        # 准备数据
        avg_scores = [aggregated_data.get(bucket, {}).get('avg_score', 0) for bucket in time_buckets]
        positive_ratios = [aggregated_data.get(bucket, {}).get('positive_ratio', 0) * 100 for bucket in time_buckets]
        negative_ratios = [aggregated_data.get(bucket, {}).get('negative_ratio', 0) * 100 for bucket in time_buckets]
        total_counts = [aggregated_data.get(bucket, {}).get('total_count', 0) for bucket in time_buckets]
        positive_counts = [aggregated_data.get(bucket, {}).get('positive_count', 0) for bucket in time_buckets]
        negative_counts = [aggregated_data.get(bucket, {}).get('negative_count', 0) for bucket in time_buckets]
        neutral_counts = [aggregated_data.get(bucket, {}).get('neutral_count', 0) for bucket in time_buckets]
        
        # 创建图表 - 改为4行1列
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(14, 18))
        fig.suptitle(
            f'{config["name"]} - 情感趋势分析\n关键词: {", ".join(keywords) if keywords else "全部"}',
            fontsize=16,
            fontweight='bold'
        )
        
        # 图1: 平均情感得分折线图
        ax1.plot(time_buckets, avg_scores, marker='o', linewidth=2, 
                color=config['color'], label='平均情感得分', markersize=6)
        ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.set_xlabel(f'时间（按{self.interval_config[interval]["label"]}）', fontsize=12)
        ax1.set_ylabel('平均情感得分', fontsize=12)
        ax1.set_title('情感得分趋势 (-1=负面, 0=中性, 1=正面)', fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=10)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 图2: 情感分布堆叠面积图
        ax2.fill_between(time_buckets, 0, positive_ratios, 
                         alpha=0.6, color='green', label='正面')
        ax2.fill_between(time_buckets, positive_ratios, 
                         [p + n for p, n in zip(positive_ratios, negative_ratios)],
                         alpha=0.6, color='red', label='负面')
        ax2.fill_between(time_buckets, 
                         [p + n for p, n in zip(positive_ratios, negative_ratios)], 
                         100,
                         alpha=0.6, color='gray', label='中性')
        
        ax2.set_xlabel(f'时间（按{self.interval_config[interval]["label"]}）', fontsize=12)
        ax2.set_ylabel('占比 (%)', fontsize=12)
        ax2.set_title('情感分布趋势', fontsize=14)
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=10)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 图3: 数据量统计（堆叠柱状图）
        width = 0.6
        x_pos = range(len(time_buckets))
        
        ax3.bar(x_pos, positive_counts, width, label='正面', color='green', alpha=0.7)
        ax3.bar(x_pos, neutral_counts, width, bottom=positive_counts, 
                label='中性', color='gray', alpha=0.7)
        ax3.bar(x_pos, negative_counts, width, 
                bottom=[p + n for p, n in zip(positive_counts, neutral_counts)],
                label='负面', color='red', alpha=0.7)
        
        # 在柱状图顶部显示总数
        for i, total in enumerate(total_counts):
            if total > 0:
                ax3.text(i, total, str(total), ha='center', va='bottom', fontsize=9)
        
        ax3.set_xlabel(f'时间（按{self.interval_config[interval]["label"]}）', fontsize=12)
        ax3.set_ylabel('数据量', fontsize=12)
        ax3.set_title('时间桶数据量统计', fontsize=14)
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(time_buckets)
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.legend(fontsize=10)
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 图4: 讨论热度趋势
        total_heats = [aggregated_data.get(bucket, {}).get('total_heat', 0) for bucket in time_buckets]
        avg_heats = [aggregated_data.get(bucket, {}).get('avg_heat', 0) for bucket in time_buckets]
        
        ax4.plot(time_buckets, total_heats, marker='D', linewidth=2, 
                color=config['color'], label='总热度', markersize=6, alpha=0.7)
        ax4_twin = ax4.twinx()  # 创建共享x轴的第二个y轴
        ax4_twin.plot(time_buckets, avg_heats, marker='o', linewidth=2, 
                     color='orange', label='平均热度', markersize=5, linestyle='--', alpha=0.7)
        
        ax4.set_xlabel(f'时间（按{self.interval_config[interval]["label"]}）', fontsize=12)
        ax4.set_ylabel('总热度', fontsize=12, color=config['color'])
        ax4_twin.set_ylabel('平均热度', fontsize=12, color='orange')
        ax4.set_title('讨论热度趋势', fontsize=14)
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis='y', labelcolor=config['color'])
        ax4_twin.tick_params(axis='y', labelcolor='orange')
        
        # 合并图例
        lines1, labels1 = ax4.get_legend_handles_labels()
        lines2, labels2 = ax4_twin.get_legend_handles_labels()
        ax4.legend(lines1 + lines2, labels1 + labels2, fontsize=10, loc='upper left')
        
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"已保存 {config['name']} 情感趋势图（含数据量统计和热度趋势）: {save_path}")

    def _plot_comparison(
        self,
        platforms_data: Dict[str, Dict[str, Dict[str, Any]]],
        time_buckets: List[str],
        interval: str,
        keywords: Optional[List[str]],
        save_path: str
    ):
        """
        绘制多平台对比图
        
        Args:
            platforms_data: 各平台的聚合数据 {platform: {bucket: stats}}
            time_buckets: 时间桶列表
            interval: 时间间隔
            keywords: 关键词列表
            save_path: 保存路径
        """
        # 改为4行1列布局
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(14, 18))
        fig.suptitle(
            f'多平台情感趋势对比\n关键词: {", ".join(keywords) if keywords else "全部"}',
            fontsize=16,
            fontweight='bold'
        )
        
        # 图1: 平均情感得分对比
        for platform, aggregated_data in platforms_data.items():
            config = self.platform_config[platform]
            avg_scores = [aggregated_data.get(bucket, {}).get('avg_score', 0) for bucket in time_buckets]
            ax1.plot(time_buckets, avg_scores, marker='o', linewidth=2,
                    color=config['color'], label=config['name'], markersize=6)
        
        ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.set_xlabel(f'时间（按{self.interval_config[interval]["label"]}）', fontsize=12)
        ax1.set_ylabel('平均情感得分', fontsize=12)
        ax1.set_title('各平台情感得分趋势对比', fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=10)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 图2: 正面情感占比对比
        for platform, aggregated_data in platforms_data.items():
            config = self.platform_config[platform]
            positive_ratios = [aggregated_data.get(bucket, {}).get('positive_ratio', 0) * 100 
                             for bucket in time_buckets]
            ax2.plot(time_buckets, positive_ratios, marker='s', linewidth=2,
                    color=config['color'], label=config['name'], markersize=6)
        
        ax2.set_xlabel(f'时间（按{self.interval_config[interval]["label"]}）', fontsize=12)
        ax2.set_ylabel('正面情感占比 (%)', fontsize=12)
        ax2.set_title('各平台正面情感占比趋势', fontsize=14)
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=10)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 图3: 数据量对比（折线图）
        for platform, aggregated_data in platforms_data.items():
            config = self.platform_config[platform]
            total_counts = [aggregated_data.get(bucket, {}).get('total_count', 0) 
                          for bucket in time_buckets]
            ax3.plot(time_buckets, total_counts, marker='^', linewidth=2,
                    color=config['color'], label=config['name'], markersize=6)
        
        ax3.set_xlabel(f'时间（按{self.interval_config[interval]["label"]}）', fontsize=12)
        ax3.set_ylabel('数据量', fontsize=12)
        ax3.set_title('各平台时间桶数据量对比', fontsize=14)
        ax3.grid(True, alpha=0.3)
        ax3.legend(fontsize=10)
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 图4: 平均热度对比
        for platform, aggregated_data in platforms_data.items():
            config = self.platform_config[platform]
            avg_heats = [aggregated_data.get(bucket, {}).get('avg_heat', 0) 
                        for bucket in time_buckets]
            ax4.plot(time_buckets, avg_heats, marker='D', linewidth=2,
                    color=config['color'], label=config['name'], markersize=6)
        
        ax4.set_xlabel(f'时间（按{self.interval_config[interval]["label"]}）', fontsize=12)
        ax4.set_ylabel('平均讨论热度', fontsize=12)
        ax4.set_title('各平台讨论热度对比', fontsize=14)
        ax4.grid(True, alpha=0.3)
        ax4.legend(fontsize=10)
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"已保存多平台对比图（含数据量统计和热度对比）: {save_path}")

    async def analyze_and_visualize(
        self,
        platforms: List[str] = ['zhihu', 'xhs', 'tieba'],
        keywords: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = 'day',
        content_type: str = 'all',
        output_dir: str = './sentiment_analysis_charts'
    ) -> Dict[str, Any]:
        """
        执行情感趋势分析并生成可视化图表
        
        Args:
            platforms: 要分析的平台列表
            keywords: 关键词列表（可选）
            start_date: 开始日期（格式: YYYY-MM-DD）
            end_date: 结束日期（格式: YYYY-MM-DD）
            interval: 时间间隔 (day/week/month)
            content_type: 内容类型 (post/comment/all)
            output_dir: 输出目录
            
        Returns:
            分析结果统计
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 解析时间范围
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_dt = datetime.now() - timedelta(days=30)  # 默认最近30天
        
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_dt = datetime.now()
        
        logger.info("=" * 60)
        logger.info("开始情感趋势分析")
        logger.info(f"平台: {', '.join([self.platform_config[p]['name'] for p in platforms])}")
        logger.info(f"关键词: {keywords if keywords else '全部'}")
        logger.info(f"时间范围: {start_dt.date()} 至 {end_dt.date()}")
        logger.info(f"时间间隔: {self.interval_config[interval]['label']}")
        logger.info(f"内容类型: {content_type}")
        logger.info("=" * 60)
        
        # 生成时间桶
        time_buckets = self._generate_time_buckets(start_dt, end_dt, interval)
        logger.info(f"生成 {len(time_buckets)} 个时间桶")
        
        # 收集各平台数据
        platforms_data = {}
        platforms_raw_data = {}
        
        for platform in platforms:
            logger.info(f"\n正在获取 {self.platform_config[platform]['name']} 数据...")
            raw_data = await self._fetch_platform_data(
                platform, keywords, start_dt, end_dt, content_type
            )
            platforms_raw_data[platform] = raw_data
            
            # 聚合数据
            aggregated = self._aggregate_by_time(raw_data, interval)
            platforms_data[platform] = aggregated
            
            # 绘制单平台图表
            chart_name = f"{platform}_sentiment_trend_{interval}.png"
            chart_path = os.path.join(output_dir, chart_name)
            self._plot_single_platform(
                platform, aggregated, time_buckets, interval, keywords, chart_path
            )
        
        # 绘制对比图
        if len(platforms) > 1:
            comparison_name = f"comparison_sentiment_trend_{interval}.png"
            comparison_path = os.path.join(output_dir, comparison_name)
            self._plot_comparison(
                platforms_data, time_buckets, interval, keywords, comparison_path
            )
        
        # 生成统计报告
        stats = {
            'platforms': {},
            'time_range': {
                'start': start_date or start_dt.strftime('%Y-%m-%d'),
                'end': end_date or end_dt.strftime('%Y-%m-%d'),
            },
            'interval': interval,
            'keywords': keywords,
            'content_type': content_type,
            'charts': []
        }
        
        for platform in platforms:
            raw_data = platforms_raw_data[platform]
            positive = sum(1 for d in raw_data if d['sentiment_label'] == 'positive')
            negative = sum(1 for d in raw_data if d['sentiment_label'] == 'negative')
            neutral = sum(1 for d in raw_data if d['sentiment_label'] == 'neutral')
            total = len(raw_data)
            
            # 计算总热度和平均热度
            total_heat = sum(d.get('heat_score', 0) for d in raw_data)
            avg_heat = total_heat / total if total > 0 else 0
            
            stats['platforms'][platform] = {
                'name': self.platform_config[platform]['name'],
                'total_count': total,
                'positive_count': positive,
                'negative_count': negative,
                'neutral_count': neutral,
                'positive_ratio': f"{positive / total * 100:.2f}%" if total > 0 else "0%",
                'avg_sentiment': sum(d['sentiment_score'] for d in raw_data) / total if total > 0 else 0,
                'total_heat': f"{total_heat:.2f}",  # 新增
                'avg_heat': f"{avg_heat:.2f}",  # 新增
            }
            
            stats['charts'].append(f"{platform}_sentiment_trend_{interval}.png")
        
        if len(platforms) > 1:
            stats['charts'].append(f"comparison_sentiment_trend_{interval}.png")
        
        # 保存统计报告
        report_path = os.path.join(output_dir, 'analysis_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info("\n" + "=" * 60)
        logger.info("分析完成！")
        logger.info(f"图表保存在: {output_dir}")
        logger.info(f"统计报告: {report_path}")
        logger.info("=" * 60)
        
        # 打印统计摘要
        for platform, platform_stats in stats['platforms'].items():
            logger.info(f"\n{platform_stats['name']}:")
            logger.info(f"  总数: {platform_stats['total_count']}")
            logger.info(f"  正面: {platform_stats['positive_count']} ({platform_stats['positive_ratio']})")
            logger.info(f"  负面: {platform_stats['negative_count']}")
            logger.info(f"  平均得分: {platform_stats['avg_sentiment']:.4f}")
            logger.info(f"  总热度: {platform_stats['total_heat']}")
            logger.info(f"  平均热度: {platform_stats['avg_heat']}")
        
        return stats


# 便捷函数
async def analyze_sentiment_trends(
    platforms: List[str] = ['zhihu', 'xhs', 'tieba'],
    keywords: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = 'day',
    content_type: str = 'all',
    output_dir: str = './sentiment_analysis_charts'
) -> Dict[str, Any]:
    """
    便捷函数：执行情感趋势分析
    
    Args:
        platforms: 平台列表 ['zhihu', 'xhs', 'tieba']
        keywords: 关键词列表，如 ['产品', '服务']
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        interval: 时间间隔 'day'/'week'/'month'
        content_type: 'post'/'comment'/'all'
        output_dir: 输出目录
    
    Returns:
        分析统计结果
    """
    analyzer = SentimentDataAnalyzer()
    return await analyzer.analyze_and_visualize(
        platforms=platforms,
        keywords=keywords,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        content_type=content_type,
        output_dir=output_dir
    )
