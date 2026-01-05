"""
NLP模型对比结果可视化程序
展示模型性能指标、平台差异、混淆矩阵等
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

# 设置绘图风格
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'


class NLPModelVisualizer:
    """NLP模型对比可视化器"""
    
    def __init__(self, json_file):
        """加载JSON数据"""
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.overall_results = self.data['overall_results']
        self.platform_results = self.data['platform_results']
        
        # 模型名称映射（简化显示）
        self.model_names = {
            'snownlp': 'SnowNLP',
            'rule_based': 'RuleBased',
            'hybrid_6_4': 'Hybrid 6:4',
            'hybrid_7_3': 'Hybrid 7:3',
            'hybrid_5_5': 'Hybrid 5:5',
            'simple_threshold': 'SimpleThreshold'
        }
        
        # 平台名称映射
        self.platform_names = {
            'zhihu': 'Zhihu',
            'xhs': 'XHS',
            'tieba': 'Tieba'
        }
    
    def plot_overall_metrics_comparison(self):
        """绘制全平台模型性能对比"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Overall Model Performance Comparison', fontsize=16, fontweight='bold', y=0.995)
        
        models = list(self.model_names.keys())
        metrics = ['accuracy', 'precision', 'recall', 'f1_score']
        metric_names = ['Accuracy', 'Precision', 'Recall', 'F1 Score']
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
        
        for idx, (metric, metric_name, color) in enumerate(zip(metrics, metric_names, colors)):
            ax = axes[idx // 2, idx % 2]
            
            values = [self.overall_results[model][metric] for model in models]
            model_labels = [self.model_names[model] for model in models]
            
            bars = ax.bar(range(len(models)), values, color=color, alpha=0.7, edgecolor='black')
            
            # 添加数值标签
            for i, (bar, val) in enumerate(zip(bars, values)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{val:.4f}', ha='center', va='bottom', fontsize=9)
            
            ax.set_xlabel('Model', fontsize=11)
            ax.set_ylabel(metric_name, fontsize=11)
            ax.set_title(f'{metric_name} Comparison', fontsize=12, fontweight='bold')
            ax.set_xticks(range(len(models)))
            ax.set_xticklabels(model_labels, rotation=30, ha='right', fontsize=9)
            ax.set_ylim(0, 1.0)
            ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_f1_ranking(self):
        """绘制F1分数排行榜"""
        fig, ax = plt.subplots(figsize=(12, 7))
        
        models = list(self.model_names.keys())
        f1_scores = [self.overall_results[model]['f1_score'] for model in models]
        model_labels = [self.model_names[model] for model in models]
        
        # 排序
        sorted_indices = np.argsort(f1_scores)[::-1]
        sorted_models = [model_labels[i] for i in sorted_indices]
        sorted_f1 = [f1_scores[i] for i in sorted_indices]
        
        # 颜色渐变
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(models)))
        
        bars = ax.barh(range(len(models)), sorted_f1, color=colors, edgecolor='black', linewidth=1.5)
        
        # 添加数值标签
        for i, (bar, val) in enumerate(zip(bars, sorted_f1)):
            ax.text(val + 0.01, bar.get_y() + bar.get_height()/2,
                   f'{val:.4f}', va='center', fontsize=11, fontweight='bold')
        
        # 添加排名标签
        for i in range(len(models)):
            ax.text(-0.02, i, f'#{i+1}', va='center', ha='right', 
                   fontsize=12, fontweight='bold', color='#2c3e50')
        
        ax.set_yticks(range(len(models)))
        ax.set_yticklabels(sorted_models, fontsize=11)
        ax.set_xlabel('F1 Score', fontsize=12, fontweight='bold')
        ax.set_title('Model F1 Score Ranking (All Platforms)', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlim(0, 1.0)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        ax.invert_yaxis()
        
        plt.tight_layout()
        return fig
    
    def plot_platform_comparison(self):
        """绘制各平台模型性能对比"""
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        fig.suptitle('Model Performance Comparison by Platform (F1 Score)', fontsize=16, fontweight='bold')
        
        models = list(self.model_names.keys())
        platforms = ['zhihu', 'xhs', 'tieba']
        
        for idx, platform in enumerate(platforms):
            ax = axes[idx]
            
            f1_scores = [self.platform_results[platform][model]['f1_score'] 
                        for model in models]
            model_labels = [self.model_names[model] for model in models]
            
            colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(models)))
            bars = ax.bar(range(len(models)), f1_scores, color=colors, 
                         alpha=0.8, edgecolor='black')
            
            # 添加数值标签
            for bar, val in zip(bars, f1_scores):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{val:.3f}', ha='center', va='bottom', fontsize=9)
            
            ax.set_xlabel('Model', fontsize=11)
            ax.set_ylabel('F1 Score', fontsize=11)
            ax.set_title(f'{self.platform_names[platform]}', fontsize=13, fontweight='bold')
            ax.set_xticks(range(len(models)))
            ax.set_xticklabels(model_labels, rotation=30, ha='right', fontsize=9)
            ax.set_ylim(0, 1.0)
            ax.grid(axis='y', alpha=0.3)
            
            # 标记最佳模型
            best_idx = np.argmax(f1_scores)
            ax.patches[best_idx].set_facecolor('#e74c3c')
            ax.patches[best_idx].set_alpha(0.9)
        
        plt.tight_layout()
        return fig
    
    def plot_heatmap(self):
        """绘制模型-平台性能热力图"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        models = list(self.model_names.keys())
        platforms = ['zhihu', 'xhs', 'tieba']
        
        # 构建数据矩阵
        data_matrix = np.zeros((len(models), len(platforms)))
        for i, model in enumerate(models):
            for j, platform in enumerate(platforms):
                data_matrix[i, j] = self.platform_results[platform][model]['f1_score']
        
        # 绘制热力图
        sns.heatmap(data_matrix, annot=True, fmt='.4f', cmap='YlGnBu',
                   xticklabels=[self.platform_names[p] for p in platforms],
                   yticklabels=[self.model_names[m] for m in models],
                   cbar_kws={'label': 'F1 Score'},
                   linewidths=2, linecolor='white',
                   ax=ax, vmin=0, vmax=1.0)
        
        ax.set_title('F1 Score Heatmap by Model and Platform', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Platform', fontsize=12, fontweight='bold')
        ax.set_ylabel('Model', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def plot_confusion_matrix(self, model='hybrid_7_3'):
        """绘制混淆矩阵"""
        fig, ax = plt.subplots(figsize=(8, 7))
        
        cm = np.array(self.overall_results[model]['confusion_matrix'])
        labels = ['Positive', 'Neutral', 'Negative']
        
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=labels, yticklabels=labels,
                   cbar_kws={'label': 'Count'},
                   linewidths=2, linecolor='white',
                   ax=ax)
        
        ax.set_title(f'{self.model_names[model]} - Confusion Matrix\n(All Platforms)', 
                    fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
        ax.set_ylabel('True Label', fontsize=12, fontweight='bold')
        
        # 计算准确率并添加到每个格子
        row_sums = cm.sum(axis=1, keepdims=True)
        percentages = (cm / row_sums * 100).astype(int)
        
        for i in range(len(labels)):
            for j in range(len(labels)):
                text = ax.text(j + 0.5, i + 0.7,
                             f'({percentages[i, j]}%)',
                             ha='center', va='center',
                             color='gray', fontsize=9)
        
        plt.tight_layout()
        return fig
    
    def plot_metrics_radar(self):
        """绘制雷达图对比前4个模型"""
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # 选择前4个模型
        top_models = ['hybrid_7_3', 'hybrid_6_4', 'snownlp', 'hybrid_5_5']
        metrics = ['accuracy', 'precision', 'recall', 'f1_score']
        metric_labels = ['Accuracy', 'Precision', 'Recall', 'F1 Score']
        
        # 设置角度
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # 闭合
        
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
        
        for model, color in zip(top_models, colors):
            values = [self.overall_results[model][m] for m in metrics]
            values += values[:1]  # 闭合
            
            ax.plot(angles, values, 'o-', linewidth=2, label=self.model_names[model],
                   color=color, markersize=8)
            ax.fill(angles, values, alpha=0.15, color=color)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metric_labels, fontsize=12)
        ax.set_ylim(0, 1.0)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=10)
        ax.set_title('Top 4 Models Performance Radar Chart', fontsize=14, fontweight='bold', pad=30)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        return fig
    
    def plot_all(self, save_dir=None):
        """生成所有图表"""
        print("=" * 80)
        print("Generating visualizations...")
        print("=" * 80)
        
        figures = []
        
        print("\n📊 1. Generating overall metrics comparison...")
        fig1 = self.plot_overall_metrics_comparison()
        figures.append(('overall_metrics', fig1))
        
        print("📊 2. Generating F1 score ranking...")
        fig2 = self.plot_f1_ranking()
        figures.append(('f1_ranking', fig2))
        
        print("📊 3. Generating platform comparison...")
        fig3 = self.plot_platform_comparison()
        figures.append(('platform_comparison', fig3))
        
        print("📊 4. Generating heatmap...")
        fig4 = self.plot_heatmap()
        figures.append(('heatmap', fig4))
        
        print("📊 5. Generating confusion matrix...")
        fig5 = self.plot_confusion_matrix()
        figures.append(('confusion_matrix', fig5))
        
        print("📊 6. Generating radar chart...")
        fig6 = self.plot_metrics_radar()
        figures.append(('radar', fig6))
        
        # 保存图表
        if save_dir:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            
            print(f"\n💾 Saving charts to: {save_path}")
            for name, fig in figures:
                filename = save_path / f'nlp_{name}.png'
                fig.savefig(filename, dpi=300, bbox_inches='tight')
                print(f"  ✓ {filename}")
        
        print("\n" + "=" * 80)
        print("✅ All charts generated successfully!")
        print("=" * 80)
        
        plt.show()


def main():
    """主函数"""
    # 查找最新的JSON文件
    nlp_dir = Path(r'f:\code\Introduction-to-Data-Science\big_work\MediaCrawler\MediaCrawler\nlp')
    json_files = list(nlp_dir.glob('nlp_model_comparison_*.json'))
    
    if not json_files:
        print("❌ JSON file not found!")
        return
    
    # 使用最新的文件
    latest_json = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"📁 Loading data file: {latest_json.name}\n")
    
    # 创建可视化器
    visualizer = NLPModelVisualizer(latest_json)
    
    # 生成所有图表
    save_dir = nlp_dir / 'visualizations'
    visualizer.plot_all(save_dir=save_dir)


if __name__ == '__main__':
    main()