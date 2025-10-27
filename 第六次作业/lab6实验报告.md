# 数据结构导论 - 第五次作业实验

## 实验题目：华东师范大学专业排名分析 pro max

**实验日期：** 2025年10月27日

## 实验目的
通过编程训练，学习深度学习

## 问题重述
1. 在上一节课作业的基础上，请利用深度学习方法，对各学科做一个排名模型，能够较好的预测出排名位置，并且利用MSE，MAPE等指标来进行评价模型的优劣。
2. 对ESI的数据进行聚类，发现与华师大类似的学校有哪些，并分析下原因。

## 深度学习环境配置
## $\text{PyTorch-GPU}$ 实验环境简述

实验环境是基于 $\text{Anaconda}$ 的**独立虚拟环境**，利用 $\text{RTX 4060}$ 笔记本电脑进行深度学习训练而搭建。


| 类别 | 详细配置 |
| :--- | :--- |
| **硬件** | $\text{NVIDIA GeForce RTX 4060 Laptop GPU}$ (算力 $\text{8.9}$) |
| **操作系统** | $\text{Windows 11}$ 或 $\text{10}$ ($\text{PS C:}$ 命令行环境) |
| **$\text{GPU}$ 驱动** | $\text{NVIDIA}$ 驱动 |
| **系统 $\text{CUDA}$** | $\text{CUDA Toolkit 11.8}$ (通过 $\text{nvcc -V}$ 确认) |
| **环境管理** | $\text{Anaconda/Conda}$ (独立环境，`rtx4060_env`) |
| **Python 版本** | $\text{3.11.14}$ |
| **核心框架** | $\text{PyTorch}$ ($\text{GPU}$ 版本，兼容 $\text{cu118}$) |
| **辅助库** | $\text{Torchvision, Torchaudio}$ |



## 问题一
### 1. 方法概述
利用深度学习方法，对各学科做一个排名模型，较好的预测出排名位置，并且利用MSE，MAPE等指标来进行评价模型的优劣。MSE，MAPE的计算公式如下：
$$
\text{MSE} = \frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2
$$
$$
\text{MAPE} = \frac{100\%}{n} \sum_{i=1}^{n} \left| \frac{y_i - \hat{y}_i}{y_i} \right|
$$
### 2. 核心类结构

```
HyperParameters          # 超参数配置管理类
├── 数据库配置
├── 特征与目标变量定义
├── 模型架构参数
├── 训练超参数
└── 设备配置(CPU/GPU)

RankingNet              # 深度神经网络模型
├── 多层感知机(MLP)架构
├── BatchNorm + Dropout + LeakyReLU
└── Kaiming权重初始化

EarlyStopping           # 早停机制
└── 监控验证损失,防止过拟合

MetricsNormalizer       # 指标归一化器
├── 对多学科的评估指标进行归一化
└── 计算综合评分

DeepLearningRankingPredictor  # 主控制器
├── 数据加载与预处理
├── 模型训练
├── 结果评估与保存
└── 训练过程可视化
```

### 3. 详细实现步骤
实现流程图：
```
1. 数据加载
   └─> 从MySQL加载数据
   
2. 全局预处理
   ├─> 类型转换
   ├─> 异常值裁剪
   └─> 样本量筛选

3. 按学科迭代训练
   ├─> 3.1 提取单个学科数据
   ├─> 3.2 缺失值填充
   ├─> 3.3 特征标准化
   ├─> 3.4 数据划分(训练/验证/测试)
   ├─> 3.5 创建DataLoader
   ├─> 3.6 初始化模型、优化器、调度器
   ├─> 3.7 训练循环
   │   ├─> 前向传播
   │   ├─> 计算损失
   │   ├─> 反向传播
   │   ├─> 参数更新
   │   ├─> 验证
   │   ├─> 学习率调整
   │   └─> 早停检查
   └─> 3.8 在测试集上评估

4. 指标归一化
   └─> 对所有学科的指标进行Min-Max归一化

5. 结果保存与报告
   ├─> 保存CSV文件
   ├─> 打印性能报告
   └─> 生成训练过程图
```

#### 3.1 数据加载与预处理

