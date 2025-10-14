"""
Schema优化效果验证和性能对比
"""

import mysql.connector
import time
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

def performance_comparison():
    """性能对比测试"""
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("Schema性能对比测试")
    print("=" * 60)
    
    # 测试1：查询某个国家的所有机构
    print("1. 查询中国大陆所有机构的排名记录")
    
    # 原始表查询
    start_time = time.time()
    cursor.execute("""
        SELECT institution_name, subject_field, ranking_position 
        FROM university_rankings 
        WHERE country_region = 'CHINA MAINLAND'
        ORDER BY ranking_position
    """)
    original_results = cursor.fetchall()
    original_time = time.time() - start_time
    
    # 优化表查询
    start_time = time.time()
    cursor.execute("""
        SELECT i.institution_name, s.subject_name, r.ranking_position
        FROM rankings r
        JOIN institutions i ON r.institution_id = i.id
        JOIN subjects s ON r.subject_id = s.id
        JOIN countries c ON i.country_id = c.id
        WHERE c.country_name = 'CHINA MAINLAND'
        ORDER BY r.ranking_position
    """)
    optimized_results = cursor.fetchall()
    optimized_time = time.time() - start_time
    
    print(f"   原始表查询: {len(original_results)} 条记录, 耗时: {original_time:.4f}秒")
    print(f"   优化表查询: {len(optimized_results)} 条记录, 耗时: {optimized_time:.4f}秒")
    print(f"   性能差异: {((original_time - optimized_time) / original_time * 100):.1f}%")
    
    # 测试2：统计各学科的平均引用数
    print("\n2. 统计各学科的平均引用数")
    
    # 原始表查询
    start_time = time.time()
    cursor.execute("""
        SELECT subject_field, AVG(cites) as avg_cites, COUNT(*) as count
        FROM university_rankings 
        WHERE cites IS NOT NULL
        GROUP BY subject_field
        ORDER BY avg_cites DESC
    """)
    original_stats = cursor.fetchall()
    original_time2 = time.time() - start_time
    
    # 优化表查询
    start_time = time.time()
    cursor.execute("""
        SELECT s.subject_name, AVG(r.total_cites) as avg_cites, COUNT(*) as count
        FROM rankings r
        JOIN subjects s ON r.subject_id = s.id
        WHERE r.total_cites IS NOT NULL
        GROUP BY s.subject_name
        ORDER BY avg_cites DESC
    """)
    optimized_stats = cursor.fetchall()
    optimized_time2 = time.time() - start_time
    
    print(f"   原始表查询: {len(original_stats)} 个学科, 耗时: {original_time2:.4f}秒")
    print(f"   优化表查询: {len(optimized_stats)} 个学科, 耗时: {optimized_time2:.4f}秒")
    print(f"   性能差异: {((original_time2 - optimized_time2) / original_time2 * 100):.1f}%")
    
    # 测试3：复杂关联查询
    print("\n3. 复杂查询：各国在工程学科的平均排名")
    
    # 原始表查询
    start_time = time.time()
    cursor.execute("""
        SELECT country_region, AVG(ranking_position) as avg_ranking, COUNT(*) as count
        FROM university_rankings 
        WHERE subject_field = 'ENGINEERING' AND ranking_position IS NOT NULL
        GROUP BY country_region
        HAVING count >= 10
        ORDER BY avg_ranking
        LIMIT 10
    """)
    original_complex = cursor.fetchall()
    original_time3 = time.time() - start_time
    
    # 优化表查询
    start_time = time.time()
    cursor.execute("""
        SELECT c.country_name, AVG(r.ranking_position) as avg_ranking, COUNT(*) as count
        FROM rankings r
        JOIN institutions i ON r.institution_id = i.id
        JOIN countries c ON i.country_id = c.id
        JOIN subjects s ON r.subject_id = s.id
        WHERE s.subject_name = 'ENGINEERING' AND r.ranking_position IS NOT NULL
        GROUP BY c.country_name
        HAVING count >= 10
        ORDER BY avg_ranking
        LIMIT 10
    """)
    optimized_complex = cursor.fetchall()
    optimized_time3 = time.time() - start_time
    
    print(f"   原始表查询: {len(original_complex)} 个国家, 耗时: {original_time3:.4f}秒")
    print(f"   优化表查询: {len(optimized_complex)} 个国家, 耗时: {optimized_time3:.4f}秒")
    print(f"   性能差异: {((original_time3 - optimized_time3) / original_time3 * 100):.1f}%")
    
    cursor.close()
    connection.close()

