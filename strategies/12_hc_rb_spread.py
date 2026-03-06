#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略12 - 跨品种套利：热卷与螺纹钢价差策略
原理：
    热卷（HC）与螺纹钢（RB）同属钢材品种，价格高度相关。
    当两者价差偏离历史均值时，进行均值回归交易。
    价差 = 热卷价格 - 螺纹钢价格

参数：
    - 热卷合约：SHFE.hc2505
    - 螺纹钢合约：SHFE.rb2505
    - 价差窗口：50根K线
    - 开仓阈值：1.3倍标准差
    - 平仓阈值：0.25倍标准差

作者：kubangr / tqsdk-arbitrage
日期：2026-03-06
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np

# ============ 参数配置 ============
HC_SYMBOL = "SHFE.hc2505"     # 热卷合约
RB_SYMBOL = "SHFE.rb2505"     # 螺纹钢合约
KLINE_DURATION = 60 * 60      # K线周期：1小时
WINDOW = 50                    # 价差滚动窗口
OPEN_THRESHOLD = 1.3           # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.25         # 平仓阈值
LOT_SIZE = 1                   # 每次交易手数

# ============ 价差计算 ============
def calc_spread(hc_price, rb_price):
    """计算热卷-螺纹钢价差"""
    return hc_price - rb_price

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
    hc_kline = api.get_kline_serial(HC_SYMBOL, KLINE_DURATION)
    rb_kline = api.get_kline_serial(RB_SYMBOL, KLINE_DURATION)
    
    # 持仓状态
    position = 0  # 1: 多HC空RB, -1: 空HC多RB, 0: 空仓
    
    print(f"启动热卷-螺纹钢跨品种套利策略")
    print(f"热卷:{HC_SYMBOL} 螺纹:{RB_SYMBOL}")
    
    spread_history = []
    
    while True:
        api.wait_update()
        
        if len(hc_kline) < WINDOW + 1 or len(rb_kline) < WINDOW + 1:
            continue
        
        hc_price = hc_kline["close"][-1]
        rb_price = rb_kline["close"][-1]
        spread = calc_spread(hc_price, rb_price)
        spread_history.append(spread)
        
        if len(spread_history) > 200:
            spread_history = spread_history[-200:]
        
        zscore = calc_zscore(spread_history)
        
        # 交易逻辑
        if position == 0:
            if zscore > OPEN_THRESHOLD:
                # 价差过高，预期收窄，做空价差
                print(f"[开空价差] 热卷:{hc_price:.0f} 螺纹:{rb_price:.0f} 价差:{spread:.0f} Z:{zscore:.2f}")
                position = -1
            elif zscore < -OPEN_THRESHOLD:
                # 价差过低，预期扩大，做多价差
                print(f"[开多价差] 热卷:{hc_price:.0f} 螺纹:{rb_price:.0f} 价差:{spread:.0f} Z:{zscore:.2f}")
                position = 1
        else:
            if abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差:{spread:.0f} Z:{zscore:.2f}")
                position = 0

if __name__ == "__main__":
    main()
