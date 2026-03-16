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
| 03 | 跨品种套利：螺纹钢与铁矿石价差策略 | 跨品种套利 | SHFE.rb + DCE.i | [03_rb_i_spread.py](strategies/03_rb_i_spread.py) |
| 04 | 统计套利：黄金与白银比价回归策略 | 统计套利 | SHFE.au + SHFE.ag | [04_au_ag_ratio.py](strategies/04_au_ag_ratio.py) |
| 05 | 跨期套利：螺纹钢近远月价差回归策略 | 跨期套利 | SHFE.rb | [05_rb_spread_regression.py](strategies/05_rb_spread_regression.py) |
| 06 | 跨品种套利：螺纹钢与热卷价差策略 | 跨品种套利 | SHFE.rb + SHFE.hc | [06_rb_hc_spread.py](strategies/06_rb_hc_spread.py) |
| 07 | 跨品种套利：螺纹钢与焦炭价差策略 | 跨品种套利 | SHFE.rb + SHFE.j | [07_rb_j_spread.py](strategies/07_rb_j_spread.py) |
| 08 | 跨品种套利：大豆与豆粕价差策略 | 跨品种套利 | DCE.a + DCE.m | [08_a_m_spread.py](strategies/08_a_m_spread.py) |
| 09 | 铁矿石跨期套利策略 | 跨期套利 | DCE.i | [09_i_spread.py](strategies/09_i_spread.py) |
| 10 | 铜铝跨品种套利策略 | 跨品种套利 | SHFE.cu + SHFE.al | [10_cu_al_ratio.py](strategies/10_cu_al_ratio.py) |
| 11 | 跨期套利：螺纹钢近远月价差策略 | 跨期套利 | SHFE.rb | [11_rb_calendar_spread.py](strategies/11_rb_calendar_spread.py) |
| 12 | 跨品种套利：热卷与螺纹钢价差策略 | 跨品种套利 | SHFE.hc + SHFE.rb | [12_hc_rb_spread.py](strategies/12_hc_rb_spread.py) |
| 13 | 跨品种套利：螺纹钢与铁矿石价差策略 | 跨品种套利 | SHFE.rb + DCE.i | [13_rb_i_spread.py](strategies/13_rb_i_spread.py) |
| 14 | 跨品种套利：焦煤与焦炭价差策略 | 跨品种套利 | DCE.jm + DCE.j | [14_jm_j_spread.py](strategies/14_jm_j_spread.py) |
| 15 | 跨品种套利：螺纹钢与热卷价差策略 | 跨品种套利 | SHFE.rb + SHFE.hc | [15_hc_rb_spread.py](strategies/15_hc_rb_spread.py) |
| 16 | 跨品种套利：豆粕与菜粕价差策略 | 跨品种套利 | DCE.m + CZCE.rm | [16_rm_pm_spread.py](strategies/16_rm_pm_spread.py) |
| 17 | 跨期套利：螺纹钢近远月价差策略 | 跨期套利 | SHFE.rb | [17_rb_calendar_spread.py](strategies/17_rb_calendar_spread.py) |
| 18 | 跨品种套利：焦炭与焦煤价差策略 | 跨品种套利 | DCE.j + DCE.jm | [18_j_jm_spread.py](strategies/18_j_jm_spread.py) |
| 19 | 有色金属跨品种套利：铜锌价差策略 | 跨品种套利 | SHFE.cu + SHFE.zn | [19_cu_zn_spread.py](strategies/19_cu_zn_spread.py) |
| 20 | 农产品跨品种套利：豆粕菜粕价差策略 | 跨品种套利 | DCE.m + CZCE.rm | [20_meal_spread.py](strategies/20_meal_spread.py) |
| 21 | 截面动量套利：黑色系多品种截面多空 | 截面动量套利 | SHFE.rb + SHFE.hc + DCE.i + DCE.jm + DCE.j | [21_cross_section_momentum_arb.py](strategies/21_cross_section_momentum_arb.py) |
| 22 | 焦化利润三腿套利：焦煤→焦炭→螺纹钢 | 加工利润三腿套利 | DCE.jm + DCE.j + SHFE.rb | [22_crack_spread_three_leg.py](strategies/22_crack_spread_three_leg.py) |
| 23 | 跨品种对冲基金属套利策略 | 统计套利 | 贵金属/基本金属 | [23_precious_metals_hedge.py](strategies/23_precious_metals_hedge.py) |
| 24 | 产业链利润套利策略 | 产业链套利 | 黑色/有色 | [24_industrial_chain_arb.py](strategies/24_industrial_chain_arb.py) |

## 策略分类

### 📅 跨期套利（Calendar Spread）
利用同品种不同月份合约价差的均值回归特性。

### 🔄 跨品种套利（Cross-Commodity）
利用原料与成品之间的加工利润回归，如黑色系（铁矿石→螺纹钢）、有色金属（铜铝）等。

### 📊 统计套利（Statistical Arbitrage）
基于协整关系或相关性的配对交易策略。

### 📐 截面动量套利（Cross-Section Momentum）
对多品种同时排名，做多强势品种、做空弱势品种，形成截面多空组合。

### 🔗 加工利润套利（Crack / Processing Spread）
基于原料→中间品→成品的产业链利润回归，多腿联动交易。

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

**持续更新中，欢迎 Star ⭐ 关注**

*更新时间：2026-03-13*
