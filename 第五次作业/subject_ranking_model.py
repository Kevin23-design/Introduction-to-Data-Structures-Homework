"""
实验要求3：利用数据建模的方式，对各学科做一个排名模型，能较好预测排名位置
"""

import os
import math
import mysql.connector
from mysql.connector import Error
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


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
        "FROM university_rankings WHERE ranking_position IS NOT NULL"
    )
    df = pd.read_sql(sql, connection)
    for c in ["institution_name", "country_region", "subject_field"]:
        df[c] = df[c].astype(str).str.strip()
    return df


def split_by_rank(df_subj: pd.DataFrame):
    """学科内按排名升序排序后切分 60/20/20。"""
    df_subj = df_subj.sort_values('ranking_position', ascending=True).reset_index(drop=True)
    n = len(df_subj)
    if n < 10:
        return None  # 数据太少，跳过
    n_train = int(n * 0.6)
    n_val = int(n * 0.2)
    train = df_subj.iloc[:n_train]
    val = df_subj.iloc[n_train:n_train + n_val]
    test = df_subj.iloc[n_train + n_val:]
    return train, val, test


def build_pipelines():
    features = [
        'web_of_science_documents', 'cites', 'cites_per_paper', 'top_papers'
    ]
    ridge = Pipeline([
        ('impute', SimpleImputer(strategy='median')),
        ('scale', StandardScaler()),
        ('model', Ridge(alpha=1.0))
    ])
    rf = Pipeline([
        ('impute', SimpleImputer(strategy='median')),
        ('model', RandomForestRegressor(
            n_estimators=300, max_depth=None, min_samples_leaf=2,
            random_state=42, n_jobs=-1
        ))
    ])
    return features, ridge, rf


def evaluate(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    try:
        rho, _ = spearmanr(y_true, y_pred)
    except Exception:
        rho = np.nan
    return mae, rmse, rho


def main():
    os.makedirs('results/models', exist_ok=True)
    conn = connect_to_database()
    if not conn:
        return
    df = load_all(conn)
    conn.close()

    features, ridge, rf = build_pipelines()
    metrics_rows = []
    samples_out = []

    for subj, g in df.groupby('subject_field'):
        split = split_by_rank(g[['ranking_position'] + features + ['institution_name']].copy())
        if split is None:
            continue
        train, val, test = split

        X_tr, y_tr = train[features].values, train['ranking_position'].values
        X_va, y_va = val[features].values, val['ranking_position'].values
        X_te, y_te = test[features].values, test['ranking_position'].values

        # 训练两种模型
        ridge.fit(X_tr, y_tr)
        rf.fit(X_tr, y_tr)

        # 在验证集上择优
        pred_va_ridge = ridge.predict(X_va)
        pred_va_rf = rf.predict(X_va)
        mae_ridge, rmse_ridge, rho_ridge = evaluate(y_va, pred_va_ridge)
        mae_rf, rmse_rf, rho_rf = evaluate(y_va, pred_va_rf)

        best = ('ridge', ridge, mae_ridge, rmse_ridge, rho_ridge) if mae_ridge <= mae_rf else ('rf', rf, mae_rf, rmse_rf, rho_rf)
        best_name, best_model, _, _, _ = best

        # 测试集评估
        pred_te = best_model.predict(X_te)
        mae, rmse, rho = evaluate(y_te, pred_te)

        metrics_rows.append({
            'subject_field': subj,
            'best_model': best_name,
            'n_train': len(train), 'n_val': len(val), 'n_test': len(test),
            'MAE': round(mae, 2), 'RMSE': round(rmse, 2), 'Spearman': round(float(rho) if not np.isnan(rho) else np.nan, 3)
        })

        # 保存部分预测样例（测试集前20）
        k = min(20, len(test))
        sample_df = test.head(k)[['institution_name', 'ranking_position']].copy()
        sample_df['pred_rank'] = pred_te[:k]
        sample_df.insert(0, 'subject_field', subj)
        samples_out.append(sample_df)

    # 汇总与导出
    metrics_df = pd.DataFrame(metrics_rows).sort_values('MAE')
    metrics_df.to_csv('results/models/subject_model_metrics.csv', index=False, encoding='utf-8-sig')
    if samples_out:
        pd.concat(samples_out, ignore_index=True).to_csv('results/models/subject_sample_predictions.csv', index=False, encoding='utf-8-sig')

    print('\n✓ 建模完成：')
    print('  - results/models/subject_model_metrics.csv')
    print('  - results/models/subject_sample_predictions.csv')
    # 不再生成 summary.md


if __name__ == '__main__':
    main()
