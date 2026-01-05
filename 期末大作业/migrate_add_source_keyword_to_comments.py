# -*- coding: utf-8 -*-
"""
为评论表添加 source_keyword 字段的数据库迁移脚本
"""
import asyncio
from sqlalchemy import text
from database.db_session import get_session
from tools.utils import logger


async def add_source_keyword_to_comments():
    """为评论表添加 source_keyword 字段"""
    
    async with get_session() as session:
        # 要修改的评论表
        comment_tables = [
            'xhs_note_comment',
            'tieba_comment',
            'zhihu_comment'
        ]
        
        for table_name in comment_tables:
            try:
                # 检查表是否存在
                check_table_query = text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table_name}'
                """)
                result = await session.execute(check_table_query)
                table_exists = result.scalar() > 0
                
                if not table_exists:
                    logger.warning(f"表 {table_name} 不存在，跳过")
                    continue
                
                # 检查字段是否已存在
                check_column_query = text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table_name}' 
                    AND column_name = 'source_keyword'
                """)
                result = await session.execute(check_column_query)
                column_exists = result.scalar() > 0
                
                if column_exists:
                    logger.info(f"✓ 表 {table_name} 的 source_keyword 字段已存在")
                    continue
                
                # 添加字段 (TEXT类型不支持DEFAULT,使用NULL)
                alter_query = text(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN source_keyword TEXT NULL
                """)
                await session.execute(alter_query)
                await session.commit()
                
                logger.info(f"✓ 成功为表 {table_name} 添加 source_keyword 字段")
                
            except Exception as e:
                logger.error(f"✗ 处理表 {table_name} 时出错: {e}")
                await session.rollback()


async def update_existing_comments_with_source_keyword():
    """
    为现有评论填充 source_keyword
    从关联的 note/content 表中读取 source_keyword
    """
    async with get_session() as session:
        try:
            # 小红书评论
            logger.info("正在更新小红书评论的 source_keyword...")
            xhs_update = text("""
                UPDATE xhs_note_comment c
                JOIN xhs_note n ON c.note_id = n.note_id
                SET c.source_keyword = n.source_keyword
                WHERE c.source_keyword = '' OR c.source_keyword IS NULL
            """)
            result = await session.execute(xhs_update)
            await session.commit()
            logger.info(f"✓ 更新了 {result.rowcount} 条小红书评论")
            
            # 贴吧评论
            logger.info("正在更新贴吧评论的 source_keyword...")
            tieba_update = text("""
                UPDATE tieba_comment c
                JOIN tieba_note n ON c.note_id = n.note_id
                SET c.source_keyword = n.source_keyword
                WHERE c.source_keyword = '' OR c.source_keyword IS NULL
            """)
            result = await session.execute(tieba_update)
            await session.commit()
            logger.info(f"✓ 更新了 {result.rowcount} 条贴吧评论")
            
            # 知乎评论
            logger.info("正在更新知乎评论的 source_keyword...")
            zhihu_update = text("""
                UPDATE zhihu_comment c
                JOIN zhihu_content n ON c.content_id = n.content_id
                SET c.source_keyword = n.source_keyword
                WHERE c.source_keyword = '' OR c.source_keyword IS NULL
            """)
            result = await session.execute(zhihu_update)
            await session.commit()
            logger.info(f"✓ 更新了 {result.rowcount} 条知乎评论")
            
        except Exception as e:
            logger.error(f"✗ 更新现有评论时出错: {e}")
            await session.rollback()


async def verify_migration():
    """验证迁移结果"""
    logger.info("\n" + "=" * 60)
    logger.info("验证迁移结果")
    logger.info("=" * 60)
    
    async with get_session() as session:
        comment_tables = [
            ('xhs_note_comment', '小红书'),
            ('tieba_comment', '贴吧'),
            ('zhihu_comment', '知乎')
        ]
        
        for table_name, platform_name in comment_tables:
            try:
                # 检查字段是否存在
                check_query = text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table_name}' 
                    AND column_name = 'source_keyword'
                """)
                result = await session.execute(check_query)
                exists = result.scalar() > 0
                
                if exists:
                    # 统计有 source_keyword 的记录
                    count_query = text(f"""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN source_keyword != '' AND source_keyword IS NOT NULL THEN 1 END) as with_keyword
                        FROM {table_name}
                    """)
                    result = await session.execute(count_query)
                    row = result.fetchone()
                    logger.info(f"✓ {platform_name}评论表: 总数={row[0]}, 有关键词={row[1]}")
                else:
                    logger.warning(f"✗ {platform_name}评论表: source_keyword 字段不存在")
                    
            except Exception as e:
                logger.error(f"✗ 验证 {platform_name}评论表时出错: {e}")


async def main():
    logger.info("=" * 60)
    logger.info("开始迁移: 为评论表添加 source_keyword 字段")
    logger.info("=" * 60)
    
    # 步骤1: 添加字段
    await add_source_keyword_to_comments()
    
    # 步骤2: 填充现有数据
    logger.info("\n" + "=" * 60)
    logger.info("填充现有评论的 source_keyword")
    logger.info("=" * 60)
    await update_existing_comments_with_source_keyword()
    
    # 步骤3: 验证
    await verify_migration()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 迁移完成！")
    logger.info("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
