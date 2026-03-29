## 一、量化交易初架构
    stock_trading/
    ├── config/                     # 配置中心
    │   ├── settings.py            # 全局参数配置
    │   ├── instruments.py         # 合约/标的配置
    │   └── strategy_params.yaml   # 策略参数文件
    │
    ├── models/                     # 模型服务层
    │   ├── __init__.py
    │   ├── base_model.py          # 模型基类，定义统一接口
    │   ├── zhipu_model.py         # zhipu模型实现
    │   ├── factory.py             # 模型工厂，根据配置创建模型实例
    │   ├── cache.py               # 模型结果缓存（支持内存/Redis/文件）
    │   └── exceptions.py          # 自定义异常
    │ 
    ├── data/                      # 数据管理
    │   ├── raw/                   # 原始数据（CSV/HDF5）
    │   ├── processed/             # 清洗后数据
    │   └── __init__.py
    │
    ├── strategies/                # 策略库
    │   ├── __init__.py
    │   ├── base_strategy.py      # 基础策略模板
    │   ├── sma_cross.py          # 双均线策略
    │   └── pairs_trading.py      # 套利策略（多标的）
    │
    ├── indicators/                # 自定义指标
    │   ├── __init__.py
    │   ├── kdj.py                # KDJ指标
    │   └── volatility_ratio.py   # 波动率指标
    │
    ├── analyzers/                 # 自定义分析器
    │   ├── __init__.py
    │   └── risk_metrics.py       # 风险指标计算
    │
    ├── utils/                     # 工具函数
    │   ├── __init__.py
    │   ├── data_loader.py        # 数据加载器
    │   ├── logger.py             # 日志管理
    │   ├── plotter.py            # 图表绘制
    │   └── performance_report.py # 绩效报告生成
    │
    ├── results/                   # 回测结果输出
    │   ├── backtest_logs/         # 回测日志
    │   ├── equity_curves/         # 资金曲线图
    │   ├── trades/                # 交易明细CSV
    │   └── performance_reports/   # 绩效报告PDF
    │
    ├── main.py                    # 主入口（单策略回测）
    ├── optimizer.py               # 参数优化入口
    ├── live_runner.py             # 实盘交易入口
    └── requirements.txt           # 依赖包


## 二、单股回测
### 1.未实现：
    instruments.py         # 合约/标的配置
    strategy_params.yaml   # 策略参数文件
    indicators/            # 自定义指标
    pairs_trading.py       # 套利策略（多标的）
    ache.py                # 模型结果缓存（支持内存/Redis/文件）
    exceptions.py          # 自定义异常
    performance_report.py  # 绩效报告生成
    backtest_logs/         # 回测日志
    equity_curves/         # 资金曲线图
    trades/                # 交易明细CSV
    performance_reports/   # 绩效报告PDF
    optimizer.py           # 参数优化入口
    live_runner.py         # 实盘交易入口
### 2.需完善：
    1.获取数据加入随机代理IP
    2.获取的新闻数据无法达到要求（时间，内容）
    3.zhipu模型情感分析结果全为0
    4.策略未包含weekly, monthly（完整daily, weekly, monthly）

## 三、实盘量化框架（计划）
    加入Redis 缓存层、数据库操作层

    stock_trading/
    ├── config/                     # 配置中心			改造：含数据库、Redis
    │   ├── settings.py            # 全局参数配置
    │   ├── instruments.py         # 合约/标的配置
    │   └── strategy_params.yaml   # 策略参数文件
    │
    ├── models/                     # 模型服务层
    │   ├── __init__.py
    │   ├── base_model.py          # 模型基类，定义统一接口
    │   ├── deepseek_model.py      # DeepSeek模型实现
    │   ├── factory.py             # 模型工厂，根据配置创建模型实例
    │   ├── cache.py               # 模型结果缓存（支持内存/Redis/文件）  改造：移除
    │   └── exceptions.py          # 自定义异常
    │ 
    ├── data/                      # 数据管理
    │   ├── raw/                   # 原始数据（CSV/HDF5）
    │   ├── processed/             # 清洗后数据
    │   └── __init__.py
    │
    ├── strategies/                # 策略库
    │   ├── __init__.py
    │   ├── base_strategy.py      # 基础策略模板		改造：支持 Redis 状态
    │   ├── sma_cross.py          # 双均线策略
    │   └── pairs_trading.py      # 套利策略（多标的）
    │
    ├── indicators/                # 自定义指标
    │   ├── __init__.py
    │   ├── kdj.py                # KDJ指标
    │   └── volatility_ratio.py   # 波动率指标
    │
    ├── analyzers/                 # 自定义分析器
    │   ├── __init__.py
    │   └── risk_metrics.py       # 风险指标计算
    │
    ├── utils/                     # 工具函数
    │   ├── __init__.py
    │   ├── data_loader.py        # 数据加载器			改造：支持数据库/Redis
    │   ├── logger.py             # 日志管理
    │   ├── plotter.py            # 图表绘制
    │   └── performance_report.py # 绩效报告生成
    │
    ├── results/                   # 回测结果输出
    │   ├── backtest_logs/         # 回测日志
    │   ├── equity_curves/         # 资金曲线图
    │   ├── trades/                # 交易明细CSV
    │   └── performance_reports/   # 绩效报告PDF
    │
    ├── main.py                    # 主入口（单策略回测）
    ├── optimizer.py               # 参数优化入口
    ├── live_runner.py             # 实盘交易入口
    └── requirements.txt           # 依赖包
    -----------------------新增-----------------------
    │
    ├── live_runner.py                 # 实盘入口（新增）
    ├── scripts/                       # 运维脚本（新增）
    │   ├── init_db.py                 # 初始化数据库
    │   └── archive_data.py            # 数据归档
    │
    ├── db/                            # 数据库操作层（新增）
    │   ├── __init__.py
    │   ├── models.py                  # SQLAlchemy 模型
    │   ├── session.py                 # 会话管理
    │   └── repositories.py            # 数据访问层
    │
    ├── cache/                         # Redis 缓存层（新增）
    │   ├── __init__.py
    │   ├── redis_client.py            # Redis 连接池
    │   ├── market_cache.py            # 实时行情缓存
    │   ├── state_cache.py             # 策略状态缓存
    │   ├── signal_queue.py            # 信号队列
    │   ├── model_cache.py             # 模型结果缓存
    │   └── rate_limiter.py            # 限流器
    │
    ├── services/                      # 业务服务层（新增）
    │   ├── __init__.py
    │   ├── data_service.py            # 统一数据服务
    │   ├── order_service.py           # 订单服务
    │   └── risk_service.py            # 风控服务