##### 3.1.1 数据库连接与查询
```python
def load_data(self):
    conn = mysql.connector.connect(**HP.DB_CONFIG)
    query = "SELECT * FROM university_rankings WHERE ranking_position IS NOT NULL"
    df = pd.read_sql(query, conn)
    conn.close()
    return df
```

##### 3.1.2 数据预处理流程

**步骤1: 数据类型转换**
```python
for col in HP.FEATURES + [HP.TARGET]:
    df[col] = pd.to_numeric(df[col], errors='coerce')
```
- 将所有特征列和目标列强制转换为数值类型
- 无法转换的值设为`NaN`

**步骤2: 异常值处理**
```python
for col in HP.FEATURES:
    q_low, q_high = df[col].quantile([0.05, 0.95])
    df[col] = np.clip(df[col], q_low, q_high)
```
- 计算每个特征的5%和95%分位数
- 将超出范围的值裁剪到边界值
- **目的**: 降低极端异常值对模型的影响

**步骤3: 样本量筛选**
```python
field_counts = df['subject_field'].value_counts()
valid_fields = field_counts[field_counts >= 15].index
df = df[df['subject_field'].isin(valid_fields)]
```
- 移除样本量少于15条的学科
- **原因**: 深度学习模型需要足够的训练数据

**步骤4: 缺失值处理(在单个学科训练时)**
```python
imputer = SimpleImputer(strategy='median')
X_imputed = imputer.fit_transform(X)
```
- 使用中位数填充缺失值
- **优势**: 中位数对异常值不敏感

**步骤5: 特征标准化**
```python
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)
```
- 将特征缩放到均值为0、标准差为1
- **必要性**: 神经网络对输入数据的尺度敏感

---

#### 3.2 模型架构设计

##### 3.2.1 RankingNet 神经网络

**网络结构**:
```
输入层(4个特征) 
    ↓
全连接层(128) → BatchNorm1d → LeakyReLU → Dropout(0.3)
    ↓
全连接层(64) → BatchNorm1d → LeakyReLU → Dropout(0.3)
    ↓
全连接层(32) → BatchNorm1d → LeakyReLU → Dropout(0.3)
    ↓
输出层(1) → 排名预测值
```

**关键技术**:

1. **BatchNorm1d (批归一化)**
   - **作用**: 加速收敛,提高训练稳定性
   - **原理**: 对每个mini-batch的数据进行标准化
   - **注意**: 需要设置`drop_last=True`避免batch_size=1的情况

2. **LeakyReLU 激活函数**
   ```python
   nn.LeakyReLU(0.1)
   ```
   - **优势**: 解决ReLU的"神经元死亡"问题
   - **原理**: 对负值部分保留小的梯度(0.1)

3. **Dropout 正则化**
   ```python
   nn.Dropout(0.3)
   ```
   - **作用**: 防止过拟合
   - **原理**: 训练时随机丢弃30%的神经元

4. **Kaiming初始化**
   ```python
   nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
   ```
   - **目的**: 为带有ReLU的深度网络提供更好的初始权重
   - **效果**: 缓解梯度消失/爆炸问题

---

#### 3.3 训练策略

##### 3.3.1 数据划分策略

```python
# 第一次划分: 分离测试集(20%)
X_temp, X_test, y_temp, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# 第二次划分: 从剩余80%中分离验证集(25% of 80% = 20%)
val_size_adj = 0.2 / (1 - 0.2)  # = 0.25
X_train, X_val, y_train, y_val = train_test_split(
    X_temp, y_temp, test_size=val_size_adj, random_state=42
)
```

**最终比例**: 训练集64% | 验证集16% | 测试集20%

##### 3.3.2 为每个学科独立训练模型

```python
for field in df['subject_field'].unique():
    df_field = df[df['subject_field'] == field]
    # ... 训练该学科的专属模型
```

**原因**:
- 不同学科的数据分布差异巨大
- 独立模型能更好地捕捉学科特定的模式
- 允许并行训练多个模型

##### 3.3.3 训练配置

**损失函数**: 均方误差(MSE)
```python
criterion = nn.MSELoss()
```
- 适合回归任务
- 对较大误差的惩罚更重

