-- 全球不同区域学科表现分析SQL查询
-- 实验要求5：通过SQL语句分析全球不同区域在各个学科中的表现

-- 1. 全球各区域基本统计

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
        

-- 2. 主要区域在各学科的TOP10%表现对比

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
        

-- 3. 各区域学科优势分析（TOP10%占比）

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
        

-- 4. 全球区域竞争力综合排名

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
        

-- 5. 各学科领域的区域分布分析

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
        

