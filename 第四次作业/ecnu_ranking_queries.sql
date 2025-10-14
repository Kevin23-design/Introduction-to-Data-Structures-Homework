-- 华东师范大学学科排名查询SQL语句集合
-- 实验要求3：通过SQL语句获取华东师范大学在各个学科中的排名

-- 1. 基础查询：华东师范大学在各学科的排名（使用原始表）
SELECT 
    subject_field AS '学科领域',
    ranking_position AS '排名',
FROM university_rankings 
WHERE institution_name LIKE '%EAST CHINA NORMAL%' 
ORDER BY ranking_position ASC;

-- 2. 优化查询：使用规范化Schema查询华东师范大学排名
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
ORDER BY r.ranking_position ASC;

-- 3. 统计分析：按学科类别统计华东师范大学表现
SELECT 
    s.subject_category AS '学科类别',
    COUNT(*) AS '学科数量',
    AVG(r.ranking_position) AS '平均排名',
    MIN(r.ranking_position) AS '最好排名',
    MAX(r.ranking_position) AS '最差排名',
    SUM(r.total_cites) AS '总引用数',
    AVG(r.cites_per_paper) AS '平均每篇引用'
FROM rankings r
JOIN institutions i ON r.institution_id = i.id
JOIN subjects s ON r.subject_id = s.id
WHERE i.institution_name LIKE '%EAST CHINA NORMAL%'
GROUP BY s.subject_category
ORDER BY AVG(r.ranking_position) ASC;

-- 4. 高级分析：华东师范大学在各学科的全球排名百分位
SELECT 
    s.subject_name AS '学科领域',
    ecnu.ranking_position AS '华师大排名',
    stats.total_institutions AS '全球参与机构数',
    ROUND((ecnu.ranking_position / stats.total_institutions * 100), 2) AS '排名百分位(%)',
    CASE 
        WHEN ecnu.ranking_position <= stats.total_institutions * 0.1 THEN 'TOP 10%'
        WHEN ecnu.ranking_position <= stats.total_institutions * 0.2 THEN 'TOP 20%'
        WHEN ecnu.ranking_position <= stats.total_institutions * 0.3 THEN 'TOP 30%'
        WHEN ecnu.ranking_position <= stats.total_institutions * 0.5 THEN 'TOP 50%'
        ELSE 'OTHER'
    END AS '排名级别'
FROM (
    SELECT r.subject_id, r.ranking_position
    FROM rankings r
    JOIN institutions i ON r.institution_id = i.id
    WHERE i.institution_name LIKE '%EAST CHINA NORMAL%'
) ecnu
JOIN subjects s ON ecnu.subject_id = s.id
JOIN (
    SELECT subject_id, COUNT(*) as total_institutions
    FROM rankings
    WHERE ranking_position IS NOT NULL
    GROUP BY subject_id
) stats ON ecnu.subject_id = stats.subject_id
ORDER BY ecnu.ranking_position ASC;

-- 5. 排名趋势：华东师范大学最强学科TOP5
SELECT 
    s.subject_name AS '学科领域',
    r.ranking_position AS '排名',
    r.total_cites AS '总引用数',
    r.cites_per_paper AS '每篇论文引用数'
FROM rankings r
JOIN institutions i ON r.institution_id = i.id
JOIN subjects s ON r.subject_id = s.id
WHERE i.institution_name LIKE '%EAST CHINA NORMAL%'
ORDER BY r.ranking_position ASC
LIMIT 5;

-- 6. 比较分析：华东师范大学vs同类师范大学
SELECT 
    i.institution_name AS '机构名称',
    COUNT(*) AS '参与学科数',
    AVG(r.ranking_position) AS '平均排名',
    SUM(r.total_cites) AS '总引用数'
FROM rankings r
JOIN institutions i ON r.institution_id = i.id
JOIN countries c ON i.country_id = c.id
WHERE (i.institution_name LIKE '%NORMAL%' OR i.institution_name LIKE '%师范%')
    AND c.country_name = 'CHINA MAINLAND'
GROUP BY i.institution_name
HAVING COUNT(*) >= 5
ORDER BY AVG(r.ranking_position) ASC;

-- 7. 详细分析：华东师范大学在特定学科领域的表现
SELECT 
    s.subject_name AS '学科领域',
    r.ranking_position AS '排名',
    r.total_cites AS '总引用数',
    r.web_of_science_documents AS 'WoS文档数',
    ROUND(r.total_cites / r.web_of_science_documents, 2) AS '每文档引用数'
FROM rankings r
JOIN institutions i ON r.institution_id = i.id
JOIN subjects s ON r.subject_id = s.id
WHERE i.institution_name LIKE '%EAST CHINA NORMAL%'
    AND s.subject_category IN ('SCIENCE', 'ENGINEERING')
ORDER BY r.ranking_position ASC;