**优化器**: AdamW
```python
optimizer = optim.AdamW(
    model.parameters(), 
    lr=0.001, 
    weight_decay=1e-4
)
```
- **AdamW**: Adam的改进版,解耦了权重衰减
- **学习率**: 0.001(标准起始值)
- **权重衰减**: 1e-4(L2正则化)

**学习率调度器**: ReduceLROnPlateau
```python
scheduler = optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, 'min', 
    factor=0.5,      # 学习率减半
    patience=10      # 10个epoch验证损失不降才触发
)
```
- **自适应调整**: 当验证损失停止下降时自动降低学习率
- **效果**: 帮助模型逃离局部最优,更精细地收敛

#### 3.3.4 早停机制 (Early Stopping)

```python
class EarlyStopping:
    def __init__(self):
        self.patience = 20
        self.min_delta = 0.001
        self.best_loss = None
        self.counter = 0
        
    def __call__(self, val_loss):
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0
```

**工作原理**:
- 监控验证集损失
- 如果连续20个epoch验证损失没有改善(至少0.001),则停止训练
- 自动加载验证性能最佳的模型权重

**优势**:
- 防止过拟合
- 节省训练时间
- 自动选择最优模型

---

#### 3.4 GPU加速与混合精度训练

##### 3.4.1 自动设备检测
```python
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
USE_AMP = torch.cuda.is_available()
```

#### 3.4.2 混合精度训练(AMP)

```python
scaler = torch.cuda.amp.GradScaler(enabled=HP.USE_AMP)

# 训练循环
for batch_X, batch_y in train_loader:
    optimizer.zero_grad()
    with torch.cuda.amp.autocast(enabled=HP.USE_AMP):
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
    
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
```

**混合精度训练优势**:
- **速度提升**: 利用Tensor Cores加速(可提升2-3倍)
- **显存节省**: FP16占用更少显存
- **精度保持**: 通过动态损失缩放维持数值稳定性

##### 3.4.3 DataLoader优化

```python
train_loader = DataLoader(
    train_dataset, 
    batch_size=32, 
    shuffle=True,
    num_workers=0,
    pin_memory=True,      # GPU加速
    drop_last=True        # 解决BatchNorm错误
)
```

**关键参数说明**:
- `pin_memory=True`: 将数据固定在内存中,加快CPU到GPU的传输
- `drop_last=True`: **重要!** 丢弃最后一个不完整的batch,防止`BatchNorm1d`在batch_size=1时报错

---

#### 3.5 模型评估

##### 3.5.1 多维度评估指标

```python
def calculate_metrics(self, y_true, y_pred):
    return {
        'MAE': mean_absolute_error(y_true, y_pred),
        'MSE': mean_squared_error(y_true, y_pred),
        'RMSE': np.sqrt(mean_squared_error(y_true, y_pred)),
        'R2': r2_score(y_true, y_pred),
        'MAPE': np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100,
        'Spearman': spearmanr(rankdata(y_true), rankdata(y_pred))[0]
    }
```

**各指标含义**:

| 指标 | 含义 | 取值范围 | 越小越好/越大越好 |
|------|------|----------|-------------------|
| MAE | 平均绝对误差 | [0, +∞) | 越小越好 |
| MSE | 均方误差 | [0, +∞) | 越小越好 |
| RMSE | 均方根误差 | [0, +∞) | 越小越好 |
| R² | 决定系数 | (-∞, 1] | 越大越好 |
| MAPE | 平均绝对百分比误差 | [0, +∞) | 越小越好 |
| Spearman | 斯皮尔曼等级相关 | [-1, 1] | 越大越好 |

##### 3.5.2 指标归一化与综合评分

**问题**: 不同学科的排名范围差异大(有的1-50,有的1-500),直接比较MSE等绝对指标不公平。

**解决方案**: 指标归一化

```python
class MetricsNormalizer:
    def fit(self, metrics_dict):
        # 收集所有学科的同一指标值
        for name, values in all_metrics.items():
            scaler = MinMaxScaler()  # 归一化到[0,1]
            scaler.fit(np.array(values).reshape(-1, 1))
            self.scalers[name] = scaler
    
    def get_composite_score(self, metrics):
        weights = {
            'MAE': -0.15, 'MSE': -0.15, 'RMSE': -0.15,
            'R2': 0.30, 'MAPE': -0.15, 'Spearman': 0.10
        }
        score = 0
        for name, weight in weights.items():
            norm_val = metrics[name]
            if weight < 0:
                score += abs(weight) * (1 - norm_val)  # 误差类指标取反
            else:
                score += weight * norm_val
        return score
```

