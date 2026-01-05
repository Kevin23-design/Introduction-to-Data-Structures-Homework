# -*- coding: utf-8 -*-
"""
情感分析功能测试脚本
用于验证情感分析器的基本功能
"""
import asyncio
from tools.sentiment_analyzer import get_sentiment_analyzer


async def test_sentiment_analyzer():
    """测试情感分析器的基本功能"""
    
    print("=" * 60)
    print("情感分析器功能测试")
    print("=" * 60)
    
    analyzer = get_sentiment_analyzer()
    
    # 测试用例
    test_cases = [
        ("这个产品真的太好用了，强烈推荐！", "正面情感"),
        ("质量太差了，非常失望，不推荐购买", "负面情感"),
        ("还行吧，一般般", "中性情感"),
        ("今天天气不错", "中性/轻微正面"),
        ("服务态度恶劣，再也不来了！", "负面情感"),
        ("哇，这个功能太棒了，简直完美！", "正面情感"),
        ("", "空文本测试"),
        ("内容很丰富，但是价格有点贵", "混合情感"),
    ]
    
    print("\n单个文本分析测试:")
    print("-" * 60)
    
    for text, expected in test_cases:
        result = await analyzer.analyze_text(text)
        
        print(f"\n文本: {text if text else '(空)'}")
        print(f"预期: {expected}")
        print(f"得分: {result['score']:.4f} (原始: {result['raw_score']:.4f})")
        print(f"标签: {result['label']}")
        print(f"置信度: {result['confidence']:.4f}")
        if 'error' in result:
            print(f"错误: {result['error']}")
    
    # 测试批量分析
    print("\n\n批量分析测试:")
    print("-" * 60)
    
    batch_texts = [
        "这个地方环境优美，服务周到",
        "价格昂贵，性价比不高",
        "普通的产品，没什么特别的",
    ]
    
    batch_results = await analyzer.analyze_batch(batch_texts)
    
    for text, result in zip(batch_texts, batch_results):
        print(f"\n文本: {text}")
        print(f"标签: {result['label']} | 得分: {result['score']:.4f}")
    
    # 测试文本合并功能
    print("\n\n文本合并分析测试:")
    print("-" * 60)
    
    title = "北京旅游攻略"
    desc = "这次北京之行非常愉快"
    content = "景点很美，人也很友好，美食也很棒，强烈推荐大家来北京玩！"
    
    merged_result = await analyzer.analyze_merged_text(title, desc, content)
    
    print(f"标题: {title}")
    print(f"描述: {desc}")
    print(f"内容: {content}")
    print(f"\n合并后分析结果:")
    print(f"标签: {merged_result['label']}")
    print(f"得分: {merged_result['score']:.4f}")
    print(f"置信度: {merged_result['confidence']:.4f}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_sentiment_analyzer())
