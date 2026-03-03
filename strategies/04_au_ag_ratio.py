#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略04 - 统计套利：黄金与白银比价回归策略
原理：
    黄金（AU）与白银（AG）历史上存在稳定的比价关系。
    当金银比价偏离历史均值超过阈值时，进行比价回归交易。
    金银比 = AU价格 / AG价格
    历史均值约在 60-80 区间波动。

参数：
    - 比价窗口：120根K线
    - 开仓阈值：2.0倍标准差
    - 平仓阈值：0.5倍标准差
    - 止损：3.0倍标准差

适用行情：金银比价偏离均值时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
AU_SYMBOL = "SHFE.au2406"      # 黄金合约
AG_SYMBOL = "SHFE.ag2406"      # 白银合约
KLINE_DURATION = 60 * 60       # K线周期：1小时
WINDOW = 120                   # 比价滚动窗口
OPEN_THRESHOLD = 2.0           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.5         # 平仓阈值
STOP_THRESHOLD = 3.0          # 止损阈值
LOT_AU = 1                    # 黄金手数
LOT_AG = 10                   # 白银手数（根据合约乘数调整）

# ============ 比价计算 ============
def calc_ratio(a, b):
    """计算金银比价"""
    if b == 0:
        return 0.0
    return a / b

def calc_zscore(ratio_series):
    """计算比价的 Z-Score"""
    mean = np.mean(ratio_series)
    std = np.std(ratio_series)
    if std == 0:
        return 0.0
    return (ratio_series[-1] - mean) / std

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：黄金-白银统计套利策略")
    
    au_quote = api.get_quote(AU_SYMBOL)
    ag_quote = api.get_quote(AG_SYMBOL)
    
    au_klines = api.get_kline_serial(AU_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    ag_klines = api.get_kline_serial(AG_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    position = 0  # 1: 做空比价(空AU多AG), -1: 做多比价(多AU空AG), 0: 空仓
    
    while True:
        api.wait_update()
        
        if len(au_klines) < WINDOW or len(ag_klines) < WINDOW:
            continue
        
        # 计算最新比价序列
        au_prices = [k['close'] for k in au_klines[-WINDOW:]]
        ag_prices = [k['close'] for k in ag_klines[-WINDOW:]]
        
        ratios = [calc_ratio(au, ag) for au, ag in zip(au_prices, ag_prices)]
        zscore = calc_zscore(ratios)
        
        current_ratio = ratios[-1]
        
        # 交易逻辑
        if position == 0:
            # 做空比价：比价过高（金相对于银太贵）
            if zscore > OPEN_THRESHOLD:
                print(f"金银比={current_ratio:.4f}, Z={zscore:.2f} → 做空比价(空AU多AG)")
                api.insert_order(symbol=AU_SYMBOL, direction="short", offset="open", volume=LOT_AU)
                api.insert_order(symbol=AG_SYMBOL, direction="long", offset="open", volume=LOT_AG)
                position = 1
            
            # 做多比价：比价过低（银相对于金太贵）
            elif zscore < -OPEN_THRESHOLD:
                print(f"金银比={current_ratio:.4f}, Z={zscore:.2f} → 做多比价(多AU空AG)")
                api.insert_order(symbol=AU_SYMBOL, direction="long", offset="open", volume=LOT_AU)
                api.insert_order(symbol=AG_SYMBOL, direction="short", offset="open", volume=LOT_AG)
                position = -1
        
        elif position == 1:
            # 做空比价仓位，比价回归时平仓
            if zscore < CLOSE_THRESHOLD or zscore > STOP_THRESHOLD:
                print(f"金银比={current_ratio:.4f}, Z={zscore:.2f} → 平做空比价仓位")
                api.insert_order(symbol=AU_SYMBOL, direction="long", offset="close", volume=LOT_AU)
                api.insert_order(symbol=AG_SYMBOL, direction="short", offset="close", volume=LOT_AG)
                position = 0
        
        elif position == -1:
            # 做多比价仓位，比价回归时平仓
            if zscore > -CLOSE_THRESHOLD or zscore < -STOP_THRESHOLD:
                print(f"金银比={current_ratio:.4f}, Z={zscore:.2f} → 平做多比价仓位")
                api.insert_order(symbol=AU_SYMBOL, direction="short", offset="close", volume=LOT_AU)
                api.insert_order(symbol=AG_SYMBOL, direction="long", offset="close", volume=LOT_AG)
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
