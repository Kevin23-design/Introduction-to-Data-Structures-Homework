# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import asyncio
import sys
from typing import Optional

import cmd_arg
import config
from database import db
from base.base_crawler import AbstractCrawler
from media_platform.bilibili import BilibiliCrawler
from media_platform.douyin import DouYinCrawler
from media_platform.kuaishou import KuaishouCrawler
from media_platform.tieba import TieBaCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.xhs import XiaoHongShuCrawler
from media_platform.zhihu import ZhihuCrawler
from tools.async_file_writer import AsyncFileWriter
from tools.sentiment_processor import get_sentiment_processor
from tools.data_analyzer import analyze_sentiment_trends
from tools.utils import logger
from var import crawler_type_var


class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler,
        "dy": DouYinCrawler,
        "ks": KuaishouCrawler,
        "bili": BilibiliCrawler,
        "wb": WeiboCrawler,
        "tieba": TieBaCrawler,
        "zhihu": ZhihuCrawler,
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError(
                "Invalid Media Platform Currently only supported xhs or dy or ks or bili ..."
            )
        return crawler_class()


crawler: Optional[AbstractCrawler] = None


# persist-1<persist1@126.com>
# 原因：增加 --init_db 功能，用于数据库初始化。
# 副作用：无
# 回滚策略：还原此文件。
async def sentiment_analysis_entry(platform: str, content_type: str, overwrite: bool = False):
    """
    情感分析入口函数
    
    Args:
        platform: 平台名称 (zhihu/xhs/tieba/all)
        content_type: 内容类型 (post/comment/all)
        overwrite: 是否覆盖已有的分析结果
    """
    if overwrite:
        logger.info(f"开始情感分析 - 平台: {platform}, 类型: {content_type} [覆盖模式]")
    else:
        logger.info(f"开始情感分析 - 平台: {platform}, 类型: {content_type}")
    
    processor = get_sentiment_processor(batch_size=100, overwrite=overwrite)
    
    try:
        if platform == "all":
            # 处理所有平台
            stats = await processor.process_all_platforms(content_type)
            logger.info("=" * 50)
            logger.info("所有平台情感分析完成!")
            logger.info(f"总计处理: {stats['total_processed']} 条")
            logger.info(f"成功: {stats['total_success']} 条")
            logger.info(f"失败: {stats['total_failed']} 条")
            logger.info("=" * 50)
            
            # 打印各平台详情
            for platform_stats in stats['platforms']:
                logger.info(f"\n平台 {platform_stats['platform']}:")
                if platform_stats['content_stats']:
                    logger.info(f"  内容: {platform_stats['content_stats']}")
                if platform_stats['comment_stats']:
                    logger.info(f"  评论: {platform_stats['comment_stats']}")
        else:
            # 处理单个平台
            stats = await processor.process_platform(platform, content_type)
            logger.info("=" * 50)
            logger.info(f"平台 {platform} 情感分析完成!")
            logger.info(f"总计处理: {stats['total_processed']} 条")
            logger.info(f"成功: {stats['total_success']} 条")
            logger.info(f"失败: {stats['total_failed']} 条")
            logger.info("=" * 50)
            
            if stats['content_stats']:
                logger.info(f"内容统计: {stats['content_stats']}")
            if stats['comment_stats']:
                logger.info(f"评论统计: {stats['comment_stats']}")
                
    except Exception as e:
        logger.error(f"情感分析过程中发生错误: {e}", exc_info=True)
        raise


async def data_analysis_entry(
    platforms: list,
    keywords: Optional[list] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = 'day',
    content_type: str = 'all',
    output_dir: str = './sentiment_analysis_charts'
):
    """
    数据分析入口函数
    
    Args:
        platforms: 要分析的平台列表
        keywords: 关键词列表
        start_date: 开始日期
        end_date: 结束日期
        interval: 时间间隔
        content_type: 内容类型
        output_dir: 输出目录
    """
    try:
        logger.info("=" * 60)
        logger.info("开始情感趋势分析和可视化")
        logger.info(f"平台: {', '.join(platforms)}")
        logger.info(f"关键词: {keywords if keywords else '全部'}")
        logger.info(f"时间范围: {start_date or '30天前'} 至 {end_date or '今天'}")
        logger.info(f"时间间隔: {interval}")
        logger.info(f"内容类型: {content_type}")
        logger.info(f"输出目录: {output_dir}")
        logger.info("=" * 60)
        
        # 执行分析
        stats = await analyze_sentiment_trends(
            platforms=platforms,
            keywords=keywords,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            content_type=content_type,
            output_dir=output_dir
        )
        
        logger.info("\n分析完成！")
        logger.info(f"生成的图表:")
        for chart in stats.get('charts', []):
            logger.info(f"  - {chart}")
            
    except Exception as e:
        logger.error(f"数据分析过程中发生错误: {e}", exc_info=True)
        raise


async def main():
    # Init crawler
    global crawler

    # parse cmd
    args = await cmd_arg.parse_cmd()

    # init db
    if args.init_db:
        await db.init_db(args.init_db)
        print(f"Database {args.init_db} initialized successfully.")
        return  # Exit the main function cleanly

    # data analysis (trend visualization)
    if args.analyze_sentiment:
        logger.info("检测到数据分析参数，开始执行情感趋势分析...")
        await data_analysis_entry(
            platforms=args.analyze_platforms,
            keywords=args.analyze_keywords,
            start_date=args.start_date,
            end_date=args.end_date,
            interval=args.analyze_interval,
            content_type=args.analyze_content_type,
            output_dir=args.output_dir
        )
        return  # Exit after data analysis

    # sentiment analysis
    if args.sentiment:
        logger.info("检测到情感分析参数，开始执行情感分析...")
        await sentiment_analysis_entry(args.sentiment, args.sentiment_type, args.overwrite)
        return  # Exit after sentiment analysis

    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.start()

    # Generate wordcloud after crawling is complete
    # Only for JSON save mode
    if config.SAVE_DATA_OPTION == "json" and config.ENABLE_GET_WORDCLOUD:
        try:
            file_writer = AsyncFileWriter(
                platform=config.PLATFORM,
                crawler_type=crawler_type_var.get()
            )
            await file_writer.generate_wordcloud_from_comments()
        except Exception as e:
            print(f"Error generating wordcloud: {e}")


def cleanup():
    if crawler:
        # asyncio.run(crawler.close())
        pass
    if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
        asyncio.run(db.close())


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    finally:
        cleanup()
