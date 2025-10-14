import mysql.connector
import pandas as pd
import os
import re
from mysql.connector import Error

def get_db_config():
    """获取数据库配置"""
    print("请输入MySQL连接信息:")
    host = input("主机地址 (默认: localhost): ").strip() or "localhost"
    user = input("用户名 (默认: root): ").strip() or "root"
    password = input("密码: ").strip()
    
    return {
        'host': host,
        'user': user,
        'password': password,
        'database': 'university_ranking'
    }

def create_database_and_table(config):
    """创建数据库和表"""
    try:
        # 连接MySQL服务器
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password']
        )
        cursor = connection.cursor()
        
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ 数据库 '{config['database']}' 创建成功")
        cursor.close()
        connection.close()
        
        # 连接到新创建的数据库
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # 删除已存在的表（如果需要重新创建）
        cursor.execute("DROP TABLE IF EXISTS university_rankings")
        
        # 创建表
        create_table_sql = """
        CREATE TABLE university_rankings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ranking_position INT,
            institution_name VARCHAR(500) NOT NULL,
            country_region VARCHAR(200) NOT NULL,
            subject_field VARCHAR(200) NOT NULL,
            web_of_science_documents INT,
            cites BIGINT,
            cites_per_paper DECIMAL(10,2),
            top_papers INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_institution (institution_name),
            INDEX idx_country (country_region),
            INDEX idx_subject (subject_field),
            INDEX idx_ranking (ranking_position)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_sql)
        print("✓ 数据表创建成功")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"✗ 创建数据库或表时出错: {e}")
        return False

def parse_csv_line(line):
    """解析CSV行数据"""
    # 使用正则表达式提取引号中的数据
    pattern = r'"([^"]+)"'
    matches = re.findall(pattern, line)
    
    if len(matches) >= 6:
        return {
            'ranking': matches[0],
            'institution': matches[1],
            'country_region': matches[2],
            'web_documents': matches[3],
            'cites': matches[4],
            'cites_per_paper': matches[5],
            'top_papers': matches[6] if len(matches) > 6 else '0'
        }
    return None

def import_single_csv(config, csv_file, subject_name):
    """导入单个CSV文件"""
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        print(f"正在处理: {subject_name}")
        
        # 读取文件内容
        with open(csv_file, 'r', encoding='ISO-8859-1') as f:
            lines = f.readlines()
        
        # 找到数据开始的行
        data_lines = []
        for i, line in enumerate(lines):
            if line.strip().startswith('"') and ',' in line:
                # 检查是否是数据行（包含引号和逗号）
                parsed = parse_csv_line(line.strip())
                if parsed and parsed['ranking'].isdigit():
                    data_lines.append(parsed)
        
        print(f"找到 {len(data_lines)} 条有效数据")
        
        if len(data_lines) == 0:
            print(f"警告: {subject_name} 没有找到有效数据")
            return 0
        
        # 插入数据
        insert_sql = """
        INSERT INTO university_rankings 
        (ranking_position, institution_name, country_region, subject_field, 
         web_of_science_documents, cites, cites_per_paper, top_papers)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        records_inserted = 0
        for data in data_lines:
            try:
                # 清理数据
                ranking = int(data['ranking']) if data['ranking'].isdigit() else None
                institution = data['institution']
                country_region = data['country_region']
                web_documents = int(data['web_documents'].replace(',', '')) if data['web_documents'].replace(',', '').isdigit() else None
                cites = int(data['cites'].replace(',', '')) if data['cites'].replace(',', '').isdigit() else None
                cites_per_paper = float(data['cites_per_paper']) if data['cites_per_paper'].replace('.', '').isdigit() else None
                top_papers = int(data['top_papers']) if data['top_papers'].isdigit() else None
                
                cursor.execute(insert_sql, (
                    ranking,
                    institution,
                    country_region,
                    subject_name,
                    web_documents,
                    cites,
                    cites_per_paper,
                    top_papers
                ))
                records_inserted += 1
                
            except Exception as e:
                print(f"插入记录时出错: {e}")
                print(f"问题数据: {data}")
                continue
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"✓ {subject_name}: 成功导入 {records_inserted} 条记录")
        return records_inserted
        
    except Exception as e:
        print(f"✗ 处理 {subject_name} 时出错: {e}")
        return 0

def import_all_data(config):
    """导入所有CSV数据"""
    csv_files = []
    download_dir = "download"
    
    # 获取所有CSV文件
    if os.path.exists(download_dir):
        for file in os.listdir(download_dir):
            if file.endswith('.csv'):
                csv_files.append((os.path.join(download_dir, file), file.replace('.csv', '')))
    
    print(f"找到 {len(csv_files)} 个CSV文件")
    
    total_records = 0
    successful_files = 0
    
    for csv_file, subject_name in csv_files:
        records = import_single_csv(config, csv_file, subject_name)
        if records > 0:
            successful_files += 1
            total_records += records
    
    print(f"\n总计：")
    print(f"  成功处理的文件: {successful_files}/{len(csv_files)}")
    print(f"  总共导入记录: {total_records}")
    
    return total_records

def verify_import(config):
    """验证导入结果"""
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # 检查总记录数
        cursor.execute("SELECT COUNT(*) FROM university_rankings")
        total_count = cursor.fetchone()[0]
        print(f"数据库中总记录数: {total_count}")
        
        # 检查学科数量
        cursor.execute("SELECT COUNT(DISTINCT subject_field) FROM university_rankings")
        subject_count = cursor.fetchone()[0]
        print(f"学科数量: {subject_count}")
        
        # 检查各学科的记录数
        cursor.execute("""
            SELECT subject_field, COUNT(*) as count 
            FROM university_rankings 
            GROUP BY subject_field 
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print("\n各学科记录数 (前10个):")
        for subject, count in cursor.fetchall():
            print(f"  {subject}: {count} 条记录")
        
        # 显示一些示例记录
        cursor.execute("""
            SELECT ranking_position, institution_name, country_region, subject_field 
            FROM university_rankings 
            WHERE country_region LIKE '%CHINA%'
            ORDER BY ranking_position 
            LIMIT 10
        """)
        
        print("\n中国机构前10条记录:")
        for row in cursor.fetchall():
            print(f"  排名: {row[0]}, 机构: {row[1]}, 国家/地区: {row[2]}, 学科: {row[3]}")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"验证数据时出错: {e}")

def main():
    """主函数"""
    print("大学排名数据导入脚本")
    print("=" * 50)
    
    # 获取数据库配置
    config = get_db_config()
    
    print("\n1. 创建数据库和表...")
    if not create_database_and_table(config):
        return
    
    print("\n2. 导入所有CSV数据...")
    total_records = import_all_data(config)
    
    if total_records > 0:
        print("\n3. 验证导入结果...")
        verify_import(config)
        
        print("\n" + "=" * 50)
        print("✓ 数据导入完成！")
        print(f"总共导入了 {total_records} 条记录")
    else:
        print("\n✗ 没有成功导入任何数据")

if __name__ == "__main__":
    main()