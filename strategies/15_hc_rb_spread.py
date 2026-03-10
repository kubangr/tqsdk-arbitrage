#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略15 - 跨品种套利：螺纹钢与热卷价差策略
原理：
    螺纹钢（RB）和热卷（HC）同属钢材系列，价格高度相关。
    两者价差受供需关系影响，当价差偏离历史均值时进行均值回归交易。
    价差 = 热卷价格 - 螺纹钢价格

参数：
    - 螺纹钢合约：SHFE.rb2505
    - 热卷合约：SHFE.hc2505
    - K线周期：30分钟
    - 价差窗口：30根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：0.3倍标准差

作者：kubangr / tqsdk-arbitrage
日期：2026-03-10
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np

# ============ 参数配置 ============
RB_SYMBOL = "SHFE.rb2505"      # 螺纹钢合约
HC_SYMBOL = "SHFE.hc2505"      # 热卷合约
KLINE_DURATION = 30 * 60       # K线周期：30分钟
WINDOW = 30                    # 价差滚动窗口
OPEN_THRESHOLD = 1.5           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.3          # 平仓阈值
LOT_RB = 1                     # 螺纹钢手数
LOT_HC = 1                    # 热卷手数

# ============ 价差计算 ============
def calc_spread(hc_price, rb_price):
    """计算热卷-螺纹钢价差"""
    return hc_price - rb_price

def calc_zscore(spread_series, window=30):
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
    
    print("启动：热卷-螺纹钢价差套利策略")
    print(f"监控：{HC_SYMBOL} vs {RB_SYMBOL}")
    
    rb_klines = api.get_kline_serial(RB_SYMBOL, KLINE_DURATION, data_length=80)
    hc_klines = api.get_kline_serial(HC_SYMBOL, KLINE_DURATION, data_length=80)
    
    position = 0  # 1: 多HC空RB, -1: 空HC多RB
    
    while True:
        api.wait_update()
        
        if api.is_changing(rb_klines) or api.is_changing(hc_klines):
            if len(rb_klines) < WINDOW + 10 or len(hc_klines) < WINDOW + 10:
                continue
            
            rb_closes = rb_klines['close'].values
            hc_closes = hc_klines['close'].values
            
            # 计算价差序列
            spreads = [calc_spread(hc_closes[i], rb_closes[i]) for i in range(len(hc_closes))]
            
            # 计算Z-score
            zscore = calc_zscore(spreads, WINDOW)
            
            print(f"价差: {spreads[-1]:.2f}, Z-Score: {zscore:.2f}, 持仓: {position}")
            
            # 开仓信号
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    # 价差过高，预期回归，做空价差：空HC，多RB
                    position = -1
                    print(f"开仓：空HC多RB，价差={spreads[-1]:.2f}")
                elif zscore < -OPEN_THRESHOLD:
                    # 价差过低，预期回归，做多价差：多HC，空RB
                    position = 1
                    print(f"开仓：多HC空RB，价差={spreads[-1]:.2f}")
            
            # 平仓信号
            elif position != 0:
                if abs(zscore) < CLOSE_THRESHOLD:
                    print(f"平仓：Z-score回归到{abs(zscore):.2f}")
                    position = 0

if __name__ == "__main__":
    main()
