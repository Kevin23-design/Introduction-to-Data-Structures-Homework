"""
实验要求3：通过SQL语句获取华东师范大学在各个学科中的排名
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

def query_ecnu_rankings():
    """查询华东师范大学的排名信息"""
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("华东师范大学学科排名查询")
    print("=" * 80)
    
    # 方法1：使用原始表查询
    print("1. 使用原始表查询华东师范大学排名")
    print("-" * 60)
    
    sql1 = """
    SELECT 
        subject_field AS '学科领域',
        ranking_position AS '排名',
        cites AS '总引用数',
        cites_per_paper AS '每篇论文引用数',
        web_of_science_documents AS 'WoS文档数',
        top_papers AS '顶级论文数'
    FROM university_rankings 
    WHERE institution_name LIKE '%EAST CHINA NORMAL%' 
    ORDER BY ranking_position ASC
    """
    
    print("SQL语句:")
    print(sql1)
    print("\n查询结果:")
    
    cursor.execute(sql1)
    results1 = cursor.fetchall()
    
    if results1:
        print(f"{'学科领域':<25} {'排名':>6} {'总引用数':>10} {'每篇引用':>8} {'WoS文档':>8} {'顶级论文':>8}")
        print("-" * 80)
        for row in results1:
            subject = row[0][:23] + "..." if len(row[0]) > 25 else row[0]
            print(f"{subject:<25} {row[1]:>6} {row[2]:>10,} {row[3]:>8.2f} {row[4]:>8} {row[5]:>8}")
        
        print(f"\n华东师范大学共在 {len(results1)} 个学科中有排名记录")
    else:
        print("未找到华东师范大学的排名数据")
    
    # 方法2：使用优化Schema查询
    print("\n\n2. 使用优化Schema查询华东师范大学排名")
    print("-" * 60)
    
    sql2 = """
    SELECT 
        s.subject_name AS '学科领域',
        s.subject_category AS '学科类别',
        r.ranking_position AS '排名',
        r.total_cites AS '总引用数',
        r.cites_per_paper AS '每篇论文引用数',
        r.web_of_science_documents AS 'WoS文档数',
        r.top_papers AS '顶级论文数',
        c.country_name AS '国家/地区'
    FROM rankings r
    JOIN institutions i ON r.institution_id = i.id
    JOIN subjects s ON r.subject_id = s.id
    JOIN countries c ON i.country_id = c.id
    WHERE i.institution_name LIKE '%EAST CHINA NORMAL%'
    ORDER BY r.ranking_position ASC
    """
    
    print("SQL语句:")
    print(sql2)
    print("\n查询结果:")
    
    cursor.execute(sql2)
    results2 = cursor.fetchall()
    
    if results2:
        print(f"{'学科领域':<25} {'类别':<10} {'排名':>6} {'总引用数':>10} {'每篇引用':>8}")
        print("-" * 70)
        for row in results2:
            subject = row[0][:23] + "..." if len(row[0]) > 25 else row[0]
            category = row[1][:8] + "..." if len(row[1]) > 10 else row[1]
            print(f"{subject:<25} {category:<10} {row[2]:>6} {row[3]:>10,} {row[4]:>8.2f}")
        
        print(f"\n华东师范大学共在 {len(results2)} 个学科中有排名记录")
        print(f"学校所在地区: {results2[0][7]}")
    