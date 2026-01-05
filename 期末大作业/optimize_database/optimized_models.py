"""
优化后的数据库模型 - 统一的4表结构
支持多平台(zhihu/xhs/tieba)的统一数据模型
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, BigInteger, Integer, Text, 
    DateTime, Float, JSON, ForeignKey, Index, Enum
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class PlatformEnum(enum.Enum):
    """平台枚举"""
    ZHIHU = "zhihu"
    XHS = "xhs"
    TIEBA = "tieba"


class ContentTypeEnum(enum.Enum):
    """内容类型枚举"""
    POST = "post"
    COMMENT = "comment"


class SentimentLabelEnum(enum.Enum):
    """情感标签枚举"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class User(Base):
    """
    用户表 - 统一存储所有平台的用户信息
    """
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    platform = Column(
        Enum(PlatformEnum), 
        nullable=False, 
        index=True,
        comment="平台: zhihu/xhs/tieba"
    )
    platform_user_id = Column(
        String(128), 
        nullable=False, 
        comment="平台用户ID"
    )
    nickname = Column(String(128), comment="用户昵称")
    avatar_url = Column(String(512), comment="头像URL")
    
    # 时间戳
    created_at = Column(
        DateTime, 
        default=datetime.now, 
        comment="记录创建时间"
    )
    updated_at = Column(
        DateTime, 
        default=datetime.now, 
        onupdate=datetime.now,
        comment="记录更新时间"
    )
    
    # 关系
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    
    # 复合唯一索引: 同一平台的用户ID唯一
    __table_args__ = (
        Index('idx_platform_user', 'platform', 'platform_user_id', unique=True),
        Index('idx_nickname', 'nickname'),
        {'comment': '用户表 - 存储所有平台用户信息'}
    )


class Post(Base):
    """
    帖子表 - 统一存储所有平台的帖子/笔记/主题
    """
    __tablename__ = "posts"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    platform = Column(
        Enum(PlatformEnum), 
        nullable=False, 
        index=True,
        comment="平台"
    )
    platform_post_id = Column(
        String(128), 
        nullable=False,
        comment="平台帖子ID"
    )
    user_id = Column(
        BigInteger, 
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="用户ID"
    )
    
    # 基础内容
    title = Column(String(512), comment="标题")
    content = Column(Text, comment="内容")
    
    # 统计数据
    likes_count = Column(Integer, default=0, comment="点赞数")
    comments_count = Column(Integer, default=0, comment="评论数")
    shares_count = Column(Integer, default=0, comment="分享数")
    views_count = Column(Integer, default=0, comment="浏览数")
    
    # 时间
    published_at = Column(DateTime, comment="发布时间")
    created_at = Column(DateTime, default=datetime.now, comment="记录创建时间")
    updated_at = Column(
        DateTime, 
        default=datetime.now, 
        onupdate=datetime.now,
        comment="记录更新时间"
    )
    
    # 平台特有字段 - JSON存储
    platform_data = Column(
        JSON, 
        comment="""平台特有字段JSON:
        - zhihu: {question_id, answer_id, voteup_count, comment_count}
        - xhs: {note_id, image_list, video_url, tag_list, liked_count, collected_count}
        - tieba: {forum_name, thread_id, reply_count, heat_score}
        """
    )
    
    # 关系
    user = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    sentiment_analysis = relationship(
        "SentimentAnalysis", 
        primaryjoin="and_(Post.id==foreign(SentimentAnalysis.content_id), "
                    "SentimentAnalysis.content_type=='POST')",
        viewonly=True
    )
    
    __table_args__ = (
        Index('idx_platform_post', 'platform', 'platform_post_id', unique=True),
        Index('idx_user_id', 'user_id'),
        Index('idx_published_at', 'published_at'),
        Index('idx_likes_count', 'likes_count'),
        {'comment': '帖子表 - 存储所有平台的帖子内容'}
    )


class Comment(Base):
    """
    评论表 - 统一存储所有平台的评论
    """
    __tablename__ = "comments"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    platform = Column(
        Enum(PlatformEnum), 
        nullable=False, 
        index=True,
        comment="平台"
    )
    platform_comment_id = Column(
        String(128), 
        nullable=False,
        comment="平台评论ID"
    )
    post_id = Column(
        BigInteger, 
        ForeignKey('posts.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="帖子ID"
    )
    user_id = Column(
        BigInteger, 
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="用户ID"
    )
    
    # 评论内容
    content = Column(Text, nullable=False, comment="评论内容")
    
    # 统计数据
    likes_count = Column(Integer, default=0, comment="点赞数")
    
    # 回复关系
    parent_comment_id = Column(
        BigInteger, 
        ForeignKey('comments.id', ondelete='CASCADE'),
        comment="父评论ID(用于多级评论)"
    )
    
    # 时间
    published_at = Column(DateTime, comment="发布时间")
    created_at = Column(DateTime, default=datetime.now, comment="记录创建时间")
    updated_at = Column(
        DateTime, 
        default=datetime.now, 
        onupdate=datetime.now,
        comment="记录更新时间"
    )
    
    # 平台特有字段
    platform_data = Column(
        JSON,
        comment="平台特有字段JSON"
    )
    
    # 关系
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent_comment = relationship(
        "Comment", 
        remote_side=[id],
        backref="sub_comments"
    )
    sentiment_analysis = relationship(
        "SentimentAnalysis",
        primaryjoin="and_(Comment.id==foreign(SentimentAnalysis.content_id), "
                    "SentimentAnalysis.content_type=='COMMENT')",
        viewonly=True
    )
    
    __table_args__ = (
        Index('idx_platform_comment', 'platform', 'platform_comment_id', unique=True),
        Index('idx_post_id', 'post_id'),
        Index('idx_user_id', 'user_id'),
        Index('idx_published_at', 'published_at'),
        {'comment': '评论表 - 存储所有平台的评论'}
    )


class SentimentAnalysis(Base):
    """
    情感分析表 - 存储帖子和评论的情感分析结果
    """
    __tablename__ = "sentiment_analysis"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    content_type = Column(
        Enum(ContentTypeEnum), 
        nullable=False,
        index=True,
        comment="内容类型: post/comment"
    )
    content_id = Column(
        BigInteger, 
        nullable=False,
        index=True,
        comment="内容ID(post_id或comment_id)"
    )
    
    # SnowNLP自动分析结果
    sentiment_label = Column(
        Enum(SentimentLabelEnum),
        comment="情感标签: positive/neutral/negative"
    )
    sentiment_score = Column(
        Float,
        comment="情感分数: -1.0~1.0"
    )
    
    # 人工标注结果
    manual_label = Column(
        Enum(SentimentLabelEnum),
        comment="人工标注标签"
    )
    manual_score = Column(
        Float,
        comment="人工标注分数"
    )
    annotator = Column(String(64), comment="标注人")
    annotation_time = Column(DateTime, comment="标注时间")
    annotation_notes = Column(Text, comment="标注备注")
    is_annotated = Column(Integer, default=0, comment="是否已标注: 0-否 1-是")
    
    # 时间戳
    analyzed_at = Column(
        DateTime, 
        default=datetime.now,
        comment="分析时间"
    )
    updated_at = Column(
        DateTime, 
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )
    
    __table_args__ = (
        Index('idx_content_type_id', 'content_type', 'content_id', unique=True),
        Index('idx_sentiment_label', 'sentiment_label'),
        Index('idx_is_annotated', 'is_annotated'),
        {'comment': '情感分析表 - 存储帖子和评论的情感分析结果'}
    )
