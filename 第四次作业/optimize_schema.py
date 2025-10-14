"""
实验要求2：设计优化的数据库Schema
分析当前数据结构并设计更好的规范化Schema
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

def analyze_current_schema():
    """分析当前的数据库结构"""
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("当前数据库Schema分析")
    print("=" * 60)
    
    # 1. 查看表结构
    print("1. 当前表结构:")
    cursor.execute("DESCRIBE university_rankings")
    columns = cursor.fetchall()
    for column in columns:
        print(f"   {column[0]} - {column[1]} - {column[2]} - {column[3]}")
    
    # 2. 分析数据重复情况
    print("\n2. 数据重复性分析:")
    
    # 机构名称重复情况
    cursor.execute("""
        SELECT institution_name, COUNT(*) as count
        FROM university_rankings 
        GROUP BY institution_name 
        ORDER BY count DESC 
        LIMIT 10
    """)
    institutions = cursor.fetchall()
    print("   机构名称重复次数TOP10:")
    for inst, count in institutions:
        print(f"     {inst}: {count} 次")
    
    # 国家/地区重复情况
    cursor.execute("""
        SELECT country_region, COUNT(*) as count
        FROM university_rankings 
        GROUP BY country_region 
        ORDER BY count DESC 
        LIMIT 10
    """)
    countries = cursor.fetchall()
    print("\n   国家/地区重复次数TOP10:")
    for country, count in countries:
        print(f"     {country}: {count} 次")
    
    # 学科重复情况
    cursor.execute("""
        SELECT subject_field, COUNT(*) as count
        FROM university_rankings 
        GROUP BY subject_field 
        ORDER BY count DESC
    """)
    subjects = cursor.fetchall()
    print("\n   各学科记录数:")
    for subject, count in subjects:
        print(f"     {subject}: {count} 次")
    
    # 3. 存储空间分析
    print("\n3. 存储空间分析:")
    cursor.execute("SELECT COUNT(*) FROM university_rankings")
    total_records = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT institution_name) FROM university_rankings")
    unique_institutions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT country_region) FROM university_rankings")
    unique_countries = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT subject_field) FROM university_rankings")
    unique_subjects = cursor.fetchone()[0]
    
    print(f"   总记录数: {total_records}")
    print(f"   唯一机构数: {unique_institutions} (重复率: {(1-unique_institutions/total_records)*100:.1f}%)")
    print(f"   唯一国家数: {unique_countries} (重复率: {(1-unique_countries/total_records)*100:.1f}%)")
    print(f"   唯一学科数: {unique_subjects} (重复率: {(1-unique_subjects/total_records)*100:.1f}%)")
    
    cursor.close()
    connection.close()

def create_optimized_schema():
    """创建优化的数据库Schema"""
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("\n优化Schema设计与实现")
    print("=" * 60)
    
    try:
        # 创建国家/地区表
        print("1. 创建countries表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            country_name VARCHAR(200) NOT NULL UNIQUE,
            region_type ENUM('MAINLAND', 'ISLAND', 'OTHER') DEFAULT 'OTHER',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_country_name (country_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建学科表
        print("2. 创建subjects表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subject_name VARCHAR(200) NOT NULL UNIQUE,
            subject_category ENUM('SCIENCE', 'ENGINEERING', 'MEDICINE', 'SOCIAL', 'OTHER') DEFAULT 'OTHER',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_subject_name (subject_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建机构表
        print("3. 创建institutions表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS institutions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            institution_name VARCHAR(500) NOT NULL UNIQUE,
            country_id INT NOT NULL,
            institution_type ENUM('UNIVERSITY', 'RESEARCH_INSTITUTE', 'GOVERNMENT', 'SYSTEM', 'OTHER') DEFAULT 'OTHER',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE,
            INDEX idx_institution_name (institution_name),
            INDEX idx_country_id (country_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建优化的排名表
        print("4. 创建rankings表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            institution_id INT NOT NULL,
            subject_id INT NOT NULL,
            ranking_position INT,
            web_of_science_documents INT,
            total_cites BIGINT,
            cites_per_paper DECIMAL(10,2),
            top_papers INT,
            ranking_year YEAR DEFAULT 2024,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            UNIQUE KEY uk_institution_subject_year (institution_id, subject_id, ranking_year),
            INDEX idx_ranking_position (ranking_position),
            INDEX idx_institution_id (institution_id),
            INDEX idx_subject_id (subject_id),
            INDEX idx_year (ranking_year)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        print("✓ 优化Schema创建完成")
        
    except Error as e:
        print(f"创建优化Schema时出错: {e}")
    
    cursor.close()
    connection.close()

def migrate_data_to_optimized_schema():
    """将数据迁移到优化的Schema"""
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("\n数据迁移到优化Schema")
    print("=" * 60)
    
    try:
        # 1. 迁移国家数据
        print("1. 迁移国家/地区数据...")
        cursor.execute("""
        INSERT IGNORE INTO countries (country_name, region_type)
        SELECT DISTINCT 
            country_region,
            CASE 
                WHEN country_region LIKE '%MAINLAND%' THEN 'MAINLAND'
                WHEN country_region IN ('TAIWAN', 'SINGAPORE', 'HONG KONG', 'CYPRUS', 'MALTA') THEN 'ISLAND'
                ELSE 'OTHER'
            END
        FROM university_rankings
        """)
        country_count = cursor.rowcount
        print(f"   插入 {country_count} 个国家/地区")
        
        # 2. 迁移学科数据
        print("2. 迁移学科数据...")
        cursor.execute("""
        INSERT IGNORE INTO subjects (subject_name, subject_category)
        SELECT DISTINCT 
            subject_field,
            CASE 
                WHEN subject_field LIKE '%MEDICINE%' OR subject_field LIKE '%CLINICAL%' 
                     OR subject_field LIKE '%PHARMACOLOGY%' OR subject_field LIKE '%IMMUNOLOGY%' 
                     OR subject_field LIKE '%MICROBIOLOGY%' OR subject_field LIKE '%NEUROSCIENCE%'
                     OR subject_field LIKE '%PSYCHIATRY%' THEN 'MEDICINE'
                WHEN subject_field LIKE '%ENGINEERING%' OR subject_field LIKE '%COMPUTER%' 
                     OR subject_field LIKE '%MATERIALS%' THEN 'ENGINEERING'
                WHEN subject_field LIKE '%CHEMISTRY%' OR subject_field LIKE '%PHYSICS%' 
                     OR subject_field LIKE '%BIOLOGY%' OR subject_field LIKE '%MATHEMATICS%'
                     OR subject_field LIKE '%GEOSCIENCES%' OR subject_field LIKE '%SPACE%'
                     OR subject_field LIKE '%MOLECULAR%' OR subject_field LIKE '%ENVIRONMENT%'
                     OR subject_field LIKE '%PLANT%' OR subject_field LIKE '%AGRICULTURAL%' THEN 'SCIENCE'
                WHEN subject_field LIKE '%SOCIAL%' OR subject_field LIKE '%ECONOMICS%' 
                     OR subject_field LIKE '%PSYCHOLOGY%' THEN 'SOCIAL'
                ELSE 'OTHER'
            END
        FROM university_rankings
        """)
        subject_count = cursor.rowcount
        print(f"   插入 {subject_count} 个学科")
        
        # 3. 迁移机构数据
        print("3. 迁移机构数据...")
        cursor.execute("""
        INSERT IGNORE INTO institutions (institution_name, country_id, institution_type)
        SELECT DISTINCT 
            ur.institution_name,
            c.id,
            CASE 
                WHEN ur.institution_name LIKE '%UNIVERSITY%' OR ur.institution_name LIKE '%大学%' THEN 'UNIVERSITY'
                WHEN ur.institution_name LIKE '%ACADEMY%' OR ur.institution_name LIKE '%INSTITUTE%' 
                     OR ur.institution_name LIKE '%研究%' THEN 'RESEARCH_INSTITUTE'
                WHEN ur.institution_name LIKE '%SYSTEM%' THEN 'SYSTEM'
                WHEN ur.institution_name LIKE '%DEPARTMENT%' OR ur.institution_name LIKE '%MINISTRY%' THEN 'GOVERNMENT'
                ELSE 'OTHER'
            END
        FROM university_rankings ur
        JOIN countries c ON c.country_name = ur.country_region
        """)
        institution_count = cursor.rowcount
        print(f"   插入 {institution_count} 个机构")
        
        # 4. 迁移排名数据
        print("4. 迁移排名数据...")
        cursor.execute("""
        INSERT IGNORE INTO rankings 
        (institution_id, subject_id, ranking_position, web_of_science_documents, 
         total_cites, cites_per_paper, top_papers)
        SELECT 
            i.id,
            s.id,
            ur.ranking_position,
            ur.web_of_science_documents,
            ur.cites,
            ur.cites_per_paper,
            ur.top_papers
        FROM university_rankings ur
        JOIN institutions i ON i.institution_name = ur.institution_name
        JOIN subjects s ON s.subject_name = ur.subject_field
        JOIN countries c ON c.country_name = ur.country_region AND i.country_id = c.id
        """)
        ranking_count = cursor.rowcount
        print(f"   插入 {ranking_count} 条排名记录")
        
        connection.commit()
        print("✓ 数据迁移完成")
        
    except Error as e:
        print(f"数据迁移时出错: {e}")
        connection.rollback()
    
    cursor.close()
    connection.close()

def analyze_optimized_schema():
    """分析优化后的Schema效果"""
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    print("\n优化Schema效果分析")
    print("=" * 60)
    
    # 1. 存储空间对比
    print("1. 存储空间对比:")
    cursor.execute("SELECT COUNT(*) FROM university_rankings")
    old_records = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM countries")
    countries_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM subjects")
    subjects_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM institutions")
    institutions_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM rankings")
    rankings_count = cursor.fetchone()[0]
    
    print(f"   原始表记录数: {old_records}")
    print(f"   优化后总记录数: {countries_count + subjects_count + institutions_count + rankings_count}")
    print(f"     - 国家表: {countries_count}")
    print(f"     - 学科表: {subjects_count}")
    print(f"     - 机构表: {institutions_count}")
    print(f"     - 排名表: {rankings_count}")
    
    # 2. 数据一致性验证
    print("\n2. 数据一致性验证:")
    cursor.execute("""
        SELECT COUNT(*) FROM rankings r
        JOIN institutions i ON r.institution_id = i.id
        JOIN subjects s ON r.subject_id = s.id
        JOIN countries c ON i.country_id = c.id
    """)
    joined_records = cursor.fetchone()[0]
    print(f"   关联查询记录数: {joined_records}")
    print(f"   数据完整性: {'✓ 通过' if joined_records == rankings_count else '✗ 失败'}")
    
    # 3. 查询性能示例
    print("\n3. 优化Schema查询示例:")
    
    # 示例查询1：按国家统计机构数量
    cursor.execute("""
        SELECT c.country_name, COUNT(DISTINCT i.id) as institution_count
        FROM countries c
        JOIN institutions i ON c.id = i.country_id
        GROUP BY c.country_name
        ORDER BY institution_count DESC
        LIMIT 5
    """)
    country_stats = cursor.fetchall()
    print("   各国机构数量TOP5:")
    for country, count in country_stats:
        print(f"     {country}: {count} 个机构")
    
    # 示例查询2：按学科类别统计
    cursor.execute("""
        SELECT s.subject_category, COUNT(*) as ranking_count
        FROM subjects s
        JOIN rankings r ON s.id = r.subject_id
        GROUP BY s.subject_category
        ORDER BY ranking_count DESC
    """)
    category_stats = cursor.fetchall()
    print("\n   各学科类别排名记录数:")
    for category, count in category_stats:
        print(f"     {category}: {count} 条记录")
    
    cursor.close()
    connection.close()

def main():
    """主函数"""
    print("实验要求2：设计优化的数据库Schema")
    print("=" * 80)
    
    # 步骤1：分析当前Schema
    analyze_current_schema()
    
    # 步骤2：创建优化Schema
    create_optimized_schema()
    
    # 步骤3：数据迁移
    migrate_data_to_optimized_schema()
    
    # 步骤4：效果分析
    analyze_optimized_schema()
    
    print("\n" + "=" * 80)
    print("✓ 实验要求2完成：优化的数据库Schema设计并实现！")

if __name__ == "__main__":
    main()