# tqsdk-arbitrage

> 基于 **TqSdk** 的套利策略集合，持续更新中。

## 项目简介

本仓库专注于**套利类量化策略**，涵盖跨期套利、跨品种套利、统计套利等方向。  
所有策略使用 [天勤量化 TqSdk](https://github.com/shinnytech/tqsdk-python) 实现，可直接对接实盘账户。

## 策略列表

| # | 策略名称 | 类型 | 品种 | 文件 |
|---|---------|------|------|------|
| 01 | 螺纹钢跨期套利 | 跨期套利 | SHFE.rb | [01_calendar_spread_rb.py](strategies/01_calendar_spread_rb.py) |
| 02 | 铁矿石+螺纹钢跨品种套利（钢厂利润回归） | 跨品种套利 | SHFE.rb + DCE.i | [02_cross_commodity_rb_i.py](strategies/02_cross_commodity_rb_i.py) |

## 策略分类

### 📅 跨期套利（Calendar Spread）
利用同品种不同月份合约价差的均值回归特性。

### 🔄 跨品种套利（Cross-Commodity）
利用原料与成品之间的加工利润回归，如黑色系（铁矿石→螺纹钢）。

### 📊 统计套利（Statistical Arbitrage）
基于协整关系或相关性的配对交易策略。

## 环境要求

```bash
pip install tqsdk numpy pandas
```

## 使用说明

1. 替换代码中 `YOUR_ACCOUNT` / `YOUR_PASSWORD` 为你的天勤账号
2. 根据实际行情调整合约代码（如 rb2405 → 当前主力合约）
3. 建议先用模拟账户（`TqSim()`）回测后再上实盘

## 风险提示

- 套利策略仍有风险，极端行情下相关性可能失效
- 请充分测试后再使用于实盘
- 本仓库策略仅供学习研究，不构成投资建议

---

持续更新中，欢迎 Star ⭐ 关注
