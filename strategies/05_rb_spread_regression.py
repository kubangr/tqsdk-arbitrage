#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略05 - 跨期套利：螺纹钢近远月价差回归策略
原理：
    螺纹钢期货不同月份的合约存在价差，当价差偏离历史均值时，
    价差倾向于回归。本策略做多价差（买入近月，卖出远月），
    等待价差回归时平仓获利。

参数：
    - 近月合约：SHFE.rb2505
    - 远月合约：SHFE.rb2509
    - 价差窗口：60根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：回归到0.3倍标准差以内

适用行情：近远月价差偏离均值时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
NEAR_SYMBOL = "SHFE.rb2505"    # 近月合约
FAR_SYMBOL = "SHFE.rb2509"     # 远月合约
KLINE_DURATION = 60 * 60       # K线周期：1小时
WINDOW = 60                    # 价差滚动窗口
OPEN_THRESHOLD = 1.5           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.3          # 平仓阈值
LOT_NEAR = 1                   # 近月手数
LOT_FAR = 1                    # 远月手数

# ============ 价差计算 ============
def calc_spread(near_price, far_price):
    """计算近远月价差"""
    return near_price - far_price

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
    
    print("启动：螺纹钢跨期套利策略")
    
    near_quote = api.get_quote(NEAR_SYMBOL)
    far_quote = api.get_quote(FAR_SYMBOL)
    
    near_klines = api.get_kline_serial(NEAR_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    far_klines = api.get_kline_serial(FAR_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    spread_history = []
    position = 0  # 0: 空仓, 1: 多价差(买近卖远), -1: 空价差(卖近买远)
    
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
            
            # 无持仓时
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空价差, Z-Score: {zscore:.2f}")
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多价差, Z-Score: {zscore:.2f}")
                    position = 1
                    
            # 持仓时检查平仓
            elif position == 1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归, Z-Score: {zscore:.2f}")
                position = 0
            elif position == -1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归, Z-Score: {zscore:.2f}")
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
