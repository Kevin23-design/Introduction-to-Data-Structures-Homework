"""
实验要求5：全球不同区域在各个学科中的表现分析
通过SQL语句分析全球不同区域在各个学科中的表现
"""

import mysql.connector
import pandas as pd
from mysql.connector import Error

def create_connection():
    """创建数据库连接"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='university_ranking',
            user='root',
            password='zzy419220'
        )
        if connection.is_connected():
            print("✅ 成功连接到MySQL数据库")
            return connection
    except Error as e:
        print(f"❌ 数据库连接错误: {e}")
        return None

def analyze_global_regional_performance():
    """分析全球不同区域在各个学科中的表现"""
    
    connection = create_connection()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("\n" + "="*80)
    print("📊 全球不同区域学科表现分析")
    print("="*80)
    
    try:
        # 1. 首先分析各个区域的基本情况
        print("\n1️⃣ 全球各区域基本统计")
        print("-" * 50)
        
        query1 = """
        SELECT 
            ur.country_region AS '国家/地区',
            COUNT(DISTINCT ur.institution_name) AS '大学数量',
            COUNT(*) AS '参与记录数',
            COUNT(DISTINCT ur.subject_field) AS '参与学科数',
            ROUND(AVG(ur.ranking_position), 2) AS '平均排名',
            MIN(ur.ranking_position) AS '最好排名',
            MAX(ur.ranking_position) AS '最差排名',
            SUM(CASE WHEN ur.ranking_position <= 100 THEN 1 ELSE 0 END) AS 'TOP100次数',
            SUM(CASE WHEN ur.ranking_position <= 500 THEN 1 ELSE 0 END) AS 'TOP500次数'
        FROM university_rankings ur
        WHERE ur.ranking_position IS NOT NULL 
          AND ur.country_region != 'N/A'
        GROUP BY ur.country_region
        HAVING COUNT(*) >= 50  -- 只显示有足够数据的国家/地区
        ORDER BY COUNT(*) DESC
        LIMIT 25;
        """
        
        cursor.execute(query1)
        results1 = cursor.fetchall()
        
        # 保存到文件
        with open('global_regional_analysis_queries.sql', 'w', encoding='utf-8') as f:
            f.write("-- 全球不同区域学科表现分析SQL查询\n")
            f.write("-- 实验要求5：通过SQL语句分析全球不同区域在各个学科中的表现\n\n")
            f.write("-- 1. 全球各区域基本统计\n")
            f.write(query1 + "\n\n")
        
        print(f"{'国家/地区':<25} {'大学数':<8} {'记录数':<8} {'学科数':<8} {'平均排名':<10} {'TOP100':<8} {'TOP500':<8}")
        print("-" * 90)
        for row in results1[:15]:
            print(f"{row[0]:<25} {row[1]:<8} {row[2]:<8} {row[3]:<8} {row[4]:<10} {row[7]:<8} {row[8]:<8}")
        
        # 2. 各区域在不同学科的表现对比
        print("\n\n2️⃣ 主要区域在各学科的TOP10%表现")
        print("-" * 60)
        
        query2 = """
        SELECT 
            ur.subject_field AS '学科领域',
            SUM(CASE WHEN ur.country_region = 'USA' AND ur.ranking_position <= subject_stats.top10_threshold THEN 1 ELSE 0 END) AS 'USA_TOP10%',
            SUM(CASE WHEN ur.country_region = 'CHINA MAINLAND' AND ur.ranking_position <= subject_stats.top10_threshold THEN 1 ELSE 0 END) AS 'CHINA_TOP10%',
            SUM(CASE WHEN ur.country_region = 'ENGLAND' AND ur.ranking_position <= subject_stats.top10_threshold THEN 1 ELSE 0 END) AS 'ENGLAND_TOP10%',
            SUM(CASE WHEN ur.country_region = 'GERMANY (FED REP GER)' AND ur.ranking_position <= subject_stats.top10_threshold THEN 1 ELSE 0 END) AS 'GERMANY_TOP10%',
            SUM(CASE WHEN ur.country_region = 'FRANCE' AND ur.ranking_position <= subject_stats.top10_threshold THEN 1 ELSE 0 END) AS 'FRANCE_TOP10%',
            SUM(CASE WHEN ur.country_region = 'AUSTRALIA' AND ur.ranking_position <= subject_stats.top10_threshold THEN 1 ELSE 0 END) AS 'AUSTRALIA_TOP10%',
            subject_stats.total_institutions AS '全球总数',
            subject_stats.top10_threshold AS 'TOP10%阈值'
        FROM university_rankings ur
        JOIN (
            SELECT 
                subject_field,
                COUNT(*) as total_institutions,
                CEILING(COUNT(*) * 0.1) as top10_threshold
            FROM university_rankings 
            WHERE ranking_position IS NOT NULL
            GROUP BY subject_field
        ) subject_stats ON ur.subject_field = subject_stats.subject_field
        WHERE ur.ranking_position IS NOT NULL
        GROUP BY ur.subject_field, subject_stats.total_institutions, subject_stats.top10_threshold
        ORDER BY subject_stats.total_institutions DESC;
        """
        
        cursor.execute(query2)
        results2 = cursor.fetchall()
        
        with open('global_regional_analysis_queries.sql', 'a', encoding='utf-8') as f:
            f.write("-- 2. 主要区域在各学科的TOP10%表现对比\n")
            f.write(query2 + "\n\n")
        
        print(f"{'学科领域':<25} {'美国':<6} {'中国':<6} {'英国':<6} {'德国':<6} {'法国':<6} {'澳洲':<6} {'全球总数':<8}")
        print("-" * 90)
        for row in results2:
            print(f"{row[0]:<25} {row[1]:<6} {row[2]:<6} {row[3]:<6} {row[4]:<6} {row[5]:<6} {row[6]:<6} {row[7]:<8}")
        
        # 3. 各区域的学科优势分析
        print("\n\n3️⃣ 各区域学科优势分析（TOP10%占比）")
        print("-" * 70)
        
        query3 = """
        SELECT 
            region_performance.country_region AS '国家/地区',
            region_performance.subject_field AS '学科领域',
            region_performance.total_universities AS '参与大学数',
            region_performance.top10_count AS 'TOP10%数量',
            ROUND(region_performance.top10_count / region_performance.total_universities * 100, 2) AS 'TOP10%占比(%)',
            region_performance.avg_ranking AS '平均排名',
            ROUND(region_performance.avg_ranking / subject_totals.total_institutions * 100, 2) AS '平均排名百分位(%)'
        FROM (
            SELECT 
                ur.country_region,
                ur.subject_field,
                COUNT(*) as total_universities,
                AVG(ur.ranking_position) as avg_ranking,
                SUM(CASE WHEN ur.ranking_position <= subject_top10.top10_threshold THEN 1 ELSE 0 END) as top10_count
            FROM university_rankings ur
            JOIN (
                SELECT 
                    subject_field,
                    CEILING(COUNT(*) * 0.1) as top10_threshold
                FROM university_rankings 
                WHERE ranking_position IS NOT NULL
                GROUP BY subject_field
            ) subject_top10 ON ur.subject_field = subject_top10.subject_field
            WHERE ur.ranking_position IS NOT NULL 
              AND ur.country_region IN ('USA', 'CHINA MAINLAND', 'ENGLAND', 'GERMANY (FED REP GER)', 'FRANCE', 'AUSTRALIA', 'ITALY', 'SPAIN', 'CANADA', 'JAPAN')
            GROUP BY ur.country_region, ur.subject_field
            HAVING COUNT(*) >= 5  -- 至少有5所大学参与
        ) region_performance
        JOIN (
            SELECT 
                subject_field,
                COUNT(*) as total_institutions
            FROM university_rankings 
            WHERE ranking_position IS NOT NULL
            GROUP BY subject_field
        ) subject_totals ON region_performance.subject_field = subject_totals.subject_field
        WHERE region_performance.top10_count > 0  -- 只显示有TOP10%大学的记录
        ORDER BY region_performance.top10_count / region_performance.total_universities DESC, region_performance.top10_count DESC
        LIMIT 30;
        """
        
        cursor.execute(query3)
        results3 = cursor.fetchall()
        
        with open('global_regional_analysis_queries.sql', 'a', encoding='utf-8') as f:
            f.write("-- 3. 各区域学科优势分析（TOP10%占比）\n")
            f.write(query3 + "\n\n")
        
        print(f"{'国家/地区':<20} {'学科领域':<25} {'参与数':<8} {'TOP10%':<8} {'占比%':<8} {'平均排名':<10}")
        print("-" * 100)
        for row in results3:
            print(f"{row[0]:<20} {row[1]:<25} {row[2]:<8} {row[3]:<8} {row[4]:<8} {row[6]:<10}")
        
        # 4. 全球区域竞争力综合排名
        print("\n\n4️⃣ 全球区域竞争力综合排名")
        print("-" * 50)
        
        query4 = """
        SELECT 
            ur.country_region AS '国家/地区',
            COUNT(DISTINCT ur.subject_field) AS '参与学科数',
            COUNT(*) AS '总参与次数',
            COUNT(DISTINCT ur.institution_name) AS '大学数量',
            ROUND(AVG(ur.ranking_position), 2) AS '平均排名',
            SUM(CASE WHEN ur.ranking_position <= 10 THEN 1 ELSE 0 END) AS 'TOP10次数',
            SUM(CASE WHEN ur.ranking_position <= 50 THEN 1 ELSE 0 END) AS 'TOP50次数',
            SUM(CASE WHEN ur.ranking_position <= 100 THEN 1 ELSE 0 END) AS 'TOP100次数',
            ROUND(SUM(CASE WHEN ur.ranking_position <= 100 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS 'TOP100占比(%)',
            -- 竞争力综合得分（越低越好）
            ROUND(
                AVG(ur.ranking_position) * 0.4 +  -- 平均排名权重40%
                (1000 - SUM(CASE WHEN ur.ranking_position <= 100 THEN 1 ELSE 0 END)) * 0.3 +  -- TOP100数量权重30%（取反）
                (100 - COUNT(DISTINCT ur.subject_field)) * 10 * 0.3,  -- 学科覆盖度权重30%（取反）
                2
            ) AS '竞争力得分'
        FROM university_rankings ur
        WHERE ur.ranking_position IS NOT NULL 
          AND ur.country_region != 'N/A'
        GROUP BY ur.country_region
        HAVING COUNT(*) >= 100  -- 只分析有足够数据的国家/地区
        ORDER BY 
            SUM(CASE WHEN ur.ranking_position <= 100 THEN 1 ELSE 0 END) DESC,  -- 首先按TOP100数量排序
            AVG(ur.ranking_position) ASC  -- 然后按平均排名排序
        LIMIT 20;
        """
        
        cursor.execute(query4)
        results4 = cursor.fetchall()
        
        with open('global_regional_analysis_queries.sql', 'a', encoding='utf-8') as f:
            f.write("-- 4. 全球区域竞争力综合排名\n")
            f.write(query4 + "\n\n")
        
        print(f"{'排名':<4} {'国家/地区':<20} {'学科数':<8} {'大学数':<8} {'平均排名':<10} {'TOP100':<8} {'TOP100%':<10}")
        print("-" * 85)
        for i, row in enumerate(results4, 1):
            print(f"{i:<4} {row[0]:<20} {row[1]:<8} {row[3]:<8} {row[4]:<10} {row[7]:<8} {row[8]:<10}")
        
        # 5. 学科领域的区域分布分析
        print("\n\n5️⃣ 各学科领域的区域分布情况")
        print("-" * 60)
        
        query5 = """
        SELECT 
            ur.subject_field AS '学科领域',
            COUNT(*) AS '全球总数',
            COUNT(DISTINCT ur.country_region) AS '参与国家数',
            -- 各大洲/主要区域的分布
            SUM(CASE WHEN ur.country_region IN ('USA', 'CANADA') THEN 1 ELSE 0 END) AS '北美洲',
            SUM(CASE WHEN ur.country_region IN ('ENGLAND', 'GERMANY (FED REP GER)', 'FRANCE', 'ITALY', 'SPAIN', 'NETHERLANDS', 'SWITZERLAND', 'SWEDEN', 'NORWAY', 'DENMARK', 'BELGIUM') THEN 1 ELSE 0 END) AS '欧洲',
            SUM(CASE WHEN ur.country_region IN ('CHINA MAINLAND', 'JAPAN', 'SOUTH KOREA', 'SINGAPORE', 'HONG KONG', 'TAIWAN', 'INDIA', 'THAILAND', 'MALAYSIA') THEN 1 ELSE 0 END) AS '亚洲',
            SUM(CASE WHEN ur.country_region IN ('AUSTRALIA', 'NEW ZEALAND') THEN 1 ELSE 0 END) AS '大洋洲',
            -- TOP100中各区域的占比
            ROUND(SUM(CASE WHEN ur.country_region IN ('USA', 'CANADA') AND ur.ranking_position <= 100 THEN 1 ELSE 0 END) / SUM(CASE WHEN ur.ranking_position <= 100 THEN 1 ELSE 0 END) * 100, 1) AS '北美TOP100%',
            ROUND(SUM(CASE WHEN ur.country_region IN ('ENGLAND', 'GERMANY (FED REP GER)', 'FRANCE', 'ITALY', 'SPAIN', 'NETHERLANDS', 'SWITZERLAND', 'SWEDEN', 'NORWAY', 'DENMARK', 'BELGIUM') AND ur.ranking_position <= 100 THEN 1 ELSE 0 END) / SUM(CASE WHEN ur.ranking_position <= 100 THEN 1 ELSE 0 END) * 100, 1) AS '欧洲TOP100%',
            ROUND(SUM(CASE WHEN ur.country_region IN ('CHINA MAINLAND', 'JAPAN', 'SOUTH KOREA', 'SINGAPORE', 'HONG KONG', 'TAIWAN', 'INDIA', 'THAILAND', 'MALAYSIA') AND ur.ranking_position <= 100 THEN 1 ELSE 0 END) / SUM(CASE WHEN ur.ranking_position <= 100 THEN 1 ELSE 0 END) * 100, 1) AS '亚洲TOP100%'
        FROM university_rankings ur
        WHERE ur.ranking_position IS NOT NULL
        GROUP BY ur.subject_field
        ORDER BY COUNT(*) DESC;
        """
        
        cursor.execute(query5)
        results5 = cursor.fetchall()
        
        with open('global_regional_analysis_queries.sql', 'a', encoding='utf-8') as f:
            f.write("-- 5. 各学科领域的区域分布分析\n")
            f.write(query5 + "\n\n")
        
        print(f"{'学科领域':<25} {'总数':<6} {'国家数':<8} {'北美':<6} {'欧洲':<6} {'亚洲':<6} {'北美%':<8} {'欧洲%':<8} {'亚洲%':<8}")
        print("-" * 110)
        for row in results5:
            print(f"{row[0]:<25} {row[1]:<6} {row[2]:<8} {row[3]:<6} {row[4]:<6} {row[5]:<6} {row[7]:<8} {row[8]:<8} {row[9]:<8}")
        
        print(f"\n✅ 全球区域学科表现分析完成！")
        print(f"📄 详细SQL查询已保存到: global_regional_analysis_queries.sql")
        
    except Error as e:
        print(f"❌ 查询执行错误: {e}")
    
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 数据库连接已关闭")

if __name__ == "__main__":
    print("🌍 开始全球不同区域学科表现分析...")
    analyze_global_regional_performance()
    print("\n🎉 分析完成！")