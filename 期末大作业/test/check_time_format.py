# -*- coding: utf-8 -*-
"""
检查时间字段格式
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from database.db_session import get_session
from database.models import ZhihuContent, ZhihuComment, TiebaNote, TiebaComment, XhsNote, XhsNoteComment
from tools.utils import logger


async def check_time_formats():
    """检查各平台的时间字段格式"""
    async with get_session() as session:
        # 知乎帖子
        logger.info("=" * 60)
        logger.info("知乎帖子时间格式 (created_time):")
        result = await session.execute(
            select(ZhihuContent.created_time, ZhihuContent.title)
            .where(ZhihuContent.sentiment_label != None)
            .limit(3)
        )
        for time_val, title in result.all():
            logger.info(f"  {time_val} | {title[:30]}")
        
        # 知乎评论
        logger.info("\n知乎评论时间格式 (publish_time):")
        result = await session.execute(
            select(ZhihuComment.publish_time, ZhihuComment.content)
            .where(ZhihuComment.sentiment_label != None)
            .limit(3)
        )
        for time_val, content in result.all():
            logger.info(f"  {time_val} | {content[:30]}")
        
        # 贴吧帖子
        logger.info("\n=" * 60)
        logger.info("贴吧帖子时间格式 (publish_time):")
        result = await session.execute(
            select(TiebaNote.publish_time, TiebaNote.title)
            .where(TiebaNote.sentiment_label != None)
            .limit(3)
        )
        for time_val, title in result.all():
            logger.info(f"  {time_val} | {title[:30]}")
        
        # 贴吧评论
        logger.info("\n贴吧评论时间格式 (publish_time):")
        result = await session.execute(
            select(TiebaComment.publish_time, TiebaComment.content)
            .where(TiebaComment.sentiment_label != None)
            .limit(3)
        )
        for time_val, content in result.all():
            logger.info(f"  {time_val} | {content[:30]}")
        
        # 小红书帖子
        logger.info("\n=" * 60)
        logger.info("小红书帖子时间格式 (time):")
        result = await session.execute(
            select(XhsNote.time, XhsNote.title)
            .where(XhsNote.sentiment_label != None)
            .limit(3)
        )
        for time_val, title in result.all():
            logger.info(f"  {time_val} | {title[:30]}")
        
        # 小红书评论
        logger.info("\n小红书评论时间格式 (create_time):")
        result = await session.execute(
            select(XhsNoteComment.create_time, XhsNoteComment.content)
            .where(XhsNoteComment.sentiment_label != None)
            .limit(3)
        )
        for time_val, content in result.all():
            logger.info(f"  {time_val} | {content[:30]}")
        
        logger.info("\n" + "=" * 60)


if __name__ == '__main__':
    asyncio.run(check_time_formats())
