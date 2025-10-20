"""
实验要求2：通过探索性分析，对华东师范大学（ECNU）做一个学科画像，尽可能多角度。
"""

import os
import math
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')  # 后端设为非交互，便于无界面保存图
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体支持
rcParams['font.sans-serif'] = ['SimHei']  # 黑体
rcParams['axes.unicode_minus'] = False    # 正常显示负号

def connect_to_database():
    cfg = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', 'zzy419220'),
        'database': os.getenv('MYSQL_DB', 'university_ranking')
    }
    try:
        return mysql.connector.connect(**cfg)
    except Error as e:
        print(f"数据库连接失败: {e}")
        return None


def load_all(connection) -> pd.DataFrame:
    sql = (
        "SELECT ranking_position, institution_name, country_region, subject_field, "
        "web_of_science_documents, cites, cites_per_paper, top_papers "
        "FROM university_rankings"
    )
    df = pd.read_sql(sql, connection)
    for c in ["institution_name", "country_region", "subject_field"]:
        df[c] = df[c].astype(str).str.strip()
    return df


def find_ecnu_name(cands: list[str]) -> str | None:
    pats = [
        'EAST CHINA NORMAL UNIVERSITY', 'EAST CHINA NORMAL UNIV', 'ECNU', '华东师范'
    ]
    up = {s.upper(): s for s in cands}
    for p in pats:
        pu = p.upper()
        for name_u, orig in up.items():
            if pu in name_u:
                return orig
    return None


def compute_subject_scores(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby('subject_field').agg(
        max_rank=('ranking_position', 'max'),
        min_cpp=('cites_per_paper', 'min'), max_cpp=('cites_per_paper', 'max'),
        min_top=('top_papers', 'min'), max_top=('top_papers', 'max'),
    )
    df = df.merge(stats, left_on='subject_field', right_index=True, how='left')

    def rscore(r, mr):
        if pd.isna(r) or pd.isna(mr) or mr in (0, 1):
            return 0.0
        return 1.0 - (float(r) - 1.0) / (float(mr) - 1.0)

    def minmax(v, a, b):
        if pd.isna(v) or pd.isna(a) or pd.isna(b) or a == b:
            return 0.0
        return (float(v) - float(a)) / (float(b) - float(a))

    df['rank_score'] = [rscore(r, m) for r, m in zip(df['ranking_position'], df['max_rank'])]
    df['cpp_norm'] = [minmax(v, a, b) for v, a, b in zip(df['cites_per_paper'], df['min_cpp'], df['max_cpp'])]
    df['top_norm'] = [minmax(v, a, b) for v, a, b in zip(df['top_papers'], df['min_top'], df['max_top'])]
    df['subject_score'] = 0.7*df['rank_score'] + 0.2*df['cpp_norm'] + 0.1*df['top_norm']
    return df


def percentiles_by_subject(df: pd.DataFrame, inst_name: str) -> pd.DataFrame:
    """计算目标高校在各学科上的指标百分位（基于全体院校的分布）。"""
    rows = []
    for subj, g in df.groupby('subject_field'):
        # 分布
        cpp = g['cites_per_paper'].dropna().values
        top = g['top_papers'].dropna().values
        rk = g['ranking_position'].dropna().values

        # 该校记录
        gi = g[g['institution_name'] == inst_name]
        if gi.empty:
            continue
        # 可能同一学科多条，取最优排名对应的一条
        gi = gi.sort_values('ranking_position', ascending=True).iloc[0]

        def pct(value, arr, higher_is_better=True):
            if arr.size == 0 or pd.isna(value):
                return np.nan
            if higher_is_better:
                return float((arr <= value).sum()/arr.size*100.0) if value in arr else float(np.searchsorted(np.sort(arr), value, side='right')/arr.size*100.0)
            else:
                # 排名越小越好，用反向百分位（小越好 → 高百分位）
                return float((arr >= value).sum()/arr.size*100.0) if value in arr else float((arr.size - np.searchsorted(np.sort(arr), value, side='left'))/arr.size*100.0)

        cpp_pct = pct(gi['cites_per_paper'], cpp, higher_is_better=True)
        top_pct = pct(gi['top_papers'], top, higher_is_better=True)
        rank_pct = pct(gi['ranking_position'], rk, higher_is_better=False)

        rows.append({
            'subject_field': subj,
            'ecnu_rank': int(gi['ranking_position']) if not pd.isna(gi['ranking_position']) else None,
            'rank_percentile(%)': round(rank_pct, 2) if not pd.isna(rank_pct) else None,
            'cites_per_paper': float(gi['cites_per_paper']) if not pd.isna(gi['cites_per_paper']) else None,
            'cites_per_paper_percentile(%)': round(cpp_pct, 2) if not pd.isna(cpp_pct) else None,
            'top_papers': int(gi['top_papers']) if not pd.isna(gi['top_papers']) else None,
            'top_papers_percentile(%)': round(top_pct, 2) if not pd.isna(top_pct) else None,
        })

    return pd.DataFrame(rows).sort_values('rank_percentile(%)', ascending=False)


def ensure_dirs():
    os.makedirs('results/plots', exist_ok=True)


def save_plots(scores_pivot: pd.DataFrame, percentiles: pd.DataFrame, inst_name: str):
    # 雷达图：选前8个强项学科
    top_subjects = scores_pivot.sort_values(ascending=False).head(8)
    labels = top_subjects.index.tolist()
    values = top_subjects.values.tolist()
    if len(labels) >= 3:
        angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]
        fig = plt.figure(figsize=(6,6))
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles, values, 'o-', linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_thetagrids(np.array(angles[:-1]) * 180/np.pi, labels)
        ax.set_title(f'{inst_name} 学科强项雷达图')
        ax.grid(True)
        plt.tight_layout()
        fig.savefig('results/plots/ecnu_radar.png', dpi=150)
        plt.close(fig)

    # 柱状图：百分位 Top15 学科（以排名百分位排序）
    if not percentiles.empty:
        p = percentiles.dropna(subset=['rank_percentile(%)']).head(15)
        fig, ax = plt.subplots(figsize=(9,5))
        ax.barh(p['subject_field'][::-1], p['rank_percentile(%)'][::-1], color='#5B8FF9')
        ax.set_xlabel('排名百分位（越高越好）')
        ax.set_title(f'{inst_name} 学科排名百分位 Top15')
        plt.tight_layout()
        fig.savefig('results/plots/ecnu_rank_percentile_top15.png', dpi=150)
        plt.close(fig)


