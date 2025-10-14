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
