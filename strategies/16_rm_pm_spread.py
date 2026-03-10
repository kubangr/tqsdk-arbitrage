#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略16 - 跨品种套利：豆粕与菜粕价差策略
原理：
    豆粕（RM）和菜粕（PM）同属蛋白饲料，价格高度相关。
    两者价差受季节性供需和替代效应影响，当价差偏离历史均值时进行均值回归交易。
    价差 = 豆粕价格 - 菜粕价格

参数：
    - 豆粕合约：CZCE.rm2505
    - 菜粕合约：CZCE.pm2505
    - K线周期：1小时
    - 价差窗口：50根K线
    - 开仓阈值：1.3倍标准差
    - 平仓阈值：0.25倍标准差

作者：kubangr / tqsdk-arbitrage
日期：2026-03-10
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np

# ============ 参数配置 ============
RM_SYMBOL = "CZCE.rm2505"      # 豆粕合约
PM_SYMBOL = "CZCE.pm2505"      # 菜粕合约
KLINE_DURATION = 60 * 60       # K线周期：1小时
WINDOW = 50                    # 价差滚动窗口
OPEN_THRESHOLD = 1.3           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.25         # 平仓阈值
LOT_RM = 1                     # 豆粕手数
LOT_PM = 1                     # 菜粕手数

# ============ 价差计算 ============
def calc_spread(rm_price, pm_price):
    """计算豆粕-菜粕价差"""
    return rm_price - pm_price

def calc_zscore(spread_series, window=50):
    """计算价差的 Z-Score"""
    if len(spread_series) < window:
        return 0.0
    recent = spread_series[-window:]
    mean = np.mean(recent)
    std = np.std(recent)
    if std == 0:
        return 0.0
    return (spread_series[-1] - mean) / std

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"), sim=TqSim())
    
    print("启动：豆粕-菜粕价差套利策略")
    print(f"监控：{RM_SYMBOL} vs {PM_SYMBOL}")
    
    rm_klines = api.get_kline_serial(RM_SYMBOL, KLINE_DURATION, data_length=100)
    pm_klines = api.get_kline_serial(PM_SYMBOL, KLINE_DURATION, data_length=100)
    
    position = 0  # 1: 多RM空PM, -1: 空RM多PM
    
    while True:
        api.wait_update()
        
        if api.is_changing(rm_klines) or api.is_changing(pm_klines):
            if len(rm_klines) < WINDOW + 10 or len(pm_klines) < WINDOW + 10:
                continue
            
            rm_closes = rm_klines['close'].values
            pm_closes = pm_klines['close'].values
            
            # 计算价差序列
            spreads = [calc_spread(rm_closes[i], pm_closes[i]) for i in range(len(rm_closes))]
            
            # 计算Z-score
            zscore = calc_zscore(spreads, WINDOW)
            
            print(f"价差: {spreads[-1]:.2f}, Z-Score: {zscore:.2f}, 持仓: {position}")
            
            # 开仓信号
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    # 价差过高，预期回归，做空价差：空RM，多PM
                    position = -1
                    print(f"开仓：空RM多PM，价差={spreads[-1]:.2f}")
                elif zscore < -OPEN_THRESHOLD:
                    # 价差过低，预期回归，做多价差：多RM，空PM
                    position = 1
                    print(f"开仓：多RM空PM，价差={spreads[-1]:.2f}")
            
            # 平仓信号
            elif position != 0:
                if abs(zscore) < CLOSE_THRESHOLD:
                    print(f"平仓：Z-score回归到{abs(zscore):.2f}")
                    position = 0

if __name__ == "__main__":
    main()