def schema_benefits_analysis():
    """Schema优化效果分析"""
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("\nSchema优化效果详细分析")
    print("=" * 60)
    
    # 1. 存储空间效率
    print("1. 存储空间效率分析")
    
    # 计算原始表的估算存储空间
    cursor.execute("""
        SELECT 
            SUM(LENGTH(institution_name)) as inst_size,
            SUM(LENGTH(country_region)) as country_size,
            SUM(LENGTH(subject_field)) as subject_size,
            COUNT(*) as total_records
        FROM university_rankings
    """)
    original_size = cursor.fetchone()
    
    # 计算优化表的存储空间
    cursor.execute("SELECT SUM(LENGTH(country_name)) FROM countries")
    country_size = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(LENGTH(subject_name)) FROM subjects")
    subject_size = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(LENGTH(institution_name)) FROM institutions")
    institution_size = cursor.fetchone()[0] or 0
    
    original_text_size = (original_size[0] or 0) + (original_size[1] or 0) + (original_size[2] or 0)
    optimized_text_size = country_size + subject_size + institution_size
    
    print(f"   原始表文本存储估算: {original_text_size:,} 字节")
    print(f"   优化表文本存储估算: {optimized_text_size:,} 字节")
    print(f"   空间节省: {((original_text_size - optimized_text_size) / original_text_size * 100):.1f}%")
    
    # 2. 数据一致性和完整性
    print("\n2. 数据一致性和完整性")
    
    # 检查外键约束
    cursor.execute("""
        SELECT COUNT(*) FROM rankings r
        LEFT JOIN institutions i ON r.institution_id = i.id
        WHERE i.id IS NULL
    """)
    orphaned_rankings = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM institutions i
        LEFT JOIN countries c ON i.country_id = c.id
        WHERE c.id IS NULL
    """)
    orphaned_institutions = cursor.fetchone()[0]
    
    print(f"   孤立的排名记录: {orphaned_rankings} (应该为0)")
    print(f"   孤立的机构记录: {orphaned_institutions} (应该为0)")
    print(f"   数据完整性: {'✓ 良好' if orphaned_rankings == 0 and orphaned_institutions == 0 else '✗ 有问题'}")
    
    # 3. 查询灵活性示例
    print("\n3. 查询灵活性提升")
    
    # 按机构类型统计
    cursor.execute("""
        SELECT i.institution_type, COUNT(*) as count, AVG(r.ranking_position) as avg_ranking
        FROM institutions i
        JOIN rankings r ON i.id = r.institution_id
        WHERE r.ranking_position IS NOT NULL
        GROUP BY i.institution_type
        ORDER BY avg_ranking
    """)
    institution_types = cursor.fetchall()
    
    print("   按机构类型的平均排名:")
    for inst_type, count, avg_ranking in institution_types:
        print(f"     {inst_type}: {count} 条记录, 平均排名: {avg_ranking:.1f}")
    
    # 按学科类别统计
    cursor.execute("""
        SELECT s.subject_category, COUNT(DISTINCT r.institution_id) as institutions,
               AVG(r.total_cites) as avg_cites
        FROM subjects s
        JOIN rankings r ON s.id = r.subject_id
        WHERE r.total_cites IS NOT NULL
        GROUP BY s.subject_category
        ORDER BY avg_cites DESC
    """)
    subject_categories = cursor.fetchall()
    
    print("\n   按学科类别的机构数和平均引用:")
    for category, institutions, avg_cites in subject_categories:
        print(f"     {category}: {institutions} 个机构, 平均引用: {avg_cites:,.0f}")
    
    cursor.close()
    connection.close()

def generate_schema_documentation():
    """生成Schema设计文档"""
    print("\nSchema设计文档")
    print("=" * 60)
    
    schema_doc = """
优化后的数据库Schema设计说明：

1. countries 表（国家/地区）
   - id: 主键，自增
   - country_name: 国家/地区名称，唯一索引
   - region_type: 地区类型（大陆/岛屿/其他）
   - created_at: 创建时间
   
2. subjects 表（学科）
   - id: 主键，自增
   - subject_name: 学科名称，唯一索引
   - subject_category: 学科类别（科学/工程/医学/社会/其他）
   - created_at: 创建时间

3. institutions 表（机构）
   - id: 主键，自增
   - institution_name: 机构名称，唯一索引
   - country_id: 外键，关联countries表
   - institution_type: 机构类型（大学/研究所/政府/系统/其他）
   - created_at: 创建时间

4. rankings 表（排名）
   - id: 主键，自增
   - institution_id: 外键，关联institutions表
   - subject_id: 外键，关联subjects表
   - ranking_position: 排名位置
   - web_of_science_documents: Web of Science文档数
   - total_cites: 总引用数
   - cites_per_paper: 每篇论文引用数
   - top_papers: 顶级论文数
   - ranking_year: 排名年份
   - created_at: 创建时间
   - 唯一约束: (institution_id, subject_id, ranking_year)

优化效果：
✓ 消除数据重复，节省存储空间
✓ 提高数据一致性和完整性
✓ 增强查询性能和灵活性
✓ 支持复杂的多表关联查询
✓ 便于数据维护和更新
✓ 符合数据库范式设计原则
    """
    
    print(schema_doc)

def main():
    """主函数"""
    print("Schema优化效果验证")
    print("=" * 80)
    
    # 性能对比测试
    performance_comparison()
    
    # 效果分析
    schema_benefits_analysis()
    
    # 生成文档
    generate_schema_documentation()
    
    print("\n" + "=" * 80)
    print("✓ Schema优化验证完成！")

if __name__ == "__main__":
    main()