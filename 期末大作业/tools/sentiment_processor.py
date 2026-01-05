# -*- coding: utf-8 -*-
"""
情感分析数据处理器模块
负责从数据库读取数据、执行情感分析、更新数据库
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from contextlib import asynccontextmanager

from database.db_session import get_session
from database.models import (
    ZhihuContent, ZhihuComment,
    XhsNote, XhsNoteComment,
    TiebaNote, TiebaComment
)
from tools.sentiment_analyzer import get_sentiment_analyzer
from tools.utils import logger


class SentimentProcessor:
    """
    情感分析处理器
    负责协调数据读取、情感分析和结果存储
    """

    def __init__(self, batch_size: int = 100, overwrite: bool = False):
        """
        初始化处理器
        
        Args:
            batch_size: 批量处理的大小
            overwrite: 是否覆盖已有的情感分析结果
        """
        self.batch_size = batch_size
        self.overwrite = overwrite
        self.analyzer = get_sentiment_analyzer()
        
        # 平台配置映射
        self.platform_config = {
            'zhihu': {
                'content_model': ZhihuContent,
                'comment_model': ZhihuComment,
                'content_text_fields': ['title', 'desc', 'content_text'],
                'comment_text_field': 'content',
                'content_id_field': 'content_id',
            },
            'xhs': {
                'content_model': XhsNote,
                'comment_model': XhsNoteComment,
                'content_text_fields': ['title', 'desc'],
                'comment_text_field': 'content',
                'content_id_field': 'note_id',
            },
            'tieba': {
                'content_model': TiebaNote,
                'comment_model': TiebaComment,
                'content_text_fields': ['title', 'desc'],
                'comment_text_field': 'content',
                'content_id_field': 'note_id',
            }
        }

    def _get_merged_text(self, record: Any, text_fields: List[str]) -> str:
        """
        从记录中提取并合并多个文本字段
        
        Args:
            record: 数据库记录对象
            text_fields: 要合并的字段名列表
            
        Returns:
            合并后的文本
        """
        texts = [getattr(record, field, '') for field in text_fields]
        return self.analyzer.merge_texts(*texts)

    async def _process_content_batch(
        self,
        platform: str,
        records: List[Any]
    ) -> Dict[str, Any]:
        """
        批量处理内容(帖子/笔记)的情感分析
        
        Args:
            platform: 平台名称
            records: 记录列表
            
        Returns:
            处理统计信息
        """
        if not records:
            return {'processed': 0, 'success': 0, 'failed': 0}

        config = self.platform_config[platform]
        text_fields = config['content_text_fields']
        
        # 提取文本
        texts = [self._get_merged_text(record, text_fields) for record in records]
        
        # 批量分析（传递平台信息以使用推荐模型）
        results = await self.analyzer.analyze_batch(texts, platform=platform)
        
        # 更新记录
        success_count = 0
        failed_count = 0
        current_ts = int(time.time() * 1000)
        
        for record, result in zip(records, results):
            try:
                record.sentiment_score = str(result['score'])
                record.sentiment_label = result['label']
                record.sentiment_confidence = str(result['confidence'])
                record.analyzed_at = current_ts
                success_count += 1
            except Exception as e:
                logger.error(f"更新记录失败: {e}")
                failed_count += 1
        
        return {
            'processed': len(records),
            'success': success_count,
            'failed': failed_count
        }

    async def _process_comment_batch(
        self,
        platform: str,
        records: List[Any]
    ) -> Dict[str, Any]:
        """
        批量处理评论的情感分析
        
        Args:
            platform: 平台名称
            records: 记录列表
            
        Returns:
            处理统计信息
        """
        if not records:
            return {'processed': 0, 'success': 0, 'failed': 0}

        config = self.platform_config[platform]
        text_field = config['comment_text_field']
        
        # 提取文本
        texts = [getattr(record, text_field, '') for record in records]
        
        # 批量分析（传递平台信息以使用推荐模型）
        results = await self.analyzer.analyze_batch(texts, platform=platform)
        
        # 更新记录
        success_count = 0
        failed_count = 0
        current_ts = int(time.time() * 1000)
        
        for record, result in zip(records, results):
            try:
                record.sentiment_score = str(result['score'])
                record.sentiment_label = result['label']
                record.sentiment_confidence = str(result['confidence'])
                record.analyzed_at = current_ts
                success_count += 1
            except Exception as e:
                logger.error(f"更新记录失败: {e}")
                failed_count += 1
        
        return {
            'processed': len(records),
            'success': success_count,
            'failed': failed_count
        }

    async def process_platform_content(self, platform: str) -> Dict[str, Any]:
        """
        处理指定平台的内容(帖子/笔记)情感分析
        
        Args:
            platform: 平台名称 (zhihu/xhs/tieba)
            
        Returns:
            处理统计信息
        """
        logger.info(f"开始分析 {platform} 平台的内容...")
        
        if platform not in self.platform_config:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = self.platform_config[platform]
        model = config['content_model']
        
        total_stats = {'processed': 0, 'success': 0, 'failed': 0}
        
        async with get_session() as session:
            # 查询记录：如果 overwrite=True，查询所有记录；否则只查未分析的
            if self.overwrite:
                stmt = select(model)
                result = await session.execute(stmt)
                all_records = result.scalars().all()
                logger.info(f"找到 {len(all_records)} 条内容记录 [覆盖模式]")
            else:
                stmt = select(model).where(model.sentiment_label == None)
                result = await session.execute(stmt)
                all_records = result.scalars().all()
                logger.info(f"找到 {len(all_records)} 条未分析的内容记录")
            
            total_count = len(all_records)
            
            if total_count == 0:
                return total_stats
            
            # 分批处理
            for i in range(0, total_count, self.batch_size):
                batch = all_records[i:i + self.batch_size]
                batch_stats = await self._process_content_batch(platform, batch)
                
                # 更新统计
                total_stats['processed'] += batch_stats['processed']
                total_stats['success'] += batch_stats['success']
                total_stats['failed'] += batch_stats['failed']
                
                # 提交当前批次
                await session.commit()
                
                logger.info(
                    f"进度: {min(i + self.batch_size, total_count)}/{total_count} "
                    f"成功: {batch_stats['success']} 失败: {batch_stats['failed']}"
                )
        
        logger.info(f"{platform} 内容分析完成: {total_stats}")
        return total_stats

    async def process_platform_comments(self, platform: str) -> Dict[str, Any]:
        """
        处理指定平台的评论情感分析
        
        Args:
            platform: 平台名称 (zhihu/xhs/tieba)
            
        Returns:
            处理统计信息
        """
        logger.info(f"开始分析 {platform} 平台的评论...")
        
        if platform not in self.platform_config:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = self.platform_config[platform]
        model = config['comment_model']
        
        total_stats = {'processed': 0, 'success': 0, 'failed': 0}
        
        async with get_session() as session:
            # 查询记录：如果 overwrite=True，查询所有记录；否则只查未分析的
            if self.overwrite:
                stmt = select(model)
                result = await session.execute(stmt)
                all_records = result.scalars().all()
                logger.info(f"找到 {len(all_records)} 条评论记录 [覆盖模式]")
            else:
                stmt = select(model).where(model.sentiment_label == None)
                result = await session.execute(stmt)
                all_records = result.scalars().all()
                logger.info(f"找到 {len(all_records)} 条未分析的评论记录")
            
            total_count = len(all_records)
            
            if total_count == 0:
                return total_stats
            
            # 分批处理
            for i in range(0, total_count, self.batch_size):
                batch = all_records[i:i + self.batch_size]
                batch_stats = await self._process_comment_batch(platform, batch)
                
                # 更新统计
                total_stats['processed'] += batch_stats['processed']
                total_stats['success'] += batch_stats['success']
                total_stats['failed'] += batch_stats['failed']
                
                # 提交当前批次
                await session.commit()
                
                logger.info(
                    f"进度: {min(i + self.batch_size, total_count)}/{total_count} "
                    f"成功: {batch_stats['success']} 失败: {batch_stats['failed']}"
                )
        
        logger.info(f"{platform} 评论分析完成: {total_stats}")
        return total_stats

    async def process_platform(
        self,
        platform: str,
        content_type: str = 'all'
    ) -> Dict[str, Any]:
        """
        处理指定平台的情感分析
        
        Args:
            platform: 平台名称 (zhihu/xhs/tieba/all)
            content_type: 内容类型 (post/comment/all)
            
        Returns:
            处理统计信息
        """
        if platform not in self.platform_config:
            raise ValueError(f"不支持的平台: {platform}")
        
        stats = {
            'platform': platform,
            'content_type': content_type,
            'content_stats': None,
            'comment_stats': None,
            'total_processed': 0,
            'total_success': 0,
            'total_failed': 0
        }
        
        # 处理内容
        if content_type in ['post', 'all']:
            content_stats = await self.process_platform_content(platform)
            stats['content_stats'] = content_stats
            stats['total_processed'] += content_stats['processed']
            stats['total_success'] += content_stats['success']
            stats['total_failed'] += content_stats['failed']
        
        # 处理评论
        if content_type in ['comment', 'all']:
            comment_stats = await self.process_platform_comments(platform)
            stats['comment_stats'] = comment_stats
            stats['total_processed'] += comment_stats['processed']
            stats['total_success'] += comment_stats['success']
            stats['total_failed'] += comment_stats['failed']
        
        return stats

    async def process_all_platforms(
        self,
        content_type: str = 'all'
    ) -> Dict[str, Any]:
        """
        处理所有平台的情感分析
        
        Args:
            content_type: 内容类型 (post/comment/all)
            
        Returns:
            所有平台的处理统计信息
        """
        all_stats = {
            'platforms': [],
            'total_processed': 0,
            'total_success': 0,
            'total_failed': 0
        }
        
        for platform in ['zhihu', 'xhs', 'tieba']:
            try:
                stats = await self.process_platform(platform, content_type)
                all_stats['platforms'].append(stats)
                all_stats['total_processed'] += stats['total_processed']
                all_stats['total_success'] += stats['total_success']
                all_stats['total_failed'] += stats['total_failed']
            except Exception as e:
                logger.error(f"处理平台 {platform} 时出错: {e}")
        
        return all_stats


# 创建全局单例
_sentiment_processor = None


def get_sentiment_processor(batch_size: int = 100, overwrite: bool = False) -> SentimentProcessor:
    """
    获取情感分析处理器单例
    
    Args:
        batch_size: 批量处理大小
        overwrite: 是否覆盖已有的情感分析结果
        
    Returns:
        SentimentProcessor 实例
    """
    global _sentiment_processor
    if _sentiment_processor is None or _sentiment_processor.overwrite != overwrite:
        _sentiment_processor = SentimentProcessor(batch_size, overwrite)
    return _sentiment_processor
