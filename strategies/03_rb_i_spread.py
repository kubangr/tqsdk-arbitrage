#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略03 - 跨品种套利：螺纹钢与铁矿石价差策略
原理：
    螺纹钢（RB）与铁矿石（I）存在较强的产业链上下游关系。
    当两者价差偏离历史均值时，进行均值回归交易。
    螺纹钢成本 = 铁矿石 * 1.6 + 其他成本
    合理价差范围应在历史均值 ±1.5 倍标准差内。

参数：
    - 价差窗口：60根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：0.3倍标准差
    - 止损：2.5倍标准差

适用行情：螺纹钢与铁矿石价差偏离时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np
import pandas as pd

# ============ 参数配置 ============
RB_SYMBOL = "SHFE.rb2405"      # 螺纹钢合约
I_SYMBOL = "SHFE.i2405"        # 铁矿石合约
KLINE_DURATION = 60 * 60       # K线周期：1小时
WINDOW = 60                     # 价差滚动窗口
OPEN_THRESHOLD = 1.5           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.3          # 平仓阈值
STOP_THRESHOLD = 2.5           # 止损阈值
LOT_RB = 1                     # 螺纹钢手数
LOT_I = 1                      # 铁矿石手数（根据合约乘数调整）

# ============ 价差计算 ============
def calc_spread(rb_price, i_price):
    """计算螺纹钢-铁矿石价差（单位：元/吨）"""
    return rb_price - i_price * 1.6  # 考虑生产比例

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
    
    print("启动：螺纹钢-铁矿石跨品种套利策略")
    
    rb_quote = api.get_quote(RB_SYMBOL)
    i_quote = api.get_quote(I_SYMBOL)
    
    rb_klines = api.get_kline_serial(RB_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    i_klines = api.get_kline_serial(I_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    position = 0  # 1: 做多价差(多RB空I), -1: 做空价差(空RB多I), 0: 空仓
    
    while True:
        api.wait_update()
        
        if len(rb_klines) < WINDOW or len(i_klines) < WINDOW:
            continue
        
        # 计算最新价差序列
        rb_prices = [k['close'] for k in rb_klines[-WINDOW:]]
        i_prices = [k['close'] for k in i_klines[-WINDOW:]]
        
        spreads = [calc_spread(rb, i) for rb, i in zip(rb_prices, i_prices)]
        zscore = calc_zscore(spreads)
        
        current_spread = spreads[-1]
        
        # 交易逻辑
        if position == 0:
            # 做多价差：价差过低（RB相对便宜）
            if zscore < -OPEN_THRESHOLD:
                print(f"价差={current_spread:.2f}, Z={zscore:.2f} → 做多价差(多RB空I)")
                api.insert_order(symbol=RB_SYMBOL, direction="long", offset="open", volume=LOT_RB)
                api.insert_order(symbol=I_SYMBOL, direction="short", offset="open", volume=LOT_I)
                position = 1
            
            # 做空价差：价差过高（RB相对昂贵）
            elif zscore > OPEN_THRESHOLD:
                print(f"价差={current_spread:.2f}, Z={zscore:.2f} → 做空价差(空RB多I)")
                api.insert_order(symbol=RB_SYMBOL, direction="short", offset="open", volume=LOT_RB)
                api.insert_order(symbol=I_SYMBOL, direction="long", offset="open", volume=LOT_I)
                position = -1
        
        elif position == 1:
            # 做多价差仓位，价差回归时平仓
            if zscore > -CLOSE_THRESHOLD or zscore < -STOP_THRESHOLD:
                print(f"价差={current_spread:.2f}, Z={zscore:.2f} → 平多价差仓位")
                api.insert_order(symbol=RB_SYMBOL, direction="short", offset="close", volume=LOT_RB)
                api.insert_order(symbol=I_SYMBOL, direction="long", offset="close", volume=LOT_I)
                position = 0
        
        elif position == -1:
            # 做空价差仓位，价差回归时平仓
            if zscore < CLOSE_THRESHOLD or zscore > STOP_THRESHOLD:
                print(f"价差={current_spread:.2f}, Z={zscore:.2f} → 平空价差仓位")
                api.insert_order(symbol=RB_SYMBOL, direction="long", offset="close", volume=LOT_RB)
                api.insert_order(symbol=I_SYMBOL, direction="short", offset="close", volume=LOT_I)
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
