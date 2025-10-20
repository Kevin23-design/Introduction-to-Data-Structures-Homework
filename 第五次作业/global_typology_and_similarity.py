"""
实验要求1：结合学科排名数据，给出全球高校的类型划分，并找出与华东师范大学相似的高校
"""

import os
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def connect_to_database():
    """连接到数据库"""
    config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', 'zzy419220'),
        'database': os.getenv('MYSQL_DB', 'university_ranking')
    }
    try:
        connection = mysql.connector.connect(**config)
        return connection
    except Error as e:
        print(f"数据库连接失败: {e}")
        return None


def load_data(connection) -> pd.DataFrame:
    sql = (
        "SELECT ranking_position, institution_name, country_region, subject_field, "
        "web_of_science_documents, cites, cites_per_paper, top_papers "
        "FROM university_rankings"
    )
    # pandas 对 mysql-connector 的 read_sql 有告警，但可用
    df = pd.read_sql(sql, connection)
    df["institution_name"] = df["institution_name"].str.strip()
    df["country_region"] = df["country_region"].str.strip()
    df["subject_field"] = df["subject_field"].str.strip()
    return df


def compute_subject_scores(df: pd.DataFrame) -> pd.DataFrame:
    """按学科归一化指标并综合为 subject_score"""
    df = df.copy()
    stats = df.groupby('subject_field').agg(
        max_rank=('ranking_position', 'max'),
        min_cpp=('cites_per_paper', 'min'),
        max_cpp=('cites_per_paper', 'max'),
        min_top=('top_papers', 'min'),
        max_top=('top_papers', 'max'),
    )
    df = df.merge(stats, left_on='subject_field', right_index=True, how='left')

    def rank_score(r, max_r):
        if pd.isna(r) or pd.isna(max_r) or max_r in (0, 1):
            return 0.0
        return 1.0 - (float(r) - 1.0) / (float(max_r) - 1.0)

    def minmax(v, vmin, vmax):
        if pd.isna(v) or pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
            return 0.0
        return (float(v) - float(vmin)) / (float(vmax) - float(vmin))

    df['rank_score'] = [rank_score(r, m) for r, m in zip(df['ranking_position'], df['max_rank'])]
    df['cpp_norm'] = [minmax(v, a, b) for v, a, b in zip(df['cites_per_paper'], df['min_cpp'], df['max_cpp'])]
    df['top_norm'] = [minmax(v, a, b) for v, a, b in zip(df['top_papers'], df['min_top'], df['max_top'])]
    df['subject_score'] = 0.7 * df['rank_score'] + 0.2 * df['cpp_norm'] + 0.1 * df['top_norm']
    return df[['institution_name', 'country_region', 'subject_field', 'subject_score']]


def build_feature_matrix(subj_scores: pd.DataFrame):
    pivot = subj_scores.pivot_table(index='institution_name', columns='subject_field', values='subject_score', aggfunc='mean', fill_value=0.0)
    institutions = pivot.index.to_list()
    subjects = pivot.columns.to_list()
    X = pivot.values.astype(float)
    coverage = (pivot.values > 0).sum(axis=1)
    mean_strength = np.where(coverage > 0, pivot.values.sum(axis=1) / np.maximum(coverage, 1), 0.0)
    return X, institutions, subjects, coverage, mean_strength


def auto_k(X, k_min=3, k_max=8):
    best_k, best_s = None, -1
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=20, random_state=42)
        labels = km.fit_predict(X)
        if len(set(labels)) < 2:
            continue
        s = silhouette_score(X, labels, metric='cosine')
        if s > best_s:
            best_k, best_s = k, s
    return best_k or 4


def cosine_sim(X: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(X, axis=1, keepdims=True)
    n[n == 0] = 1.0
    Xn = X / n
    return Xn @ Xn.T


def find_ecnu_name(names: list[str]) -> str | None:
    pats = [
        'EAST CHINA NORMAL UNIVERSITY',
        'EAST CHINA NORMAL UNIV',
        'ECNU',
        '华东师范'
    ]
    upper = {t.upper(): t for t in names}
    for p in pats:
        u = p.upper()
        for name_u, orig in upper.items():
            if u in name_u:
                return orig
    return None


def step1_typology(df: pd.DataFrame):
    print("1. 全球高校类型划分（聚类分析）")
    print("-" * 60)
    subj_scores = compute_subject_scores(df)
    X, institutions, subjects, coverage, mean_strength = build_feature_matrix(subj_scores)
    if X.shape[0] < 5:
        print("样本过少，无法聚类。")
        return None
    k = auto_k(X)
    km = KMeans(n_clusters=k, n_init=20, random_state=42)
    labels = km.fit_predict(X)

    cov_q = np.quantile(coverage, [0.33, 0.66])
    str_q = np.quantile(mean_strength, [0.33, 0.66])

    def label_name(cov, strength, top_subjects):
        cov_level = 0 if cov <= cov_q[0] else (2 if cov >= cov_q[1] else 1)
        str_level = 0 if strength <= str_q[0] else (2 if strength >= str_q[1] else 1)
        if cov_level == 2 and str_level == 2:
            base = '全球综合型强校'
        elif cov_level == 2 and str_level == 1:
            base = '综合均衡型院校'
        elif cov_level == 1 and str_level == 2:
            base = '优势明显的研究型'
        elif cov_level == 0 and str_level == 2:
            base = '尖子单科/特色强校'
        else:
            base = '发展中/教学研究型'
        tops = ", ".join([s for s, _ in top_subjects[:3]]) or '无明显强项'
        return f"{base}（强项：{tops}）"

    # 输出每个簇的概览
    for c in range(k):
        idx = np.where(labels == c)[0]
        Xc = X[idx]
        if Xc.size == 0:
            continue
        mean_vec = Xc.mean(axis=0)
        top_idx = np.argsort(-mean_vec)[:5]
        top_subjects = [(subjects[i], float(mean_vec[i])) for i in top_idx if mean_vec[i] > 0]
        cov_mean = coverage[idx].mean()
        str_mean = mean_strength[idx].mean()
        cname = label_name(cov_mean, str_mean, top_subjects)
        print(f"- 类别 C{c}: {cname} | 规模: {len(idx)} | 平均覆盖学科: {cov_mean:.1f}")

    return {
        'X': X,
        'institutions': institutions,
        'labels': labels,
        'subjects': subjects,
    }


def step2_similar_ecnu(ctx, df: pd.DataFrame, topn=20):
    print("\n2. 与华东师范大学相似高校（余弦相似度）")
    print("-" * 60)
    X = ctx['X']
    institutions = ctx['institutions']
    names = institutions
    target = find_ecnu_name(names)
    if not target:
        print("未识别到华东师范大学（ECNU），可手动指定名称或检查数据写法。")
        return
    sim = cosine_sim(X)
    idx_map = {n: i for i, n in enumerate(institutions)}
    i = idx_map[target]
    order = np.argsort(-sim[i])
    count = 0
    for j in order:
        if j == i:
            continue
        print(f"- {institutions[j]}（相似度 {sim[i, j]:.3f}）")
        count += 1
        if count >= topn:
            break


def main():
    print("实验要求1：全球高校类型划分与ECNU相似高校分析")
    print("=" * 100)

    conn = connect_to_database()
    if not conn:
        return
    df = load_data(conn)
    conn.close()

    ctx = step1_typology(df)
    if ctx:
        step2_similar_ecnu(ctx, df)


    print("\n" + "=" * 100)
    print("✓ 实验要求1完成：全球高校类型与相似高校分析！")


if __name__ == '__main__':
    main()
