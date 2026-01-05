# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加情感分析字段
用于为现有的 MySQL 数据库添加情感分析相关字段
"""
import asyncio
import sys
from sqlalchemy import text

sys.path.append('.')
from database.db_session import get_session
from tools.utils import logger


async def add_sentiment_fields():
    """为所有相关表添加情感分析字段"""
    
    # 定义需要添加字段的表
    tables = [
        'zhihu_content',
        'zhihu_comment',
        'xhs_note',
        'xhs_note_comment',
        'tieba_note',
        'tieba_comment'
    ]
    
    # 要添加的字段
    fields_sql = """
        ADD COLUMN sentiment_score TEXT,
        ADD COLUMN sentiment_label VARCHAR(20),
        ADD COLUMN sentiment_confidence TEXT,
        ADD COLUMN analyzed_at BIGINT
    """
    
    logger.info("=" * 60)
    logger.info("开始数据库迁移：添加情感分析字段")
    logger.info("=" * 60)
    
    async with get_session() as session:
        success_count = 0
        failed_count = 0
        
        for table in tables:
            try:
                # 先检查表是否存在
                check_table_sql = f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table}'
                """
                result = await session.execute(text(check_table_sql))
                table_exists = result.scalar()
                
                if not table_exists:
                    logger.warning(f"表 {table} 不存在，跳过")
                    continue
                
                # 检查字段是否已存在
                check_column_sql = f"""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table}' 
                    AND column_name = 'sentiment_label'
                """
                result = await session.execute(text(check_column_sql))
                column_exists = result.scalar()
                
                if column_exists:
                    logger.info(f"✓ 表 {table} 已有情感分析字段，跳过")
                    success_count += 1
                    continue
                
                # 添加字段
                alter_sql = f"ALTER TABLE {table} {fields_sql}"
                logger.info(f"正在为表 {table} 添加字段...")
                
                await session.execute(text(alter_sql))
                await session.commit()
                
                logger.info(f"✓ 表 {table} 添加字段成功")
                success_count += 1
                
            except Exception as e:
                logger.error(f"✗ 表 {table} 添加字段失败: {e}")
                failed_count += 1
                await session.rollback()
    
    logger.info("=" * 60)
    logger.info("数据库迁移完成！")
    logger.info(f"成功: {success_count} 个表")
    logger.info(f"失败: {failed_count} 个表")
    logger.info("=" * 60)
    
    if failed_count > 0:
        logger.warning("部分表迁移失败，请检查错误信息")
        return False
    else:
        logger.info("所有表迁移成功！现在可以运行情感分析了")
        return True


async def verify_migration():
    """验证迁移是否成功"""
    
    logger.info("\n" + "=" * 60)
    logger.info("验证迁移结果...")
    logger.info("=" * 60)
    
    tables = [
        'zhihu_content',
        'zhihu_comment',
        'xhs_note',
        'xhs_note_comment',
        'tieba_note',
        'tieba_comment'
    ]
    
    async with get_session() as session:
        for table in tables:
            try:
                # 检查字段
                check_sql = f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table}' 
                    AND column_name IN ('sentiment_score', 'sentiment_label', 'sentiment_confidence', 'analyzed_at')
                    ORDER BY column_name
                """
                result = await session.execute(text(check_sql))
                columns = result.fetchall()
                
                if len(columns) == 4:
                    logger.info(f"✓ {table}: 所有字段存在")
                    for col_name, col_type in columns:
                        logger.info(f"  - {col_name}: {col_type}")
                else:
                    logger.warning(f"✗ {table}: 字段不完整（找到 {len(columns)}/4 个字段）")
                    
            except Exception as e:
                logger.error(f"✗ {table}: 验证失败 - {e}")
    
    logger.info("=" * 60)


async def main():
    """主函数"""
    try:
        # 执行迁移
        success = await add_sentiment_fields()
        
        # 验证迁移
        if success:
            await verify_migration()
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ 迁移完成！现在可以运行情感分析命令：")
            logger.info("  uv run main.py --sentiment zhihu --sentiment-type all")
            logger.info("=" * 60)
        else:
            logger.error("\n迁移过程中出现错误，请检查日志")
            
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
