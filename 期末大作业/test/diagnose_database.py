# -*- coding: utf-8 -*-
"""
数据库诊断脚本 - 检查情感分析数据情况
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, func, and_, or_
from database.db_session import get_session
from database.models import (
    ZhihuContent, ZhihuComment,
    XhsNote, XhsNoteComment,
    TiebaNote, TiebaComment
)
from tools.utils import logger


async def check_platform_data(platform_name: str, content_model, comment_model, keywords=None):
    """检查指定平台的数据情况"""
    logger.info("=" * 60)
    logger.info(f"检查平台: {platform_name}")
    logger.info("=" * 60)
    
    async with get_session() as session:
        # 1. 总数据量
        content_count = await session.execute(select(func.count()).select_from(content_model))
        total_content = content_count.scalar()
        
        comment_count = await session.execute(select(func.count()).select_from(comment_model))
        total_comment = comment_count.scalar()
        
        logger.info(f"📊 数据总量:")
        logger.info(f"  帖子总数: {total_content}")
        logger.info(f"  评论总数: {total_comment}")
        
        # 2. 已分析数据量
        analyzed_content = await session.execute(
            select(func.count()).select_from(content_model).where(
                content_model.sentiment_label != None
            )
        )
        analyzed_content_count = analyzed_content.scalar()
        
        analyzed_comment = await session.execute(
            select(func.count()).select_from(comment_model).where(
                comment_model.sentiment_label != None
            )
        )
        analyzed_comment_count = analyzed_comment.scalar()
        
        logger.info(f"\n🔍 已分析数据:")
        logger.info(f"  已分析帖子: {analyzed_content_count} ({analyzed_content_count/total_content*100:.1f}%)" if total_content > 0 else "  已分析帖子: 0")
        logger.info(f"  已分析评论: {analyzed_comment_count} ({analyzed_comment_count/total_comment*100:.1f}%)" if total_comment > 0 else "  已分析评论: 0")
        
        # 3. 情感分布
        if analyzed_content_count > 0 or analyzed_comment_count > 0:
            # 帖子情感分布
            if analyzed_content_count > 0:
                positive_content = await session.execute(
                    select(func.count()).select_from(content_model).where(
                        content_model.sentiment_label == 'positive'
                    )
                )
                negative_content = await session.execute(
                    select(func.count()).select_from(content_model).where(
                        content_model.sentiment_label == 'negative'
                    )
                )
                neutral_content = await session.execute(
                    select(func.count()).select_from(content_model).where(
                        content_model.sentiment_label == 'neutral'
                    )
                )
                
                logger.info(f"\n😊 帖子情感分布:")
                logger.info(f"  正面: {positive_content.scalar()}")
                logger.info(f"  负面: {negative_content.scalar()}")
                logger.info(f"  中性: {neutral_content.scalar()}")
            
            # 评论情感分布
            if analyzed_comment_count > 0:
                positive_comment = await session.execute(
                    select(func.count()).select_from(comment_model).where(
                        comment_model.sentiment_label == 'positive'
                    )
                )
                negative_comment = await session.execute(
                    select(func.count()).select_from(comment_model).where(
                        comment_model.sentiment_label == 'negative'
                    )
                )
                neutral_comment = await session.execute(
                    select(func.count()).select_from(comment_model).where(
                        comment_model.sentiment_label == 'neutral'
                    )
                )
                
                logger.info(f"\n💬 评论情感分布:")
                logger.info(f"  正面: {positive_comment.scalar()}")
                logger.info(f"  负面: {negative_comment.scalar()}")
                logger.info(f"  中性: {neutral_comment.scalar()}")
        
        # 4. 关键词匹配检查
        if keywords:
            logger.info(f"\n🔎 关键词匹配检查: {keywords}")
            
            # 检查帖子（根据不同平台的字段）
            if platform_name == "知乎":
                text_fields = ['title', 'desc', 'content_text']
            elif platform_name == "小红书":
                text_fields = ['title', 'desc']
            elif platform_name == "贴吧":
                text_fields = ['title', 'desc']
            else:
                text_fields = []
            
            # 帖子关键词匹配
            if text_fields:
                keyword_conditions = []
                for kw in keywords:
                    field_conditions = [getattr(content_model, field).contains(kw) for field in text_fields if hasattr(content_model, field)]
                    if field_conditions:
                        keyword_conditions.append(or_(*field_conditions))
                
                if keyword_conditions:
                    # 总匹配数
                    total_match = await session.execute(
                        select(func.count()).select_from(content_model).where(
                            or_(*keyword_conditions)
                        )
                    )
                    total_match_count = total_match.scalar()
                    
                    # 已分析的匹配数
                    analyzed_match = await session.execute(
                        select(func.count()).select_from(content_model).where(
                            and_(
                                or_(*keyword_conditions),
                                content_model.sentiment_label != None
                            )
                        )
                    )
                    analyzed_match_count = analyzed_match.scalar()
                    
                    logger.info(f"  帖子匹配: {total_match_count} 条")
                    logger.info(f"  已分析帖子匹配: {analyzed_match_count} 条")
            
            # 评论关键词匹配
            comment_field = 'content'
            if hasattr(comment_model, comment_field):
                keyword_conditions = [getattr(comment_model, comment_field).contains(kw) for kw in keywords]
                
                # 总匹配数
                total_match = await session.execute(
                    select(func.count()).select_from(comment_model).where(
                        or_(*keyword_conditions)
                    )
                )
                total_match_count = total_match.scalar()
                
                # 已分析的匹配数
                analyzed_match = await session.execute(
                    select(func.count()).select_from(comment_model).where(
                        and_(
                            or_(*keyword_conditions),
                            comment_model.sentiment_label != None
                        )
                    )
                )
                analyzed_match_count = analyzed_match.scalar()
                
                logger.info(f"  评论匹配: {total_match_count} 条")
                logger.info(f"  已分析评论匹配: {analyzed_match_count} 条")
        
        # 5. 未分析数据建议
        if total_content > 0 or total_comment > 0:
            unanalyzed_content = total_content - analyzed_content_count
            unanalyzed_comment = total_comment - analyzed_comment_count
            
            if unanalyzed_content > 0 or unanalyzed_comment > 0:
                logger.info(f"\n💡 建议:")
                if unanalyzed_content > 0:
                    logger.info(f"  有 {unanalyzed_content} 条帖子未分析，可运行:")
                    logger.info(f"  uv run main.py --sentiment {platform_name.lower()} --sentiment-type post")
                if unanalyzed_comment > 0:
                    logger.info(f"  有 {unanalyzed_comment} 条评论未分析，可运行:")
                    logger.info(f"  uv run main.py --sentiment {platform_name.lower()} --sentiment-type comment")
        else:
            logger.info(f"\n⚠️  该平台没有任何数据，请先爬取数据")


async def main():
    """主函数"""
    logger.info("\n" + "🔍 MediaCrawler 数据库诊断工具")
    logger.info("=" * 60)
    
    # 检查关键词（可自定义）
    keywords = ['台湾', '台海']
    
    # 检查知乎
    await check_platform_data(
        "知乎",
        ZhihuContent,
        ZhihuComment,
        keywords
    )
    
    # 检查小红书
    await check_platform_data(
        "小红书",
        XhsNote,
        XhsNoteComment,
        keywords
    )
    
    # 检查贴吧
    await check_platform_data(
        "贴吧",
        TiebaNote,
        TiebaComment,
        keywords
    )
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 诊断完成")
    logger.info("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
