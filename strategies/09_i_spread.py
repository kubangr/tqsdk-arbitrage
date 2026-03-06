#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略09 - 铁矿石跨期套利策略
原理：
    利用铁矿石不同到期月份合约之间的价差进行套利。
    当近月与远月合约价差偏离历史均值时，进行价差回归交易。

参数：
    - 近月合约：DCE.i2505
    - 远月合约：DCE.i2509
    - 周期：30分钟
    - 价差窗口：30根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：回归到0.3倍标准差

适用行情：跨期价差偏离均值时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
NEAR_SYMBOL = "DCE.i2505"       # 铁矿石近月
FAR_SYMBOL = "DCE.i2509"        # 铁矿石远月
KLINE_DURATION = 30 * 60        # 30分钟K线
WINDOW = 30                     # 价差滚动窗口
OPEN_THRESHOLD = 1.5            # 开仓阈值
CLOSE_THRESHOLD = 0.3           # 平仓阈值

# ============ 价差计算 ============
def calc_spread(near_price, far_price):
    """计算跨期价差"""
    return far_price - near_price

def calc_zscore(spread_series):
    """计算价差的 Z-Score"""
    mean = np.mean(spread_series)
    std = np.std(spread_series)
    if std == 0:
        return 0.0
    return (spread_series[-1] - mean) / std

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：铁矿石跨期套利策略")
    
    near_quote = api.get_quote(NEAR_SYMBOL)
    far_quote = api.get_quote(FAR_SYMBOL)
    
    near_klines = api.get_kline_serial(NEAR_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    far_klines = api.get_kline_serial(FAR_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    spread_history = []
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(near_quote) or api.is_changing(far_quote):
            near_price = near_quote.last_price
            far_price = far_quote.last_price
            
            if near_price <= 0 or far_price <= 0:
                continue
            
            spread = calc_spread(near_price, far_price)
            spread_history.append(spread)
            
            if len(spread_history) < WINDOW:
                continue
            
            recent_spread = spread_history[-WINDOW:]
            zscore = calc_zscore(recent_spread)
            
            print(f"近月: {near_price}, 远月: {far_price}, 价差: {spread:.2f}, Z-Score: {zscore:.2f}")
            
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空价差(买近卖远), Z-Score: {zscore:.2f}")
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多价差(卖近买远), Z-Score: {zscore:.2f}")
                    position = 1
                    
            elif position == 1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归, Z-Score: {zscore:.2f}")
                position = 0
            elif position == -1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归, Z-Score: {zscore:.2f}")
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
