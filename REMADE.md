## 环境

- Python 3.10.8

---

## 回测模块

- 入口文件：main.py
- 数据源：iFinD 官方数据接口
- 用途：策略回测、历史数据验证

---

## 实盘模块

- 入口文件：live_runner.py
- 数据源：iFinD 官方实时数据接口
- 交易执行：
  - easytrader（无官方交易API，连接同花顺客户端，部分功能存在兼容性问题）
  - pyautogui（UI自动化下单/撤单/输入操作，弥补easytrader兼容性问题）
- 注意事项：
  - 当前实盘方案基于 UI 自动化实现，并非券商官方 API
  - 同花顺版本差异可能导致 easytrader 部分功能失效 
  - easytrader登陆xiadan.exe不稳定，建议先登录同花顺交易账号。
 