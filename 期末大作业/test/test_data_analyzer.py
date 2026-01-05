# -*- coding: utf-8 -*-
"""
数据分析器测试脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.data_analyzer import SentimentDataAnalyzer, analyze_sentiment_trends
from tools.utils import logger


async def test_basic_analysis():
    """测试基本的单平台分析"""
    logger.info("=" * 60)
    logger.info("测试1: 基本分析（知乎，最近30天，按天聚合）")
    logger.info("=" * 60)
    
    analyzer = SentimentDataAnalyzer()
    stats = await analyzer.analyze_and_visualize(
        platforms=['zhihu'],
        keywords=None,
        start_date=None,
        end_date=None,
        interval='day',
        content_type='all',
        output_dir='./test_output/basic'
    )
    
    logger.info(f"✓ 测试1完成，生成图表: {stats.get('charts', [])}")
    return stats


async def test_multi_platform():
    """测试多平台对比"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 多平台对比（所有平台，按周聚合）")
    logger.info("=" * 60)
    
    stats = await analyze_sentiment_trends(
        platforms=['zhihu', 'xhs', 'tieba'],
        keywords=None,
        start_date=None,
        end_date=None,
        interval='week',
        content_type='all',
        output_dir='./test_output/multi_platform'
    )
    
    logger.info(f"✓ 测试2完成，生成图表: {stats.get('charts', [])}")
    return stats


async def test_keyword_filter():
    """测试关键词过滤"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 关键词过滤（产品、服务）")
    logger.info("=" * 60)
    
    stats = await analyze_sentiment_trends(
        platforms=['zhihu', 'xhs'],
        keywords=['产品', '服务'],
        start_date=None,
        end_date=None,
        interval='day',
        content_type='all',
        output_dir='./test_output/keyword_filter'
    )
    
    logger.info(f"✓ 测试3完成，生成图表: {stats.get('charts', [])}")
    return stats


async def test_date_range():
    """测试指定日期范围"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 指定日期范围（2024-01-01 至 2024-01-31）")
    logger.info("=" * 60)
    
    stats = await analyze_sentiment_trends(
        platforms=['xhs'],
        keywords=None,
        start_date='2024-01-01',
        end_date='2024-01-31',
        interval='day',
        content_type='all',
        output_dir='./test_output/date_range'
    )
    
    logger.info(f"✓ 测试4完成，生成图表: {stats.get('charts', [])}")
    return stats


async def test_content_type():
    """测试内容类型过滤"""
    logger.info("\n" + "=" * 60)
    logger.info("测试5: 只分析帖子（不包括评论）")
    logger.info("=" * 60)
    
    stats = await analyze_sentiment_trends(
        platforms=['zhihu'],
        keywords=None,
        start_date=None,
        end_date=None,
        interval='day',
        content_type='post',
        output_dir='./test_output/content_type'
    )
    
    logger.info(f"✓ 测试5完成，生成图表: {stats.get('charts', [])}")
    return stats


async def test_comprehensive():
    """测试综合场景"""
    logger.info("\n" + "=" * 60)
    logger.info("测试6: 综合测试（多平台+关键词+日期范围+按月聚合）")
    logger.info("=" * 60)
    
    stats = await analyze_sentiment_trends(
        platforms=['zhihu', 'xhs', 'tieba'],
        keywords=['用户', '体验'],
        start_date='2024-01-01',
        end_date='2024-03-31',
        interval='month',
        content_type='all',
        output_dir='./test_output/comprehensive'
    )
    
    logger.info(f"✓ 测试6完成，生成图表: {stats.get('charts', [])}")
    return stats


async def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "🚀 开始数据分析器功能测试")
    logger.info("=" * 60)
    
    test_results = []
    
    try:
        # 测试1：基本分析
        result1 = await test_basic_analysis()
        test_results.append(('基本分析', result1))
    except Exception as e:
        logger.error(f"✗ 测试1失败: {e}")
        test_results.append(('基本分析', None))
    
    try:
        # 测试2：多平台对比
        result2 = await test_multi_platform()
        test_results.append(('多平台对比', result2))
    except Exception as e:
        logger.error(f"✗ 测试2失败: {e}")
        test_results.append(('多平台对比', None))
    
    try:
        # 测试3：关键词过滤
        result3 = await test_keyword_filter()
        test_results.append(('关键词过滤', result3))
    except Exception as e:
        logger.error(f"✗ 测试3失败: {e}")
        test_results.append(('关键词过滤', None))
    
    try:
        # 测试4：日期范围
        result4 = await test_date_range()
        test_results.append(('日期范围', result4))
    except Exception as e:
        logger.error(f"✗ 测试4失败: {e}")
        test_results.append(('日期范围', None))
    
    try:
        # 测试5：内容类型
        result5 = await test_content_type()
        test_results.append(('内容类型', result5))
    except Exception as e:
        logger.error(f"✗ 测试5失败: {e}")
        test_results.append(('内容类型', None))
    
    try:
        # 测试6：综合测试
        result6 = await test_comprehensive()
        test_results.append(('综合测试', result6))
    except Exception as e:
        logger.error(f"✗ 测试6失败: {e}")
        test_results.append(('综合测试', None))
    
    # 打印测试总结
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试总结")
    logger.info("=" * 60)
    
    success_count = sum(1 for _, result in test_results if result is not None)
    total_count = len(test_results)
    
    for test_name, result in test_results:
        if result:
            logger.info(f"✓ {test_name}: 成功")
            logger.info(f"    - 图表: {', '.join(result.get('charts', []))}")
            
            # 打印各平台统计
            for platform, stats in result.get('platforms', {}).items():
                logger.info(f"    - {stats['name']}: 总数{stats['total_count']}, "
                          f"正面{stats['positive_ratio']}, "
                          f"平均{stats['avg_sentiment']:.4f}")
        else:
            logger.info(f"✗ {test_name}: 失败")
    
    logger.info("=" * 60)
    logger.info(f"测试完成: {success_count}/{total_count} 通过")
    logger.info("=" * 60)


async def quick_test():
    """快速测试（仅测试基本功能）"""
    logger.info("🚀 快速测试：基本数据分析功能")
    logger.info("=" * 60)
    
    try:
        stats = await analyze_sentiment_trends(
            platforms=['zhihu'],
            keywords=None,
            start_date=None,
            end_date=None,
            interval='day',
            content_type='all',
            output_dir='./quick_test_output'
        )
        
        logger.info("\n✓ 快速测试成功！")
        logger.info(f"生成图表: {stats.get('charts', [])}")
        
        for platform, platform_stats in stats.get('platforms', {}).items():
            logger.info(f"\n{platform_stats['name']} 统计:")
            logger.info(f"  总数: {platform_stats['total_count']}")
            logger.info(f"  正面: {platform_stats['positive_count']} ({platform_stats['positive_ratio']})")
            logger.info(f"  负面: {platform_stats['negative_count']}")
            logger.info(f"  平均得分: {platform_stats['avg_sentiment']:.4f}")
            
    except Exception as e:
        logger.error(f"✗ 快速测试失败: {e}", exc_info=True)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据分析器测试脚本')
    parser.add_argument('--quick', action='store_true', help='快速测试（仅基本功能）')
    parser.add_argument('--full', action='store_true', help='完整测试（所有场景）')
    
    args = parser.parse_args()
    
    if args.full:
        asyncio.run(run_all_tests())
    elif args.quick:
        asyncio.run(quick_test())
    else:
        # 默认运行快速测试
        logger.info("提示: 使用 --quick 进行快速测试，或 --full 进行完整测试")
        asyncio.run(quick_test())
