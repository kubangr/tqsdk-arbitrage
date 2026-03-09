#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略13 - 跨品种套利：螺纹钢与铁矿石价差策略
原理：
    螺纹钢（RB）与铁矿石（I）存在产业链上下游关系。
    当两者价差偏离历史均值时，进行均值回归交易。
    价差 = 螺纹钢价格 - 铁矿石价格 * 系数

参数：
    - 螺纹钢合约：SHFE.rb2505
    - 铁矿石合约：DCE.i2505
    - K线周期：1小时
    - 价差窗口：60根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：0.3倍标准差

作者：kubangr / tqsdk-arbitrage
日期：2026-03-09
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np

# ============ 参数配置 ============
RB_SYMBOL = "SHFE.rb2505"     # 螺纹钢合约
I_SYMBOL = "DCE.i2505"        # 铁矿石合约
KLINE_DURATION = 60 * 60       # K线周期：1小时
WINDOW = 60                    # 价差滚动窗口
OPEN_THRESHOLD = 1.5           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.3          # 平仓阈值
LOT_RB = 1                     # 螺纹钢手数
LOT_I = 3                      # 铁矿石手数（考虑价格比例）
RATIO = 0.15                   # 铁矿石价格转螺纹钢价格系数

# ============ 价差计算 ============
def calc_spread(rb_price, i_price):
    """计算螺纹钢-铁矿石价差"""
    return rb_price - i_price * RATIO

def calc_zscore(spread_series):
    """计算价差的 Z-Score"""
    if len(spread_series) < WINDOW:
        return 0.0
    recent = spread_series[-WINDOW:]
    mean = np.mean(recent)
    std = np.std(recent)
    if std == 0:
        return 0.0
    return (spread_series[-1] std

# ========= - mean) /=== 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"), sim=TqSim())
    
    print("启动：螺纹钢-铁矿石价差套利策略")
    print(f"监控：{RB_SYMBOL} vs {I_SYMBOL}")
    
    rb_klines = api.get_kline_serial(RB_SYMBOL, KLINE_DURATION, data_length=100)
    i_klines = api.get_kline_serial(I_SYMBOL, KLINE_DURATION, data_length=100)
    
    position = 0  # 1: 多RB空I, -1: 空RB多I
    
    while True:
        api.wait_update()
        
        if api.is_changing(rb_klines) or api.is_changing(i_klines):
            if len(rb_klines) < WINDOW + 10 or len(i_klines) < WINDOW + 10:
                continue
            
            rb_closes = rb_klines['close'].values
            i_closes = i_klines['close'].values
            
            # 计算价差序列
            spreads = [calc_spread(rb_closes[i], i_closes[i]) for i in range(len(rb_closes))]
            
            # 计算Z-score
            zscore = calc_zscore(spreads)
            
            print(f"价差: {spreads[-1]:.2f}, Z-Score: {zscore:.2f}, 持仓: {position}")
            
            # 开仓信号
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    # 价差过高，预期回归，做空价差：空RB，多I
                    position = -1
                    print(f"开仓：空RB多I，价差={spreads[-1]:.2f}")
                elif zscore < -OPEN_THRESHOLD:
                    # 价差过低，预期回归，做多价差：多RB，空I
                    position = 1
                    print(f"开仓：多RB空I，价差={spreads[-1]:.2f}")
            
            # 平仓信号
            elif position != 0:
                if abs(zscore) < CLOSE_THRESHOLD:
                    print(f"平仓：Z-score回归，盈亏计算")
                    position = 0

if __name__ == "__main__":
    main()
