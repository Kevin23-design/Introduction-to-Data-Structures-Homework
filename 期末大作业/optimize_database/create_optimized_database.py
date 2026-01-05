"""
创建优化后的数据库表结构
执行此脚本将在目标数据库中创建4张表: users, posts, comments, sentiment_analysis
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from database.optimized_models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_optimized_database(db_url: str):
    """
    创建优化后的数据库结构
    
    Args:
        db_url: 数据库连接URL
    """
    logger.info("=" * 50)
    logger.info("创建优化后的数据库结构")
    logger.info("=" * 50)
    
    # 创建引擎
    engine = create_async_engine(db_url, echo=True)
    
    try:
        # 创建所有表
        async with engine.begin() as conn:
            logger.info("\n开始创建表...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ 表创建完成!")
        
        # 显示创建的表
        logger.info("\n📋 创建的表:")
        for table_name in Base.metadata.tables.keys():
            logger.info(f"  - {table_name}")
        
        logger.info("\n" + "=" * 50)
        logger.info("数据库结构创建成功!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ 创建失败: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """主函数"""
    
    # 目标数据库配置
    # 注意: 需要先手动创建数据库 media_crawler_optimized
    # CREATE DATABASE media_crawler_optimized CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    
    DB_URL = "mysql+aiomysql://root:123456@localhost:3306/media_crawler_optimized"
    
    await create_optimized_database(DB_URL)


if __name__ == "__main__":
    asyncio.run(main())
