#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略10 - 铜铝跨品种套利策略
原理：
    铜和铝同属有色金属，具有较强的相关性。
    当两者价比偏离历史均值时，进行价比回归交易。

参数：
    - 铜合约：SHFE.cu2505
    - 铝合约：SHFE.al2505
    - 周期：1小时
    - 价比窗口：40根K线
    - 开仓阈值：1.8倍标准差
    - 平仓阈值：回归到0.4倍标准差
    - 手数配比：1:3（铝3手对铜1手）

适用行情：铜铝价比偏离均值时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
CU_SYMBOL = "SHFE.cu2505"       # 铜合约
AL_SYMBOL = "SHFE.al2505"       # 铝合约
KLINE_DURATION = 60 * 60        # 1小时K线
WINDOW = 40                     # 价比滚动窗口
OPEN_THRESHOLD = 1.8            # 开仓阈值
CLOSE_THRESHOLD = 0.4          # 平仓阈值
LOT_CU = 1                      # 铜手数
LOT_AL = 3                      # 铝手数

# ============ 价比计算 ============
def calc_ratio(cu_price, al_price):
    """计算铜铝价比"""
    if al_price <= 0:
        return 0.0
    return cu_price / al_price * LOT_AL / LOT_CU

def calc_zscore(ratio_series):
    """计算价比的 Z-Score"""
    mean = np.mean(ratio_series)
    std = np.std(ratio_series)
    if std == 0:
        return 0.0
    return (ratio_series[-1] - mean) / std

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：铜铝跨品种套利策略")
    
    cu_quote = api.get_quote(CU_SYMBOL)
    al_quote = api.get_quote(AL_SYMBOL)
    
    cu_klines = api.get_kline_serial(CU_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    al_klines = api.get_kline_serial(AL_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    ratio_history = []
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(cu_quote) or api.is_changing(al_quote):
            cu_price = cu_quote.last_price
            al_price = al_quote.last_price
            
            if cu_price <= 0 or al_price <= 0:
                continue
            
            ratio = calc_ratio(cu_price, al_price)
            ratio_history.append(ratio)
            
            if len(ratio_history) < WINDOW:
                continue
            
            recent_ratio = ratio_history[-WINDOW:]
            zscore = calc_zscore(recent_ratio)
            
            print(f"铜: {cu_price}, 铝: {al_price}, 价比: {ratio:.4f}, Z-Score: {zscore:.2f}")
            
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空铜铝价比, Z-Score: {zscore:.2f}")
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多铜铝价比, Z-Score: {zscore:.2f}")
                    position = 1
                    
            elif position == 1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价比回归, Z-Score: {zscore:.2f}")
                position = 0
            elif position == -1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价比回归, Z-Score: {zscore:.2f}")
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