def main():
    print('实验要求2：ECNU 学科画像（探索性分析）')
    print('='*100)
    ensure_dirs()

    conn = connect_to_database()
    if not conn:
        return
    df = load_all(conn)
    conn.close()

    insts = sorted(df['institution_name'].dropna().unique().tolist())
    ecnu = find_ecnu_name(insts)
    if not ecnu:
        print('未识别到华东师范大学（ECNU），请检查名称并重试。')
        return

    # 构建综合分
    df_sc = compute_subject_scores(df)
    # ECNU 综合分（学科画像）
    ecnu_scores = (
        df_sc[df_sc['institution_name'] == ecnu]
        .groupby('subject_field')['subject_score']
        .mean()
        .sort_values(ascending=False)
    )

    # 百分位画像
    percent = percentiles_by_subject(df, ecnu)

    # 汇总统计
    coverage = (ecnu_scores > 0).sum()
    strong = ecnu_scores.head(10)
    weak = ecnu_scores[ecnu_scores > 0].tail(10)

    # 保存CSV
    ecnu_scores.to_csv('results/ecnu_subject_scores.csv', header=['subject_score'], encoding='utf-8-sig')
    percent.to_csv('results/ecnu_subject_percentiles.csv', index=False, encoding='utf-8-sig')

    # 画图
    save_plots(ecnu_scores, percent, ecnu)

    print('\n✓ 画像完成：')
    print('  - results/ecnu_subject_scores.csv')
    print('  - results/ecnu_subject_percentiles.csv')
    print('  - results/plots/*.png')


if __name__ == '__main__':
    main()
