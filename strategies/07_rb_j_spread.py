#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略07 - 跨品种套利：螺纹钢与焦炭价差策略
原理：
    螺纹钢（RB）和焦炭（J）属于上下游产业链，走势高度相关。
    当两者价差偏离历史均值时，进行价差回归交易。

参数：
    - RB合约：SHFE.rb2505
    - J合约：DCE.j2505
    - 价差窗口：60根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：回归到0.3倍标准差以内
    - 手数配比：1:1

适用行情：RB-J价差偏离均值时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
RB_SYMBOL = "SHFE.rb2505"      # 螺纹钢合约
J_SYMBOL = "DCE.j2505"         # 焦炭合约
KLINE_DURATION = 60 * 60       # K线周期：1小时
WINDOW = 60                    # 价差滚动窗口
OPEN_THRESHOLD = 1.5           # 开仓阈值
CLOSE_THRESHOLD = 0.3          # 平仓阈值
LOT_RB = 1                     # 螺纹钢手数
LOT_J = 1                      # 焦炭手数

# ============ 价差计算 ============
def calc_spread(rb_price, j_price):
    """计算品种间价差"""
    return rb_price - j_price * 10  # 焦炭乘数

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
    
    print("启动：螺纹钢-焦炭跨品种套利策略")
    
    rb_quote = api.get_quote(RB_SYMBOL)
    j_quote = api.get_quote(J_SYMBOL)
    
    rb_klines = api.get_kline_serial(RB_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    j_klines = api.get_kline_serial(J_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    spread_history = []
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(rb_quote) or api.is_changing(j_quote):
            rb_price = rb_quote.last_price
            j_price = j_quote.last_price
            
            if rb_price <= 0 or j_price <= 0:
                continue
                
            spread = calc_spread(rb_price, j_price)
            spread_history.append(spread)
            
            if len(spread_history) < WINDOW:
                continue
                
            recent_spread = spread_history[-WINDOW:]
            zscore = calc_zscore(recent_spread)
            
            print(f"RB: {rb_price}, J: {j_price}, 价差: {spread:.2f}, Z-Score: {zscore:.2f}")
            
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空RB-J价差, Z-Score: {zscore:.2f}")
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多RB-J价差, Z-Score: {zscore:.2f}")
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
