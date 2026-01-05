"""
优化后数据库的查询工具
提供常用查询方法和统计分析功能
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.optimized_models import (
    User, Post, Comment, SentimentAnalysis,
    PlatformEnum, ContentTypeEnum, SentimentLabelEnum
)
import pandas as pd


class OptimizedDatabaseQuery:
    """优化后数据库的查询接口"""
    
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url, echo=False)
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def get_user_posts(
        self, 
        user_id: int,
        limit: int = 10
    ) -> List[Post]:
        """
        获取用户的所有帖子
        
        示例:
            posts = await query.get_user_posts(user_id=123, limit=10)
        """
        async with self.session_maker() as session:
            result = await session.execute(
                select(Post)
                .where(Post.user_id == user_id)
                .order_by(desc(Post.published_at))
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_post_comments(
        self,
        post_id: int,
        limit: int = 100
    ) -> List[Comment]:
        """
        获取帖子的所有评论
        
        示例:
            comments = await query.get_post_comments(post_id=456)
        """
        async with self.session_maker() as session:
            result = await session.execute(
                select(Comment)
                .where(Comment.post_id == post_id)
                .order_by(Comment.published_at)
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_platform_sentiment_stats(
        self,
        platform: Optional[PlatformEnum] = None
    ) -> Dict:
        """
        跨平台情感分布对比
        
        示例:
            # 获取所有平台的情感统计
            stats = await query.get_platform_sentiment_stats()
            
            # 获取特定平台的情感统计
            stats = await query.get_platform_sentiment_stats(platform=PlatformEnum.ZHIHU)
        """
        async with self.session_maker() as session:
            # 帖子情感统计
            query = (
                select(
                    Post.platform,
                    SentimentAnalysis.sentiment_label,
                    func.count(SentimentAnalysis.id).label('count')
                )
                .join(
                    SentimentAnalysis,
                    and_(
                        SentimentAnalysis.content_id == Post.id,
                        SentimentAnalysis.content_type == ContentTypeEnum.POST
                    )
                )
                .group_by(Post.platform, SentimentAnalysis.sentiment_label)
            )
            
            if platform:
                query = query.where(Post.platform == platform)
            
            result = await session.execute(query)
            rows = result.all()
            
            # 组织数据
            stats = {}
            for row in rows:
                platform_name = row.platform.value
                if platform_name not in stats:
                    stats[platform_name] = {
                        'positive': 0,
                        'neutral': 0,
                        'negative': 0,
                        'total': 0
                    }
                
                label = row.sentiment_label.value
                count = row.count
                stats[platform_name][label] = count
                stats[platform_name]['total'] += count
            
            return stats
    
    async def get_hot_posts(
        self,
        platform: Optional[PlatformEnum] = None,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict]:
        """
        获取热门帖子(按互动度排序)
        
        示例:
            # 获取所有平台最近7天的热门帖子
            hot_posts = await query.get_hot_posts(days=7, limit=10)
            
            # 获取小红书最近30天的热门帖子
            hot_posts = await query.get_hot_posts(
                platform=PlatformEnum.XHS,
                days=30,
                limit=20
            )
        """
        async with self.session_maker() as session:
            # 计算互动度: likes + comments + shares
            heat_score = (
                Post.likes_count + 
                Post.comments_count * 2 + 
                Post.shares_count * 3
            ).label('heat_score')
            
            query = (
                select(
                    Post.id,
                    Post.platform,
                    Post.title,
                    Post.likes_count,
                    Post.comments_count,
                    Post.shares_count,
                    Post.published_at,
                    User.nickname.label('author_nickname'),
                    heat_score
                )
                .join(User, Post.user_id == User.id)
                .where(
                    Post.published_at >= datetime.now() - timedelta(days=days)
                )
            )
            
            if platform:
                query = query.where(Post.platform == platform)
            
            query = query.order_by(desc('heat_score')).limit(limit)
            
            result = await session.execute(query)
            rows = result.all()
            
            return [
                {
                    'id': row.id,
                    'platform': row.platform.value,
                    'title': row.title,
                    'author': row.author_nickname,
                    'likes': row.likes_count,
                    'comments': row.comments_count,
                    'shares': row.shares_count,
                    'heat_score': row.heat_score,
                    'published_at': row.published_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                for row in rows
            ]
    
    async def get_user_activity(
        self,
        user_id: int
    ) -> Dict:
        """
        获取用户活跃度统计
        
        示例:
            activity = await query.get_user_activity(user_id=123)
        """
        async with self.session_maker() as session:
            # 用户基本信息
            user = await session.get(User, user_id)
            if not user:
                return None
            
            # 帖子数量
            result = await session.execute(
                select(func.count(Post.id)).where(Post.user_id == user_id)
            )
            post_count = result.scalar()
            
            # 评论数量
            result = await session.execute(
                select(func.count(Comment.id)).where(Comment.user_id == user_id)
            )
            comment_count = result.scalar()
            
            # 总获赞数
            result = await session.execute(
                select(func.sum(Post.likes_count)).where(Post.user_id == user_id)
            )
            total_likes = result.scalar() or 0
            
            # 最近发帖时间
            result = await session.execute(
                select(func.max(Post.published_at)).where(Post.user_id == user_id)
            )
            last_post_time = result.scalar()
            
            return {
                'user_id': user_id,
                'platform': user.platform.value,
                'nickname': user.nickname,
                'post_count': post_count,
                'comment_count': comment_count,
                'total_likes': total_likes,
                'last_post_time': last_post_time.strftime('%Y-%m-%d %H:%M:%S') if last_post_time else None
            }
    
    async def search_posts(
        self,
        keyword: str,
        platform: Optional[PlatformEnum] = None,
        sentiment: Optional[SentimentLabelEnum] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        搜索帖子(按标题或内容)
        
        示例:
            # 搜索包含"Python"的帖子
            posts = await query.search_posts(keyword="Python")
            
            # 搜索小红书中正面情感的帖子
            posts = await query.search_posts(
                keyword="旅游",
                platform=PlatformEnum.XHS,
                sentiment=SentimentLabelEnum.POSITIVE
            )
        """
        async with self.session_maker() as session:
            query = (
                select(Post)
                .where(
                    or_(
                        Post.title.like(f'%{keyword}%'),
                        Post.content.like(f'%{keyword}%')
                    )
                )
            )
            
            if platform:
                query = query.where(Post.platform == platform)
            
            if sentiment:
                query = (
                    query
                    .join(
                        SentimentAnalysis,
                        and_(
                            SentimentAnalysis.content_id == Post.id,
                            SentimentAnalysis.content_type == ContentTypeEnum.POST,
                            SentimentAnalysis.sentiment_label == sentiment
                        )
                    )
                )
            
            query = query.order_by(desc(Post.published_at)).limit(limit)
            
            result = await session.execute(query)
            posts = result.scalars().all()
            
            return [
                {
                    'id': post.id,
                    'platform': post.platform.value,
                    'title': post.title,
                    'content': post.content[:100] + '...' if len(post.content) > 100 else post.content,
                    'published_at': post.published_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                for post in posts
            ]
    
    async def get_time_series_sentiment(
        self,
        platform: Optional[PlatformEnum] = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        获取时间序列情感趋势
        
        示例:
            # 获取最近30天的情感趋势
            df = await query.get_time_series_sentiment(days=30)
            
            # 绘制趋势图
            import matplotlib.pyplot as plt
            df.plot(x='date', y=['positive', 'neutral', 'negative'])
            plt.show()
        """
        async with self.session_maker() as session:
            start_date = datetime.now() - timedelta(days=days)
            
            query = (
                select(
                    func.date(Post.published_at).label('date'),
                    SentimentAnalysis.sentiment_label,
                    func.count(SentimentAnalysis.id).label('count')
                )
                .join(
                    SentimentAnalysis,
                    and_(
                        SentimentAnalysis.content_id == Post.id,
                        SentimentAnalysis.content_type == ContentTypeEnum.POST
                    )
                )
                .where(Post.published_at >= start_date)
                .group_by(func.date(Post.published_at), SentimentAnalysis.sentiment_label)
                .order_by(func.date(Post.published_at))
            )
            
            if platform:
                query = query.where(Post.platform == platform)
            
            result = await session.execute(query)
            rows = result.all()
            
            # 转换为DataFrame
            data = []
            for row in rows:
                data.append({
                    'date': row.date,
                    'sentiment': row.sentiment_label.value,
                    'count': row.count
                })
            
            df = pd.DataFrame(data)
            
            # 透视表: 日期 x 情感标签
            if not df.empty:
                df_pivot = df.pivot(
                    index='date',
                    columns='sentiment',
                    values='count'
                ).fillna(0)
                return df_pivot
            
            return pd.DataFrame()
    
    async def get_database_summary(self) -> Dict:
        """
        获取数据库整体统计
        
        示例:
            summary = await query.get_database_summary()
            print(f"总用户数: {summary['total_users']}")
            print(f"总帖子数: {summary['total_posts']}")
        """
        async with self.session_maker() as session:
            # 用户统计
            result = await session.execute(
                select(
                    func.count(User.id).label('total'),
                    User.platform
                )
                .group_by(User.platform)
            )
            user_stats = {row.platform.value: row.total for row in result.all()}
            
            # 帖子统计
            result = await session.execute(
                select(
                    func.count(Post.id).label('total'),
                    Post.platform
                )
                .group_by(Post.platform)
            )
            post_stats = {row.platform.value: row.total for row in result.all()}
            
            # 评论统计
            result = await session.execute(
                select(
                    func.count(Comment.id).label('total'),
                    Comment.platform
                )
                .group_by(Comment.platform)
            )
            comment_stats = {row.platform.value: row.total for row in result.all()}
            
            # 情感分析统计
            result = await session.execute(
                select(func.count(SentimentAnalysis.id))
            )
            sentiment_total = result.scalar()
            
            return {
                'total_users': sum(user_stats.values()),
                'total_posts': sum(post_stats.values()),
                'total_comments': sum(comment_stats.values()),
                'total_sentiment_analysis': sentiment_total,
                'users_by_platform': user_stats,
                'posts_by_platform': post_stats,
                'comments_by_platform': comment_stats
            }


async def demo():
    """演示查询功能"""
    DB_URL = "mysql+aiomysql://root:123456@localhost:3306/media_crawler_optimized"
    
    query = OptimizedDatabaseQuery(DB_URL)
    
    print("=" * 50)
    print("数据库查询演示")
    print("=" * 50)
    
    # 1. 数据库总览
    print("\n📊 数据库总览:")
    summary = await query.get_database_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 2. 跨平台情感对比
    print("\n💭 跨平台情感分布:")
    sentiment_stats = await query.get_platform_sentiment_stats()
    for platform, stats in sentiment_stats.items():
        print(f"  {platform}:")
        print(f"    Positive: {stats['positive']:4d} ({stats['positive']/stats['total']*100:.1f}%)")
        print(f"    Neutral:  {stats['neutral']:4d} ({stats['neutral']/stats['total']*100:.1f}%)")
        print(f"    Negative: {stats['negative']:4d} ({stats['negative']/stats['total']*100:.1f}%)")
    
    # 3. 热门帖子
    print("\n🔥 热门帖子 TOP 5:")
    hot_posts = await query.get_hot_posts(days=30, limit=5)
    for i, post in enumerate(hot_posts, 1):
        print(f"  {i}. [{post['platform']}] {post['title'][:30]}...")
        print(f"     👍 {post['likes']} 💬 {post['comments']} 📤 {post['shares']}")


if __name__ == "__main__":
    asyncio.run(demo())
