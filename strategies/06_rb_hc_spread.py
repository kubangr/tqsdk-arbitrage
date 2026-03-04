#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略06 - 跨品种套利：螺纹钢与热卷价差策略
原理：
    螺纹钢（RB）和热卷（HC）走势高度相关，但价差会周期性波动。
    当两者价差偏离历史均值时，进行价差回归交易。

参数：
    - RB合约：SHFE.rb2505
    - HC合约：SHFE.hc2505
    - 价差窗口：80根K线
    - 开仓阈值：1.8倍标准差
    - 平仓阈值：回归到0.4倍标准差以内

适用行情：RB-HC价差偏离均值时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
RB_SYMBOL = "SHFE.rb2505"      # 螺纹钢合约
HC_SYMBOL = "SHFE.hc2505"       # 热卷合约
KLINE_DURATION = 60 * 60         # K线周期：1小时
WINDOW = 80                     # 价差滚动窗口
OPEN_THRESHOLD = 1.8            # 开仓阈值
CLOSE_THRESHOLD = 0.4          # 平仓阈值
LOT_RB = 1                      # 螺纹钢手数
LOT_HC = 1                      # 热卷手数

# ============ 价差计算 ============
def calc_spread(rb_price, hc_price):
    """计算品种间价差"""
    return rb_price - hc_price

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
    
    print("启动：螺纹钢-热卷跨品种套利策略")
    
    rb_quote = api.get_quote(RB_SYMBOL)
    hc_quote = api.get_quote(HC_SYMBOL)
    
    rb_klines = api.get_kline_serial(RB_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    hc_klines = api.get_kline_serial(HC_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    spread_history = []
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(rb_quote) or api.is_changing(hc_quote):
            rb_price = rb_quote.last_price
            hc_price = hc_quote.last_price
            
            if rb_price <= 0 or hc_price <= 0:
                continue
                
            spread = calc_spread(rb_price, hc_price)
            spread_history.append(spread)
            
            if len(spread_history) < WINDOW:
                continue
                
            recent_spread = spread_history[-WINDOW:]
            zscore = calc_zscore(recent_spread)
            
            print(f"RB: {rb_price}, HC: {hc_price}, 价差: {spread:.2f}, Z-Score: {zscore:.2f}")
            
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空RB-HC价差, Z-Score: {zscore:.2f}")
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多RB-HC价差, Z-Score: {zscore:.2f}")
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
