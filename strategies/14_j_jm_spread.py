#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略14 - 跨品种套利：焦煤与焦炭价差策略
原理：
    焦煤（JM）是焦炭（J）的上游原料，两者价格高度相关。
    当两者价差偏离历史均值时，进行均值回归交易。
    价差 = 焦炭价格 - 焦煤价格

参数：
    - 焦炭合约：ZCE.j2505
    - 焦煤合约：ZCE.jm2505
    - K线周期：1小时
    - 价差窗口：40根K线
    - 开仓阈值：1.2倍标准差
    - 平仓阈值：0.2倍标准差

作者：kubangr / tqsdk-arbitrage
日期：2026-03-09
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np

# ============ 参数配置 ============
J_SYMBOL = "ZCE.j2505"        # 焦炭合约
JM_SYMBOL = "ZCE.jm2505"      # 焦煤合约
KLINE_DURATION = 60 * 60       # K线周期：1小时
WINDOW = 40                    # 价差滚动窗口
OPEN_THRESHOLD = 1.2           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.2          # 平仓阈值
LOT_J = 1                     # 焦炭手数
LOT_JM = 1                    # 焦煤手数

# ============ 价差计算 ============
def calc_spread(j_price, jm_price):
    """计算焦炭-焦煤价差"""
    return j_price - jm_price

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
    api = TqApi(auth=TqAuth("账号", "密码"), sim=TqSim())
    
    print("启动：焦炭-焦煤价差套利策略")
    print(f"监控：{J_SYMBOL} vs {JM_SYMBOL}")
    
    j_klines = api.get_kline_serial(J_SYMBOL, KLINE_DURATION, data_length=80)
    jm_klines = api.get_kline_serial(JM_SYMBOL, KLINE_DURATION, data_length=80)
    
    position = 0  # 1: 多J空JM, -1: 空J多JM
    
    while True:
        api.wait_update()
        
        if api.is_changing(j_klines) or api.is_changing(jm_klines):
            if len(j_klines) < WINDOW + 10 or len(jm_klines) < WINDOW + 10:
                continue
            
            j_closes = j_klines['close'].values
            jm_closes = jm_klines['close'].values
            
            # 计算价差序列
            spreads = [calc_spread(j_closes[i], jm_closes[i]) for i in range(len(j_closes))]
            
            # 计算Z-score
            zscore = calc_zscore(spreads)
            
            print(f"价差: {spreads[-1]:.2f}, Z-Score: {zscore:.2f}, 持仓: {position}")
            
            # 开仓信号
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    # 价差过高，预期回归，做空价差：空J，多JM
                    position = -1
                    print(f"开仓：空J多JM，价差={spreads[-1]:.2f}")
                elif zscore < -OPEN_THRESHOLD:
                    # 价差过低，预期回归，做多价差：多J，空JM
                    position = 1
                    print(f"开仓：多J空JM，价差={spreads[-1]:.2f}")
            
            # 平仓信号
            elif position != 0:
                if abs(zscore) < CLOSE_THRESHOLD:
                    print(f"平仓：Z-score回归")
                    position = 0

if __name__ == "__main__":
    main()
