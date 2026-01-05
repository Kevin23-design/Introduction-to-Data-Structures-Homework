"""
导出测试数据集到MySQL数据库
用于NLP实验的随机样本数据
"""
import argparse
import asyncio
from datetime import datetime
from typing import List, Dict, Any

import aiomysql
from sqlalchemy import select, func

from config import db_config
from database.db import init_db
from database.db_session import get_session
from database.models import (
    ZhihuContent, ZhihuComment,
    XhsNote, XhsNoteComment,
    TiebaNote, TiebaComment
)


class TestDatabaseExporter:
    """测试数据库导出器"""
    
    def __init__(self, note_count: int = 20, comment_count: int = 100):
        """
        Args:
            note_count: 每个平台导出的笔记数量
            comment_count: 每个平台导出的评论数量
        """
        self.note_count = note_count
        self.comment_count = comment_count
        self.test_db_name = "nlp_test_dataset"
        self.stats = {
            'zhihu': {'notes': 0, 'comments': 0},
            'xhs': {'notes': 0, 'comments': 0},
            'tieba': {'notes': 0, 'comments': 0}
        }
    
    def _convert_timestamp(self, value) -> datetime:
        """转换时间戳为datetime对象"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # 尝试解析字符串格式的时间戳
            try:
                return datetime.fromtimestamp(int(value))
            except:
                # 尝试毫秒级时间戳
                try:
                    return datetime.fromtimestamp(int(value) / 1000)
                except:
                    return None
        if isinstance(value, (int, float)):
            # 判断是秒级还是毫秒级时间戳
            if value > 10000000000:  # 毫秒级
                return datetime.fromtimestamp(value / 1000)
            else:  # 秒级
                return datetime.fromtimestamp(value)
        return None
        
    async def get_mysql_connection(self, use_db: bool = True):
        """创建MySQL连接"""
        config = {
            'host': db_config.MYSQL_DB_HOST,
            'port': db_config.MYSQL_DB_PORT,
            'user': db_config.MYSQL_DB_USER,
            'password': db_config.MYSQL_DB_PWD,
            'charset': 'utf8mb4',
            'autocommit': True
        }
        if use_db:
            config['db'] = self.test_db_name
        return await aiomysql.connect(**config)
    
    async def init_database(self):
        """初始化测试数据库"""
        print(f"正在初始化数据库 {self.test_db_name}...")
        conn = await self.get_mysql_connection(use_db=False)
        try:
            async with conn.cursor() as cursor:
                # 创建数据库
                await cursor.execute(f"DROP DATABASE IF EXISTS {self.test_db_name}")
                await cursor.execute(
                    f"CREATE DATABASE {self.test_db_name} "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                print(f"✓ 数据库 {self.test_db_name} 创建成功")
        finally:
            conn.close()
    
    async def create_tables(self):
        """创建测试数据表"""
        print("正在创建数据表...")
        conn = await self.get_mysql_connection()
        try:
            async with conn.cursor() as cursor:
                # 创建笔记表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_notes (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        platform VARCHAR(20) NOT NULL,
                        note_id VARCHAR(64) NOT NULL,
                        title TEXT,
                        content TEXT,
                        author VARCHAR(100),
                        publish_time DATETIME,
                        liked_count INT DEFAULT 0,
                        collected_count INT DEFAULT 0,
                        comment_count INT DEFAULT 0,
                        share_count INT DEFAULT 0,
                        note_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        -- 人工标注字段（用于模型评估）
                        manual_sentiment_label VARCHAR(20) COMMENT '人工标注情感: positive/negative/neutral',
                        manual_sentiment_score FLOAT COMMENT '人工标注情感分数: -1.0到1.0',
                        annotator VARCHAR(50) COMMENT '标注人员',
                        annotation_time TIMESTAMP NULL COMMENT '标注时间',
                        annotation_notes TEXT COMMENT '标注备注',
                        is_annotated BOOLEAN DEFAULT FALSE COMMENT '是否已标注',
                        UNIQUE KEY uk_platform_note (platform, note_id),
                        KEY idx_platform (platform),
                        KEY idx_publish_time (publish_time),
                        KEY idx_is_annotated (is_annotated)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # 创建评论表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_comments (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        platform VARCHAR(20) NOT NULL,
                        comment_id VARCHAR(64) NOT NULL,
                        note_id VARCHAR(64) NOT NULL,
                        content TEXT,
                        author VARCHAR(100),
                        publish_time DATETIME,
                        liked_count INT DEFAULT 0,
                        sub_comment_count INT DEFAULT 0,
                        parent_comment_id VARCHAR(64),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        -- 人工标注字段（用于模型评估）
                        manual_sentiment_label VARCHAR(20) COMMENT '人工标注情感: positive/negative/neutral',
                        manual_sentiment_score FLOAT COMMENT '人工标注情感分数: -1.0到1.0',
                        annotator VARCHAR(50) COMMENT '标注人员',
                        annotation_time TIMESTAMP NULL COMMENT '标注时间',
                        annotation_notes TEXT COMMENT '标注备注',
                        is_annotated BOOLEAN DEFAULT FALSE COMMENT '是否已标注',
                        UNIQUE KEY uk_platform_comment (platform, comment_id),
                        KEY idx_platform (platform),
                        KEY idx_note_id (note_id),
                        KEY idx_publish_time (publish_time),
                        KEY idx_is_annotated (is_annotated)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # 创建导出日志表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS export_logs (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        export_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        platform VARCHAR(20) NOT NULL,
                        note_count INT DEFAULT 0,
                        comment_count INT DEFAULT 0,
                        notes_exported INT DEFAULT 0,
                        comments_exported INT DEFAULT 0,
                        status VARCHAR(20) DEFAULT 'success',
                        error_message TEXT,
                        KEY idx_platform (platform),
                        KEY idx_export_time (export_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                print("✓ 数据表创建成功")
        finally:
            conn.close()
    
    async def export_zhihu_data(self):
        """导出知乎数据"""
        print(f"\n开始导出知乎数据 (笔记:{self.note_count}, 评论:{self.comment_count})...")
        
        async with get_session() as session:
            # 随机获取笔记
            stmt = select(ZhihuContent).order_by(func.random()).limit(self.note_count)
            result = await session.execute(stmt)
            notes = result.scalars().all()
            
            # 随机获取评论
            stmt = select(ZhihuComment).order_by(func.random()).limit(self.comment_count)
            result = await session.execute(stmt)
            comments = result.scalars().all()
            
            # 导出到测试数据库
            conn = await self.get_mysql_connection()
            try:
                async with conn.cursor() as cursor:
                    # 导出笔记
                    for note in notes:
                        await cursor.execute("""
                            INSERT INTO test_notes 
                            (platform, note_id, title, content, author, publish_time, 
                             liked_count, comment_count, note_url)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            title=VALUES(title), content=VALUES(content)
                        """, (
                            'zhihu',
                            note.content_id,
                            note.title,
                            note.content_text,
                            note.user_nickname,
                            self._convert_timestamp(note.created_time),
                            int(note.voteup_count or 0),
                            int(note.comment_count or 0),
                            note.content_url
                        ))
                        self.stats['zhihu']['notes'] += 1
                    
                    # 导出评论
                    for comment in comments:
                        await cursor.execute("""
                            INSERT INTO test_comments 
                            (platform, comment_id, note_id, content, author, 
                             publish_time, liked_count, sub_comment_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            content=VALUES(content)
                        """, (
                            'zhihu',
                            comment.comment_id,
                            comment.content_id,
                            comment.content,
                            comment.user_nickname,
                            self._convert_timestamp(comment.publish_time),
                            int(comment.like_count or 0),
                            int(comment.sub_comment_count or 0)
                        ))
                        self.stats['zhihu']['comments'] += 1
                    
                    # 记录导出日志
                    await cursor.execute("""
                        INSERT INTO export_logs 
                        (platform, note_count, comment_count, notes_exported, comments_exported)
                        VALUES (%s, %s, %s, %s, %s)
                    """, ('zhihu', self.note_count, self.comment_count, 
                          len(notes), len(comments)))
                    
                print(f"✓ 知乎数据导出完成: {len(notes)} 篇笔记, {len(comments)} 条评论")
            finally:
                conn.close()
    
    async def export_xhs_data(self):
        """导出小红书数据"""
        print(f"\n开始导出小红书数据 (笔记:{self.note_count}, 评论:{self.comment_count})...")
        
        async with get_session() as session:
            # 随机获取笔记
            stmt = select(XhsNote).order_by(func.random()).limit(self.note_count)
            result = await session.execute(stmt)
            notes = result.scalars().all()
            
            # 随机获取评论
            stmt = select(XhsNoteComment).order_by(func.random()).limit(self.comment_count)
            result = await session.execute(stmt)
            comments = result.scalars().all()
            
            # 导出到测试数据库
            conn = await self.get_mysql_connection()
            try:
                async with conn.cursor() as cursor:
                    # 导出笔记
                    for note in notes:
                        await cursor.execute("""
                            INSERT INTO test_notes 
                            (platform, note_id, title, content, author, publish_time,
                             liked_count, collected_count, comment_count, share_count, note_url)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            title=VALUES(title), content=VALUES(content)
                        """, (
                            'xhs',
                            note.note_id,
                            note.title,
                            note.desc,
                            note.nickname,
                            self._convert_timestamp(note.time),
                            self._parse_count(note.liked_count),
                            self._parse_count(note.collected_count),
                            self._parse_count(note.comment_count),
                            self._parse_count(note.share_count),
                            note.note_url
                        ))
                        self.stats['xhs']['notes'] += 1
                    
                    # 导出评论
                    for comment in comments:
                        await cursor.execute("""
                            INSERT INTO test_comments 
                            (platform, comment_id, note_id, content, author,
                             publish_time, liked_count, sub_comment_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            content=VALUES(content)
                        """, (
                            'xhs',
                            comment.comment_id,
                            comment.note_id,
                            comment.content,
                            comment.nickname,
                            self._convert_timestamp(comment.create_time),
                            self._parse_count(comment.like_count),
                            self._parse_count(comment.sub_comment_count)
                        ))
                        self.stats['xhs']['comments'] += 1
                    
                    # 记录导出日志
                    await cursor.execute("""
                        INSERT INTO export_logs 
                        (platform, note_count, comment_count, notes_exported, comments_exported)
                        VALUES (%s, %s, %s, %s, %s)
                    """, ('xhs', self.note_count, self.comment_count,
                          len(notes), len(comments)))
                    
                print(f"✓ 小红书数据导出完成: {len(notes)} 篇笔记, {len(comments)} 条评论")
            finally:
                conn.close()
    
    async def export_tieba_data(self):
        """导出贴吧数据"""
        print(f"\n开始导出贴吧数据 (笔记:{self.note_count}, 评论:{self.comment_count})...")
        
        async with get_session() as session:
            # 随机获取帖子
            stmt = select(TiebaNote).order_by(func.random()).limit(self.note_count)
            result = await session.execute(stmt)
            notes = result.scalars().all()
            
            # 随机获取评论
            stmt = select(TiebaComment).order_by(func.random()).limit(self.comment_count)
            result = await session.execute(stmt)
            comments = result.scalars().all()
            
            # 导出到测试数据库
            conn = await self.get_mysql_connection()
            try:
                async with conn.cursor() as cursor:
                    # 导出帖子
                    for note in notes:
                        await cursor.execute("""
                            INSERT INTO test_notes 
                            (platform, note_id, title, content, author, publish_time,
                             comment_count, note_url)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            title=VALUES(title), content=VALUES(content)
                        """, (
                            'tieba',
                            note.note_id,
                            note.title,
                            note.desc,
                            note.user_nickname,
                            self._convert_timestamp(note.publish_time),
                            int(note.total_replay_num or 0),
                            note.note_url
                        ))
                        self.stats['tieba']['notes'] += 1
                    
                    # 导出评论
                    for comment in comments:
                        await cursor.execute("""
                            INSERT INTO test_comments 
                            (platform, comment_id, note_id, content, author,
                             publish_time, sub_comment_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            content=VALUES(content)
                        """, (
                            'tieba',
                            comment.comment_id,
                            comment.note_id,
                            comment.content,
                            comment.user_nickname,
                            self._convert_timestamp(comment.publish_time),
                            int(comment.sub_comment_count or 0)
                        ))
                        self.stats['tieba']['comments'] += 1
                    
                    # 记录导出日志
                    await cursor.execute("""
                        INSERT INTO export_logs 
                        (platform, note_count, comment_count, notes_exported, comments_exported)
                        VALUES (%s, %s, %s, %s, %s)
                    """, ('tieba', self.note_count, self.comment_count,
                          len(notes), len(comments)))
                    
                print(f"✓ 贴吧数据导出完成: {len(notes)} 篇帖子, {len(comments)} 条评论")
            finally:
                conn.close()
    
    def _parse_count(self, value) -> int:
        """解析数量字段（处理中文格式）"""
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        
        value_str = str(value).strip()
        if not value_str or value_str == '-':
            return 0
        
        # 移除加号
        value_str = value_str.replace('+', '')
        
        # 处理中文数字单位
        if '万' in value_str:
            try:
                num = float(value_str.replace('万', ''))
                return int(num * 10000)
            except:
                return 0
        elif '千' in value_str:
            try:
                num = float(value_str.replace('千', ''))
                return int(num * 1000)
            except:
                return 0
        else:
            try:
                return int(float(value_str))
            except:
                return 0
    
    async def export_all(self):
        """导出所有平台数据"""
        start_time = datetime.now()
        print("=" * 60)
        print("开始导出测试数据集到MySQL数据库")
        print("=" * 60)
        
        try:
            # 初始化数据库和表
            await self.init_database()
            await self.create_tables()
            
            # 导出各平台数据
            await self.export_zhihu_data()
            await self.export_xhs_data()
            await self.export_tieba_data()
            
            # 输出统计信息
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print("\n" + "=" * 60)
            print("导出完成统计:")
            print("=" * 60)
            total_notes = sum(s['notes'] for s in self.stats.values())
            total_comments = sum(s['comments'] for s in self.stats.values())
            
            for platform, counts in self.stats.items():
                print(f"{platform:8s}: {counts['notes']:3d} 篇笔记, {counts['comments']:3d} 条评论")
            
            print("-" * 60)
            print(f"总计: {total_notes} 篇笔记, {total_comments} 条评论")
            print(f"耗时: {duration:.2f} 秒")
            print(f"数据库: {self.test_db_name}")
            print("=" * 60)
            
            # 输出查询示例
            print("\n查询示例:")
            print(f"mysql -u{db_config.MYSQL_DB_USER} -p{db_config.MYSQL_DB_PWD} {self.test_db_name}")
            print("SELECT platform, COUNT(*) FROM test_notes GROUP BY platform;")
            print("SELECT platform, COUNT(*) FROM test_comments GROUP BY platform;")
            
        except Exception as e:
            print(f"\n❌ 导出失败: {e}")
            raise


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="导出测试数据集到MySQL数据库")
    parser.add_argument(
        '--note-count',
        type=int,
        default=20,
        help='每个平台导出的笔记数量 (默认: 20)'
    )
    parser.add_argument(
        '--comment-count',
        type=int,
        default=100,
        help='每个平台导出的评论数量 (默认: 100)'
    )
    
    args = parser.parse_args()
    
    # 初始化原数据库连接
    await init_db('mysql')
    
    # 创建导出器并执行导出
    exporter = TestDatabaseExporter(
        note_count=args.note_count,
        comment_count=args.comment_count
    )
    
    await exporter.export_all()


if __name__ == "__main__":
    asyncio.run(main())
