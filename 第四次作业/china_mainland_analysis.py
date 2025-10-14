"""
实验要求4：通过SQL语句获取中国（大陆地区）大学在各个学科中的表现
表现用百分位体现
"""

import mysql.connector
from mysql.connector import Error

def connect_to_database():
    """连接到数据库"""
    config = {
        'host': 'localhost',
        'user': 'root',
        'password': 'zzy419220',
        'database': 'university_ranking'
    }
    
    try:
        connection = mysql.connector.connect(**config)
        return connection
    except Error as e:
        print(f"数据库连接失败: {e}")
        return None

def analyze_china_mainland_performance():
    """分析中国大陆大学在各学科中的表现"""
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("中国（大陆地区）大学在各个学科中的表现分析")
    print("=" * 80)
    
    # 1. 各学科中国大陆大学的百分位表现
    print("1. 各学科中国大陆大学的百分位表现")
    print("-" * 60)
    
    sql1 = """
    SELECT 
        ur.subject_field AS '学科领域',
        COUNT(*) AS '中国大陆大学数',
        total_stats.total_institutions AS '全球大学总数',
        ROUND(COUNT(*) / total_stats.total_institutions * 100, 2) AS '参与度(%)',
        MIN(ur.ranking_position) AS '最好排名',
        MAX(ur.ranking_position) AS '最差排名',
        AVG(ur.ranking_position) AS '平均排名',
        ROUND(AVG(ur.ranking_position) / total_stats.total_institutions * 100, 2) AS '平均排名百分位(%)',
        -- 计算前10%、前25%、前50%的大学数量
        SUM(CASE WHEN ur.ranking_position <= total_stats.total_institutions * 0.1 THEN 1 ELSE 0 END) AS 'TOP10%数量',
        SUM(CASE WHEN ur.ranking_position <= total_stats.total_institutions * 0.25 THEN 1 ELSE 0 END) AS 'TOP25%数量',
        SUM(CASE WHEN ur.ranking_position <= total_stats.total_institutions * 0.5 THEN 1 ELSE 0 END) AS 'TOP50%数量'
    FROM university_rankings ur
    JOIN (
        SELECT 
            subject_field,
            COUNT(*) as total_institutions
        FROM university_rankings 
        WHERE ranking_position IS NOT NULL
        GROUP BY subject_field
    ) total_stats ON ur.subject_field = total_stats.subject_field
    WHERE ur.country_region = 'CHINA MAINLAND' 
      AND ur.ranking_position IS NOT NULL
    GROUP BY ur.subject_field, total_stats.total_institutions
    ORDER BY AVG(ur.ranking_position) ASC
    """
    
    print("SQL语句:")
    print(sql1)
    print("\n查询结果:")
    
    cursor.execute(sql1)
    results1 = cursor.fetchall()
    
    if results1:
        print(f"{'学科领域':<25} {'中国数':>6} {'全球数':>6} {'参与度%':>7} {'最好':>5} {'平均':>6} {'百分位%':>7} {'TOP10%':>6} {'TOP25%':>6} {'TOP50%':>6}")
        print("-" * 100)
        for row in results1:
            subject = row[0][:23] + "..." if len(row[0]) > 25 else row[0]
            print(f"{subject:<25} {row[1]:>6} {row[2]:>6} {row[3]:>7}% {row[4]:>5} {row[6]:>6.0f} {row[7]:>7}% {row[8]:>6} {row[9]:>6} {row[10]:>6}")
    
    # 2. 中国大陆大学在各学科的优势分析
    print("\n\n2. 中国大陆大学在各学科的优势分析（按TOP10%比例排序）")
    print("-" * 60)
    
    sql2 = """
    SELECT 
        ur.subject_field AS '学科领域',
        COUNT(*) AS '中国大陆大学数',
        SUM(CASE WHEN ur.ranking_position <= total_stats.total_institutions * 0.1 THEN 1 ELSE 0 END) AS 'TOP10%数量',
        ROUND(SUM(CASE WHEN ur.ranking_position <= total_stats.total_institutions * 0.1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS 'TOP10%比例(%)',
        SUM(CASE WHEN ur.ranking_position <= total_stats.total_institutions * 0.25 THEN 1 ELSE 0 END) AS 'TOP25%数量',
        ROUND(SUM(CASE WHEN ur.ranking_position <= total_stats.total_institutions * 0.25 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS 'TOP25%比例(%)'
    FROM university_rankings ur
    JOIN (
        SELECT 
            subject_field,
            COUNT(*) as total_institutions
        FROM university_rankings 
        WHERE ranking_position IS NOT NULL
        GROUP BY subject_field
    ) total_stats ON ur.subject_field = total_stats.subject_field
    WHERE ur.country_region = 'CHINA MAINLAND' 
      AND ur.ranking_position IS NOT NULL
    GROUP BY ur.subject_field
    HAVING COUNT(*) >= 10  -- 只分析参与大学数量>=10的学科
    ORDER BY ROUND(SUM(CASE WHEN ur.ranking_position <= total_stats.total_institutions * 0.1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) DESC
    """
    
    print("SQL语句:")
    print(sql2)
    print("\n查询结果:")
    
    cursor.execute(sql2)
    results2 = cursor.fetchall()
    
    if results2:
        print(f"{'学科领域':<25} {'中国数':>6} {'TOP10%数':>7} {'TOP10%比例':>9} {'TOP25%数':>7} {'TOP25%比例':>9}")
        print("-" * 75)
        for row in results2:
            subject = row[0][:23] + "..." if len(row[0]) > 25 else row[0]
            print(f"{subject:<25} {row[1]:>6} {row[2]:>7} {row[3]:>8}% {row[4]:>7} {row[5]:>8}%")
    
    # 3. 中国大陆顶尖大学分析（各学科排名前100的大学）
    print("\n\n3. 中国大陆各学科TOP100大学分布")
    print("-" * 60)
    
    sql3 = """
    SELECT 
        subject_field AS '学科领域',
        COUNT(*) AS '进入TOP100数量',
        GROUP_CONCAT(
            CONCAT(institution_name, '(', ranking_position, ')')
            ORDER BY ranking_position 
            SEPARATOR ', '
        ) AS '具体大学及排名'
    FROM university_rankings 
    WHERE country_region = 'CHINA MAINLAND' 
      AND ranking_position <= 100
      AND ranking_position IS NOT NULL
    GROUP BY subject_field
    ORDER BY COUNT(*) DESC
    """
    
    print("SQL语句:")
    print(sql3)
    print("\n查询结果:")
    
    cursor.execute(sql3)
    results3 = cursor.fetchall()
    
    if results3:
        for subject, count, universities in results3:
            print(f"\n{subject}: {count}所大学进入TOP100")
            # 限制显示长度，避免输出过长
            if len(universities) > 200:
                universities = universities[:200] + "..."
            print(f"  {universities}")
    
    # 4. 总体统计
    print("\n\n4. 中国大陆大学总体表现统计")
    print("-" * 60)
    
    sql4 = """
    SELECT 
        COUNT(DISTINCT subject_field) AS '参与学科数',
        COUNT(*) AS '总参与大学次数',
        COUNT(DISTINCT institution_name) AS '参与大学总数',
        SUM(CASE WHEN ranking_position <= 100 THEN 1 ELSE 0 END) AS 'TOP100总数',
        SUM(CASE WHEN ranking_position <= 500 THEN 1 ELSE 0 END) AS 'TOP500总数',
        ROUND(AVG(ranking_position), 2) AS '总体平均排名',
        MIN(ranking_position) AS '最好单科排名',
        MAX(ranking_position) AS '最差单科排名'
    FROM university_rankings 
    WHERE country_region = 'CHINA MAINLAND' 
      AND ranking_position IS NOT NULL
    """
    
    print("SQL语句:")
    print(sql4)
    print("\n查询结果:")
    
    cursor.execute(sql4)
    results4 = cursor.fetchone()
    
    if results4:
        print(f"参与学科数: {results4[0]}")
        print(f"总参与大学次数: {results4[1]}")
        print(f"参与大学总数: {results4[2]}")
        print(f"TOP100总数: {results4[3]}")
        print(f"TOP500总数: {results4[4]}")
        print(f"总体平均排名: {results4[5]}")
        print(f"最好单科排名: {results4[6]}")
        print(f"最差单科排名: {results4[7]}")
    
    cursor.close()
    connection.close()