**综合评分设计**:
- 为不同指标赋予不同权重
- R²权重最高(0.30),因为它反映了模型的整体解释能力
- 误差类指标(MAE/MSE/RMSE/MAPE)被取反,越小的误差得分越高
- 最终得分在[0,1]区间,越高越好


### 结果展示与分析
##### 模型运行结果
部分的训练结果及对应的Loss 曲线图如下(完整见文件`q1运行结果.txt`以及文件夹`plots`)：
🔬 [ 1/22] 训练学科: AGRICULTURAL SCIENCES
  📊 数据划分: 训练=828 | 验证=276 | 测试=277
  🟢 训练完成: R²=0.7385, MAE=148.94, MAPE=29.27%
  📊 训练过程图已保存: results/dl_models_reloaded/plots\AGRICULTURAL_SCIENCES_training_history.png
  ![alt text](results/dl_models_reloaded/plots/AGRICULTURAL_SCIENCES_training_history.png)

────────────────────────────────────────────────────────────────────────────────
🔬 [ 2/22] 训练学科: BIOLOGY & BIOCHEMISTRY
  📊 数据划分: 训练=989 | 验证=330 | 测试=330
  🟢 训练完成: R²=0.9221, MAE=111.59, MAPE=27.81%
  📊 训练过程图已保存: results/dl_models_reloaded/plots\BIOLOGY_&_BIOCHEMISTRY_training_history.png
  ![alt text](results/dl_models_reloaded/plots/BIOLOGY_&_BIOCHEMISTRY_training_history.png)

────────────────────────────────────────────────────────────────────────────────
🔬 [ 3/22] 训练学科: CHEMISTRY
  📊 数据划分: 训练=1284 | 验证=428 | 测试=429
  🟢 训练完成: R²=0.9713, MAE=89.03, MAPE=14.00%
  📊 训练过程图已保存: results/dl_models_reloaded/plots\CHEMISTRY_training_history.png
  ![alt text](results/dl_models_reloaded/plots/CHEMISTRY_training_history.png)

