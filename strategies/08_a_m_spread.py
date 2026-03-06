#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略08 - 跨品种套利：大豆与豆粕价差策略
原理：
    大豆（豆一A）和豆粕（豆粕M）是产业链上下游关系。
    当两者价差偏离历史均值时，进行价差回归交易。

参数：
    - A合约：DCE.a2505
    - M合约：DCE.m2505
    - 价差窗口：50根K线
    - 开仓阈值：1.6倍标准差
    - 平仓阈值：回归到0.3倍标准差以内
    - 手数配比：1:2（豆粕2手对大豆1手）

适用行情：A-M价差偏离均值时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
A_SYMBOL = "DCE.a2505"         # 大豆（豆一）合约
M_SYMBOL = "DCE.m2505"         # 豆粕合约
KLINE_DURATION = 60 * 60       # K线周期：1小时
WINDOW = 50                    # 价差滚动窗口
OPEN_THRESHOLD = 1.6           # 开仓阈值
CLOSE_THRESHOLD = 0.3          # 平仓阈值
LOT_A = 1                       # 大豆手数
LOT_M = 2                       # 豆粕手数

# ============ 价差计算 ============
def calc_spread(a_price, m_price):
    """计算品种间价差（大豆-豆粕*2）"""
    return a_price - m_price * LOT_M / LOT_A

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
    
    print("启动：大豆-豆粕跨品种套利策略")
    
    a_quote = api.get_quote(A_SYMBOL)
    m_quote = api.get_quote(M_SYMBOL)
    
    a_klines = api.get_kline_serial(A_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    m_klines = api.get_kline_serial(M_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    spread_history = []
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(a_quote) or api.is_changing(m_quote):
            a_price = a_quote.last_price
            m_price = m_quote.last_price
            
            if a_price <= 0 or m_price <= 0:
                continue
                
            spread = calc_spread(a_price, m_price)
            spread_history.append(spread)
            
            if len(spread_history) < WINDOW:
                continue
                
            recent_spread = spread_history[-WINDOW:]
            zscore = calc_zscore(recent_spread)
            
            print(f"A: {a_price}, M: {m_price}, 价差: {spread:.2f}, Z-Score: {zscore:.2f}")
            
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空A-M价差, Z-Score: {zscore:.2f}")
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多A-M价差, Z-Score: {zscore:.2f}")
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