def export_china_mainland_sql():
    """导出中国大陆大学表现分析的SQL语句"""
    sql_queries = """
-- 中国（大陆地区）大学在各个学科中的表现分析SQL语句集合
-- 实验要求4：通过SQL语句获取中国（大陆地区）大学在各个学科中的表现

-- 1. 各学科中国大陆大学的百分位表现
SELECT 
    subject_field AS '学科领域',
    COUNT(*) AS '中国大陆大学数',
    total_stats.total_institutions AS '全球大学总数',
    ROUND(COUNT(*) / total_stats.total_institutions * 100, 2) AS '参与度(%)',
    MIN(ranking_position) AS '最好排名',
    MAX(ranking_position) AS '最差排名',
    AVG(ranking_position) AS '平均排名',
    ROUND(AVG(ranking_position) / total_stats.total_institutions * 100, 2) AS '平均排名百分位(%)',
    SUM(CASE WHEN ranking_position <= total_stats.total_institutions * 0.1 THEN 1 ELSE 0 END) AS 'TOP10%数量',
    SUM(CASE WHEN ranking_position <= total_stats.total_institutions * 0.25 THEN 1 ELSE 0 END) AS 'TOP25%数量',
    SUM(CASE WHEN ranking_position <= total_stats.total_institutions * 0.5 THEN 1 ELSE 0 END) AS 'TOP50%数量'
FROM university_rankings ur
JOIN (
    SELECT 
        subject_field,
        COUNT(*) as total_institutions
    FROM university_rankings 
    WHERE ranking_position IS NOT NULL
    GROUP BY subject_field
) total_stats ON ur.subject_field = total_stats.subject_field
WHERE ur.country_region = 'CHINA MAINLAND' 
  AND ur.ranking_position IS NOT NULL
GROUP BY ur.subject_field, total_stats.total_institutions
ORDER BY AVG(ur.ranking_position) ASC;

-- 2. 中国大陆大学在各学科的优势分析（按TOP10%比例排序）
SELECT 
    subject_field AS '学科领域',
    COUNT(*) AS '中国大陆大学数',
    SUM(CASE WHEN ranking_position <= total_stats.total_institutions * 0.1 THEN 1 ELSE 0 END) AS 'TOP10%数量',
    ROUND(SUM(CASE WHEN ranking_position <= total_stats.total_institutions * 0.1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS 'TOP10%比例(%)',
    SUM(CASE WHEN ranking_position <= total_stats.total_institutions * 0.25 THEN 1 ELSE 0 END) AS 'TOP25%数量',
    ROUND(SUM(CASE WHEN ranking_position <= total_stats.total_institutions * 0.25 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS 'TOP25%比例(%)'
FROM university_rankings ur
JOIN (
    SELECT 
        subject_field,
        COUNT(*) as total_institutions
    FROM university_rankings 
    WHERE ranking_position IS NOT NULL
    GROUP BY subject_field
) total_stats ON ur.subject_field = total_stats.subject_field
WHERE ur.country_region = 'CHINA MAINLAND' 
  AND ur.ranking_position IS NOT NULL
GROUP BY ur.subject_field
HAVING COUNT(*) >= 10
ORDER BY ROUND(SUM(CASE WHEN ranking_position <= total_stats.total_institutions * 0.1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) DESC;

-- 3. 中国大陆各学科TOP100大学分布
SELECT 
    subject_field AS '学科领域',
    COUNT(*) AS '进入TOP100数量',
    GROUP_CONCAT(
        CONCAT(institution_name, '(', ranking_position, ')')
        ORDER BY ranking_position 
        SEPARATOR ', '
    ) AS '具体大学及排名'
FROM university_rankings 
WHERE country_region = 'CHINA MAINLAND' 
  AND ranking_position <= 100
  AND ranking_position IS NOT NULL
GROUP BY subject_field
ORDER BY COUNT(*) DESC;

-- 4. 中国大陆大学总体表现统计
SELECT 
    COUNT(DISTINCT subject_field) AS '参与学科数',
    COUNT(*) AS '总参与大学次数',
    COUNT(DISTINCT institution_name) AS '参与大学总数',
    SUM(CASE WHEN ranking_position <= 100 THEN 1 ELSE 0 END) AS 'TOP100总数',
    SUM(CASE WHEN ranking_position <= 500 THEN 1 ELSE 0 END) AS 'TOP500总数',
    ROUND(AVG(ranking_position), 2) AS '总体平均排名',
    MIN(ranking_position) AS '最好单科排名',
    MAX(ranking_position) AS '最差单科排名'
FROM university_rankings 
WHERE country_region = 'CHINA MAINLAND' 
  AND ranking_position IS NOT NULL;
"""
    
    # 将SQL语句保存到文件
    with open('china_mainland_performance_queries.sql', 'w', encoding='utf-8') as f:
        f.write(sql_queries)
    
    print("中国大陆大学表现分析SQL语句已导出到文件: china_mainland_performance_queries.sql")

def main():
    """主函数"""
    print("实验要求4：中国（大陆地区）大学在各个学科中的表现分析")
    print("=" * 100)
    
    # 执行中国大陆大学表现分析
    analyze_china_mainland_performance()
    
    # 导出SQL语句
    print("\n" + "=" * 100)
    export_china_mainland_sql()
    
    print("\n" + "=" * 100)
    print("✓ 实验要求4完成：中国大陆大学学科表现百分位分析！")

if __name__ == "__main__":
    main()