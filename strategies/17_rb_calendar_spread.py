#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略17 - 跨期套利：螺纹钢近远月价差策略
原理：
    利用螺纹钢期货不同到期月份的价差进行套利。
    当近月-远月价差偏离均值时，预期价差回归进行交易。

参数：
    - 近月合约：SHFE.rb2505
    - 远月合约：SHFE.rb2509
    - K线周期：30分钟
    - 价差窗口：20根K线
    - 开仓阈值：2倍标准差
    - 平仓阈值：0.5倍标准差

作者：kubangr / tqsdk-arbitrage
日期：2026-03-11
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np

# ============ 参数配置 ============
NEAR_SYMBOL = "SHFE.rb2505"     # 近月合约
FAR_SYMBOL = "SHFE.rb2509"     # 远月合约
KLINE_DURATION = 30 * 60       # K线周期：30分钟
WINDOW = 20                    # 价差滚动窗口
OPEN_THRESHOLD = 2.0           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.5          # 平仓阈值
LOT_NEAR = 1                   # 近月手数
LOT_FAR = 1                    # 远月手数

# ============ 价差计算 ============
def calc_spread(near_price, far_price):
    """计算近月-远月价差"""
    return near_price - far_price

def calc_zscore(spread_series, window=20):
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
    
    print("启动：螺纹钢近远月价差套利策略")
    print(f"监控：{NEAR_SYMBOL} vs {FAR_SYMBOL}")
    
    near_klines = api.get_kline_serial(NEAR_SYMBOL, KLINE_DURATION, data_length=60)
    far_klines = api.get_kline_serial(FAR_SYMBOL, KLINE_DURATION, data_length=60)
    
    position = 0  # 1: 多近月空远月, -1: 空近月多远月
    
    while True:
        api.wait_update()
        
        if api.is_changing(near_klines) or api.is_changing(far_klines):
            if len(near_klines) < WINDOW + 10 or len(far_klines) < WINDOW + 10:
                continue
            
            near_closes = near_klines['close'].values
            far_closes = far_klines['close'].values
            
            # 计算价差序列
            spreads = [calc_spread(near_closes[i], far_closes[i]) for i in range(len(near_closes))]
            
            # 计算Z-score
            zscore = calc_zscore(spreads, WINDOW)
            
            print(f"价差: {spreads[-1]:.2f}, Z-Score: {zscore:.2f}, 持仓: {position}")
            
            # 开仓信号
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    # 价差过高，预期回归，做空价差：空近月，多远月
                    position = -1
                    print(f"开仓：空近月多远月，价差={spreads[-1]:.2f}")
                elif zscore < -OPEN_THRESHOLD:
                    # 价差过低，预期回归，做多价差：多近月空远月
                    position = 1
                    print(f"开仓：多近月空远月，价差={spreads[-1]:.2f}")
            
            # 平仓信号
            elif position != 0:
                if abs(zscore) < CLOSE_THRESHOLD:
                    print(f"平仓：Z-score回归到{abs(zscore):.2f}")
                    position = 0

if __name__ == "__main__":
    main()