完整的实验数据如下：
| 排名 | 学科名称 | 训练集 | 验证集 | 测试集 | MAE | MSE | RMSE | R² | MAPE | Spearman | 综合评分 |
|:----:|:--------------------------------|:------:|:------:|:------:|:--------:|:-----------:|:---------:|:------:|:--------:|:-----------:|:-----------:|
| 1 | CHEMISTRY | 1284 | 428 | 429 | 89.03 | 11231.09 | 105.98 | 0.9713 | 13.998 | 0.9993 | 0.9687 |
| 2 | ENVIRONMENT ECOLOGY | 1239 | 413 | 414 | 103.51 | 16374.96 | 127.96 | 0.9543 | 22.288 | 0.9995 | 0.9427 |
| 3 | MATERIALS SCIENCE | 948 | 316 | 316 | 103.91 | 15569.64 | 124.78 | 0.9182 | 24.976 | 0.9985 | 0.9280 |
| 4 | BIOLOGY & BIOCHEMISTRY | 989 | 330 | 330 | 111.59 | 17290.14 | 131.49 | 0.9221 | 27.813 | 0.9995 | 0.9262 |
| 5 | MOLECULAR BIOLOGY & GENETICS | 701 | 234 | 234 | 115.47 | 15446.83 | 124.29 | 0.8563 | 37.803 | 0.9997 | 0.9078 |
| 6 | IMMUNOLOGY | 705 | 236 | 236 | 116.54 | 19318.55 | 138.99 | 0.8245 | 33.307 | 0.9989 | 0.8935 |
| 7 | PHYSICS | 597 | 199 | 199 | 112.25 | 14491.70 | 120.38 | 0.8150 | 40.476 | 0.9976 | 0.8865 |
| 8 | PSYCHIATRY PSYCHOLOGY | 687 | 230 | 230 | 126.59 | 20757.78 | 144.08 | 0.8085 | 47.144 | 0.9977 | 0.8623 |
| 9 | NEUROSCIENCE & BEHAVIOR | 778 | 260 | 260 | 151.27 | 28608.40 | 169.14 | 0.7928 | 39.012 | 0.9993 | 0.8541 |
| 10 | PLANT & ANIMAL SCIENCE | 1170 | 390 | 390 | 156.49 | 42268.46 | 205.59 | 0.8676 | 23.553 | 0.9962 | 0.8395 |
| 11 | ENGINEERING | 1671 | 558 | 558 | 188.73 | 59192.46 | 243.30 | 0.9057 | 17.360 | 0.9992 | 0.8371 |
| 12 | AGRICULTURAL SCIENCES | 828 | 276 | 277 | 148.94 | 37513.91 | 193.69 | 0.7385 | 29.275 | 0.9982 | 0.8344 |
| 13 | COMPUTER SCIENCE | 517 | 173 | 173 | 130.70 | 20687.29 | 143.83 | 0.6742 | 53.926 | 0.9975 | 0.8279 |
| 14 | PHARMACOLOGY & TOXICOLOGY | 833 | 278 | 278 | 161.95 | 41213.38 | 203.01 | 0.7458 | 28.895 | 0.9985 | 0.8269 |
| 15 | GEOSCIENCES | 705 | 235 | 235 | 163.87 | 32894.46 | 181.37 | 0.6963 | 42.458 | 0.9997 | 0.8243 |
| 16 | SOCIAL SCIENCES, GENERAL | 1443 | 482 | 482 | 180.16 | 58373.54 | 241.61 | 0.8702 | 22.097 | 0.9853 | 0.7348 |
| 17 | SPACE SCIENCE | 141 | 47 | 48 | 62.57 | 4396.39 | 66.31 | 0.1233 | 73.384 | 0.9908 | 0.7266 |
| 18 | ECONOMICS & BUSINESS | 325 | 109 | 109 | 112.74 | 14912.85 | 122.12 | 0.4834 | 142.275 | 0.9928 | 0.6957 |
| 19 | MICROBIOLOGY | 481 | 161 | 161 | 188.46 | 43429.25 | 208.40 | 0.2052 | 68.394 | 0.9985 | 0.6756 |
| 20 | MATHEMATICS | 237 | 79 | 79 | 111.38 | 14846.32 | 121.85 | 0.0531 | 173.657 | 0.9957 | 0.6077 |
| 21 | MULTIDISCIPLINARY | 129 | 43 | 44 | 70.65 | 5746.30 | 75.80 | -0.6625 | 70.584 | 0.9858 | 0.5428 |
| 22 | CLINICAL MEDICINE | 4052 | 1351 | 1351 | 392.52 | 283058.28 | 532.03 | 0.9262 | 26.945 | 0.9982 | 0.5192 |


#### 评价模型的优劣
🏆 表现最佳的前5个学科 (按 composite_score 排序):
| 排名 | 学科名称 | R² | MAE | 综合评分 |
|:----:|:-------------------------------|:------:|:-------:|:-----------:|
| 1 | CHEMISTRY | 0.9713 | 89.03 | 0.9687 |
| 2 | ENVIRONMENT ECOLOGY | 0.9543 | 103.51 | 0.9427 |
| 3 | MATERIALS SCIENCE | 0.9182 | 103.91 | 0.9280 |
| 4 | BIOLOGY & BIOCHEMISTRY | 0.9221 | 111.59 | 0.9262 |
| 5 | MOLECULAR BIOLOGY & GENETICS | 0.8563 | 115.47 | 0.9078 |

⚠️ 需要改进的后5个学科 (按 composite_score 排序):
| 排名 | 学科名称 | R² | MAE | 综合评分 |
|:----:|:-------------------------------|:------:|:-------:|:-----------:|
| 1 | ECONOMICS & BUSINESS | 0.4834 | 112.74 | 0.6957 |
| 2 | MICROBIOLOGY | 0.2052 | 188.46 | 0.6756 |
| 3 | MATHEMATICS | 0.0531 | 111.38 | 0.6077 |
| 4 | MULTIDISCIPLINARY | -0.6625 | 70.65 | 0.5428 |
| 5 | CLINICAL MEDICINE | 0.9262 | 392.52 | 0.5192 |




