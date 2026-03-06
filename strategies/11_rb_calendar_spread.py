#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略11 - 跨期套利：螺纹钢近远月价差策略
原理：
    利用螺纹钢不同交割月份的价差进行套利。
    当近月-远月价差偏离历史均值时，进行均值回归交易。

参数：
    - 近月合约：SHFE.rb2505
    - 远月合约：SHFE.rb2510
    - 价差窗口：40根K线
    - 开仓阈值：1.2倍标准差
    - 平仓阈值：0.2倍标准差

作者：kubangr / tqsdk-arbitrage
日期：2026-03-06
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np

# ============ 参数配置 ============
NEAR_SYMBOL = "SHFE.rb2505"    # 近月合约
FAR_SYMBOL = "SHFE.rb2510"    # 远月合约
KLINE_DURATION = 60 * 30      # K线周期：30分钟
WINDOW = 40                    # 价差滚动窗口
OPEN_THRESHOLD = 1.2           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.2          # 平仓阈值
LOT_SIZE = 1                   # 每次交易手数

# ============ 价差计算 ============
def calc_spread(near_price, far_price):
    """计算近月-远月价差"""
    return near_price - far_price

def calc_zscore(spread_series):
    """计算价差的 Z-Score"""
    if len(spread_series) < WINDOW:
        return 0.0
    recent = spread_series[-WINDOW:]
    mean = np.mean(recent)
    std = np.std(recent)
    if std == 0:
        return 0.0
    return (spread_series[-1] - mean) / std

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("13556817485", "asd159753"), sim=TqSim())
    
    # 获取行情
    near_kline = api.get_kline_serial(NEAR_SYMBOL, KLINE_DURATION)
    far_kline = api.get_kline_serial(FAR_SYMBOL, KLINE_DURATION)
    
    # 持仓状态
    position = 0  # 1: 多近空远, -1: 空近多远, 0: 空仓
    
    print(f"启动螺纹钢跨期套利策略")
    print(f"近月:{NEAR_SYMBOL} 远月:{FAR_SYMBOL}")
    
    spread_history = []
    
    while True:
        api.wait_update()
        
        if len(near_kline) < WINDOW + 1 or len(far_kline) < WINDOW + 1:
            continue
        
        near_price = near_kline["close"][-1]
        far_price = far_kline["close"][-1]
        spread = calc_spread(near_price, far_price)
        spread_history.append(sppread)
        
        if len(spread_history) > 200:
            spread_history = spread_history[-200:]
        
        zscore = calc_zscore(spread_history)
        
        # 交易逻辑
        if position == 0:
            if zscore > OPEN_THRESHOLD:
                # 价差过高，预期收窄，做空价差（空近月多远月）
                print(f"[开空价差] 近月:{near_price:.0f} 远月:{far_price:.0f} 价差:{spread:.0f} Z:{zscore:.2f}")
                position = -1
            elif zscore < -OPEN_THRESHOLD:
                # 价差过低，预期扩大，做多价差（多近月空远月）
                print(f"[开多价差] 近月:{near_price:.0f} 远月:{far_price:.0f} 价差:{spread:.0f} Z:{zscore:.2f}")
                position = 1
        else:
            if abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差:{spread:.0f} Z:{zscore:.2f}")
                position = 0

if __name__ == "__main__":
    main()
