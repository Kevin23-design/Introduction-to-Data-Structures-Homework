"""
数据迁移脚本 - 从原9张表迁移到优化的4张表
将 zhihu/xhs/tieba 各自的 content/comment 表迁移到统一的 users/posts/comments/sentiment_analysis 表
"""
import asyncio
from typing import Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import (
    ZhihuContent, ZhihuComment,
    XhsNote, XhsNoteComment,
    TiebaNote, TiebaComment
)
from database.optimized_models import (
    User, Post, Comment, SentimentAnalysis,
    PlatformEnum, ContentTypeEnum, SentimentLabelEnum
)
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataMigrator:
    """数据迁移工具类"""
    
    def __init__(self, source_db_url: str, target_db_url: str):
        """
        初始化迁移器
        
        Args:
            source_db_url: 源数据库URL (原9表数据库)
            target_db_url: 目标数据库URL (优化4表数据库)
        """
        self.source_engine = create_async_engine(source_db_url, echo=False)
        self.target_engine = create_async_engine(target_db_url, echo=False)
        
        self.source_session_maker = async_sessionmaker(
            self.source_engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        self.target_session_maker = async_sessionmaker(
            self.target_engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # 用户ID映射缓存: {(platform, platform_user_id): new_user_id}
        self.user_id_map: Dict[tuple, int] = {}
        
        # 帖子ID映射缓存: {(platform, platform_post_id): new_post_id}
        self.post_id_map: Dict[tuple, int] = {}
    
    async def migrate_all(self):
        """执行完整迁移流程"""
        logger.info("=" * 50)
        logger.info("开始数据迁移: 9表 → 4表")
        logger.info("=" * 50)
        
        try:
            # 1. 迁移知乎数据
            await self.migrate_zhihu()
            
            # 2. 迁移小红书数据
            await self.migrate_xhs()
            
            # 3. 迁移贴吧数据
            await self.migrate_tieba()
            
            # 4. 生成统计报告
            await self.generate_report()
            
            logger.info("=" * 50)
            logger.info("数据迁移完成!")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            raise
    
    async def migrate_zhihu(self):
        """迁移知乎数据"""
        logger.info("\n🔵 开始迁移知乎数据...")
        
        async with self.source_session_maker() as source_session:
            async with self.target_session_maker() as target_session:
                # 查询知乎帖子
                result = await source_session.execute(
                    select(ZhihuContent)
                )
                zhihu_contents = result.scalars().all()
                logger.info(f"  - 找到 {len(zhihu_contents)} 条知乎帖子")
                
                # 迁移帖子和用户
                for content in zhihu_contents:
                    # 迁移用户
                    user_id = await self._migrate_user(
                        target_session,
                        platform=PlatformEnum.ZHIHU,
                        platform_user_id=content.author_id or "unknown",
                        nickname=content.user_nickname,
                        avatar_url=content.author_avatar_url
                    )
                    
                    # 迁移帖子
                    post = Post(
                        platform=PlatformEnum.ZHIHU,
                        platform_post_id=content.content_id,
                        user_id=user_id,
                        title=content.title,
                        content=content.content_text,
                        likes_count=content.voteup_count or 0,
                        comments_count=content.comment_count or 0,
                        published_at=self._parse_timestamp(content.created_time),
                        platform_data={
                            "question_id": content.question_id,
                            "answer_id": content.answer_id,
                            "voteup_count": content.voteup_count,
                            "comment_count": content.comment_count
                        }
                    )
                    target_session.add(post)
                    await target_session.flush()
                    
                    # 缓存帖子ID映射
                    self.post_id_map[(PlatformEnum.ZHIHU.value, content.content_id)] = post.id
                    
                    # 迁移情感分析
                    if content.sentiment_label:
                        sentiment = SentimentAnalysis(
                            content_type=ContentTypeEnum.POST,
                            content_id=post.id,
                            sentiment_label=self._parse_sentiment_label(content.sentiment_label),
                            sentiment_score=content.sentiment_score
                        )
                        target_session.add(sentiment)
                
                await target_session.commit()
                logger.info(f"  ✅ 知乎帖子迁移完成")
                
                # 迁移知乎评论
                result = await source_session.execute(
                    select(ZhihuComment)
                )
                zhihu_comments = result.scalars().all()
                logger.info(f"  - 找到 {len(zhihu_comments)} 条知乎评论")
                
                for comment in zhihu_comments:
                    # 获取对应的新帖子ID
                    post_id = self.post_id_map.get((PlatformEnum.ZHIHU.value, comment.content_id))
                    if not post_id:
                        logger.warning(f"  ⚠️  未找到评论对应的帖子: {comment.content_id}")
                        continue
                    
                    # 迁移评论用户
                    user_id = await self._migrate_user(
                        target_session,
                        platform=PlatformEnum.ZHIHU,
                        platform_user_id=comment.author_id or "unknown",
                        nickname=comment.user_nickname,
                        avatar_url=comment.avatar_url
                    )
                    
                    # 迁移评论
                    comment_obj = Comment(
                        platform=PlatformEnum.ZHIHU,
                        platform_comment_id=comment.comment_id,
                        post_id=post_id,
                        user_id=user_id,
                        content=comment.content_text,
                        likes_count=comment.like_count or 0,
                        published_at=self._parse_timestamp(comment.created_time)
                    )
                    target_session.add(comment_obj)
                    await target_session.flush()
                    
                    # 迁移评论情感分析
                    if comment.sentiment_label:
                        sentiment = SentimentAnalysis(
                            content_type=ContentTypeEnum.COMMENT,
                            content_id=comment_obj.id,
                            sentiment_label=self._parse_sentiment_label(comment.sentiment_label),
                            sentiment_score=comment.sentiment_score
                        )
                        target_session.add(sentiment)
                
                await target_session.commit()
                logger.info(f"  ✅ 知乎评论迁移完成")
    
    async def migrate_xhs(self):
        """迁移小红书数据"""
        logger.info("\n🔴 开始迁移小红书数据...")
        
        async with self.source_session_maker() as source_session:
            async with self.target_session_maker() as target_session:
                # 查询小红书笔记
                result = await source_session.execute(
                    select(XhsNote)
                )
                xhs_notes = result.scalars().all()
                logger.info(f"  - 找到 {len(xhs_notes)} 条小红书笔记")
                
                for note in xhs_notes:
                    # 迁移用户
                    user_id = await self._migrate_user(
                        target_session,
                        platform=PlatformEnum.XHS,
                        platform_user_id=note.user_id or "unknown",
                        nickname=note.user_nickname,
                        avatar_url=note.avatar
                    )
                    
                    # 迁移笔记
                    post = Post(
                        platform=PlatformEnum.XHS,
                        platform_post_id=note.note_id,
                        user_id=user_id,
                        title=note.title,
                        content=note.content_text,
                        likes_count=note.liked_count or 0,
                        comments_count=note.comment_count or 0,
                        shares_count=note.share_count or 0,
                        views_count=note.note_view_count or 0,
                        published_at=self._parse_timestamp(note.time),
                        platform_data={
                            "note_id": note.note_id,
                            "note_url": note.note_url,
                            "image_list": note.image_list,
                            "video_url": note.video_url,
                            "tag_list": note.tag_list,
                            "liked_count": note.liked_count,
                            "collected_count": note.collected_count
                        }
                    )
                    target_session.add(post)
                    await target_session.flush()
                    
                    self.post_id_map[(PlatformEnum.XHS.value, note.note_id)] = post.id
                    
                    # 迁移情感分析
                    if note.sentiment_label:
                        sentiment = SentimentAnalysis(
                            content_type=ContentTypeEnum.POST,
                            content_id=post.id,
                            sentiment_label=self._parse_sentiment_label(note.sentiment_label),
                            sentiment_score=note.sentiment_score
                        )
                        target_session.add(sentiment)
                
                await target_session.commit()
                logger.info(f"  ✅ 小红书笔记迁移完成")
                
                # 迁移小红书评论
                result = await source_session.execute(
                    select(XhsNoteComment)
                )
                xhs_comments = result.scalars().all()
                logger.info(f"  - 找到 {len(xhs_comments)} 条小红书评论")
                
                for comment in xhs_comments:
                    post_id = self.post_id_map.get((PlatformEnum.XHS.value, comment.note_id))
                    if not post_id:
                        continue
                    
                    user_id = await self._migrate_user(
                        target_session,
                        platform=PlatformEnum.XHS,
                        platform_user_id=comment.user_id or "unknown",
                        nickname=comment.user_nickname,
                        avatar_url=comment.avatar
                    )
                    
                    comment_obj = Comment(
                        platform=PlatformEnum.XHS,
                        platform_comment_id=comment.comment_id,
                        post_id=post_id,
                        user_id=user_id,
                        content=comment.content,
                        likes_count=comment.like_count or 0,
                        published_at=self._parse_timestamp(comment.time),
                        platform_data={
                            "sub_comment_count": comment.sub_comment_count
                        }
                    )
                    target_session.add(comment_obj)
                    await target_session.flush()
                    
                    if comment.sentiment_label:
                        sentiment = SentimentAnalysis(
                            content_type=ContentTypeEnum.COMMENT,
                            content_id=comment_obj.id,
                            sentiment_label=self._parse_sentiment_label(comment.sentiment_label),
                            sentiment_score=comment.sentiment_score
                        )
                        target_session.add(sentiment)
                
                await target_session.commit()
                logger.info(f"  ✅ 小红书评论迁移完成")
    
    async def migrate_tieba(self):
        """迁移贴吧数据"""
        logger.info("\n🟡 开始迁移贴吧数据...")
        
        async with self.source_session_maker() as source_session:
            async with self.target_session_maker() as target_session:
                # 查询贴吧帖子
                result = await source_session.execute(
                    select(TiebaNote)
                )
                tieba_notes = result.scalars().all()
                logger.info(f"  - 找到 {len(tieba_notes)} 条贴吧帖子")
                
                for note in tieba_notes:
                    # 迁移用户
                    user_id = await self._migrate_user(
                        target_session,
                        platform=PlatformEnum.TIEBA,
                        platform_user_id=note.user_id or "unknown",
                        nickname=note.user_nickname,
                        avatar_url=note.avatar
                    )
                    
                    # 迁移帖子
                    post = Post(
                        platform=PlatformEnum.TIEBA,
                        platform_post_id=note.note_id,
                        user_id=user_id,
                        title=note.title,
                        content=note.content,
                        likes_count=note.agree_count or 0,
                        comments_count=note.total_replay_num or 0,
                        shares_count=note.share_count or 0,
                        published_at=self._parse_timestamp(note.publish_time),
                        platform_data={
                            "forum_name": note.forum_name,
                            "thread_id": note.note_id,
                            "reply_count": note.total_replay_num,
                            "heat_score": note.heat_score
                        }
                    )
                    target_session.add(post)
                    await target_session.flush()
                    
                    self.post_id_map[(PlatformEnum.TIEBA.value, note.note_id)] = post.id
                    
                    # 迁移情感分析
                    if note.sentiment_label:
                        sentiment = SentimentAnalysis(
                            content_type=ContentTypeEnum.POST,
                            content_id=post.id,
                            sentiment_label=self._parse_sentiment_label(note.sentiment_label),
                            sentiment_score=note.sentiment_score
                        )
                        target_session.add(sentiment)
                
                await target_session.commit()
                logger.info(f"  ✅ 贴吧帖子迁移完成")
                
                # 迁移贴吧评论
                result = await source_session.execute(
                    select(TiebaComment)
                )
                tieba_comments = result.scalars().all()
                logger.info(f"  - 找到 {len(tieba_comments)} 条贴吧评论")
                
                for comment in tieba_comments:
                    post_id = self.post_id_map.get((PlatformEnum.TIEBA.value, comment.note_id))
                    if not post_id:
                        continue
                    
                    user_id = await self._migrate_user(
                        target_session,
                        platform=PlatformEnum.TIEBA,
                        platform_user_id=comment.user_id or "unknown",
                        nickname=comment.user_nickname,
                        avatar_url=comment.avatar
                    )
                    
                    comment_obj = Comment(
                        platform=PlatformEnum.TIEBA,
                        platform_comment_id=comment.comment_id,
                        post_id=post_id,
                        user_id=user_id,
                        content=comment.content,
                        likes_count=0,  # 贴吧评论无点赞数
                        published_at=self._parse_timestamp(comment.create_time)
                    )
                    target_session.add(comment_obj)
                    await target_session.flush()
                    
                    if comment.sentiment_label:
                        sentiment = SentimentAnalysis(
                            content_type=ContentTypeEnum.COMMENT,
                            content_id=comment_obj.id,
                            sentiment_label=self._parse_sentiment_label(comment.sentiment_label),
                            sentiment_score=comment.sentiment_score
                        )
                        target_session.add(sentiment)
                
                await target_session.commit()
                logger.info(f"  ✅ 贴吧评论迁移完成")
    
    async def _migrate_user(
        self, 
        session: AsyncSession,
        platform: PlatformEnum,
        platform_user_id: str,
        nickname: Optional[str],
        avatar_url: Optional[str]
    ) -> int:
        """
        迁移用户(如果不存在则创建)
        
        Returns:
            新用户表的user_id
        """
        cache_key = (platform.value, platform_user_id)
        
        # 检查缓存
        if cache_key in self.user_id_map:
            return self.user_id_map[cache_key]
        
        # 检查数据库是否已存在
        result = await session.execute(
            select(User).where(
                User.platform == platform,
                User.platform_user_id == platform_user_id
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # 创建新用户
            user = User(
                platform=platform,
                platform_user_id=platform_user_id,
                nickname=nickname,
                avatar_url=avatar_url
            )
            session.add(user)
            await session.flush()
        
        # 缓存映射
        self.user_id_map[cache_key] = user.id
        return user.id
    
    def _parse_timestamp(self, timestamp) -> Optional[datetime]:
        """解析时间戳"""
        if not timestamp:
            return None
        
        if isinstance(timestamp, datetime):
            return timestamp
        
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp)
            except:
                return None
        
        if isinstance(timestamp, (int, float)):
            # 判断是秒还是毫秒
            if timestamp > 1e12:
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp)
        
        return None
    
    def _parse_sentiment_label(self, label: str) -> SentimentLabelEnum:
        """解析情感标签"""
        label_map = {
            "positive": SentimentLabelEnum.POSITIVE,
            "neutral": SentimentLabelEnum.NEUTRAL,
            "negative": SentimentLabelEnum.NEGATIVE
        }
        return label_map.get(label.lower(), SentimentLabelEnum.NEUTRAL)
    
    async def generate_report(self):
        """生成迁移统计报告"""
        logger.info("\n📊 生成迁移统计报告...")
        
        async with self.target_session_maker() as session:
            # 统计用户数
            result = await session.execute(select(func.count(User.id)))
            user_count = result.scalar()
            
            # 统计帖子数
            result = await session.execute(select(func.count(Post.id)))
            post_count = result.scalar()
            
            # 统计评论数
            result = await session.execute(select(func.count(Comment.id)))
            comment_count = result.scalar()
            
            # 统计情感分析数
            result = await session.execute(select(func.count(SentimentAnalysis.id)))
            sentiment_count = result.scalar()
            
            # 按平台统计
            for platform in [PlatformEnum.ZHIHU, PlatformEnum.XHS, PlatformEnum.TIEBA]:
                result = await session.execute(
                    select(func.count(Post.id)).where(Post.platform == platform)
                )
                platform_post_count = result.scalar()
                
                result = await session.execute(
                    select(func.count(Comment.id)).where(Comment.platform == platform)
                )
                platform_comment_count = result.scalar()
                
                logger.info(
                    f"  - {platform.value:6s}: {platform_post_count:5d} 帖子, "
                    f"{platform_comment_count:5d} 评论"
                )
            
            logger.info(f"\n总计:")
            logger.info(f"  - 用户:     {user_count:6d}")
            logger.info(f"  - 帖子:     {post_count:6d}")
            logger.info(f"  - 评论:     {comment_count:6d}")
            logger.info(f"  - 情感分析: {sentiment_count:6d}")


async def main():
    """主函数 - 执行迁移"""
    
    # 数据库配置
    SOURCE_DB_URL = "mysql+aiomysql://root:123456@localhost:3306/media_crawler"
    TARGET_DB_URL = "mysql+aiomysql://root:123456@localhost:3306/media_crawler_optimized"
    
    # 创建迁移器
    migrator = DataMigrator(SOURCE_DB_URL, TARGET_DB_URL)
    
    # 执行迁移
    await migrator.migrate_all()


if __name__ == "__main__":
    asyncio.run(main())
