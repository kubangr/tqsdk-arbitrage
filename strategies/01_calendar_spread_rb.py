#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略01 - 螺纹钢跨期套利策略（Calendar Spread）
原理：
    利用螺纹钢近月合约（rb2405）与远月合约（rb2409）之间的价差均值回归特性。
    当价差偏离历史均值超过一定阈值时建立套利头寸，等待价差回归后平仓。

参数：
    - 价差窗口：60根K线（1小时）
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：0.3倍标准差
    - 止损：3.0倍标准差

适用行情：近远月价差均值回归时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth, TqBacktest
from tqsdk.tafunc import time_to_datetime
import numpy as np
import datetime

# ============ 参数配置 ============
NEAR_SYMBOL = "SHFE.rb2405"      # 近月合约
FAR_SYMBOL  = "SHFE.rb2409"      # 远月合约
KLINE_DURATION = 60 * 60         # K线周期：1小时
WINDOW = 60                       # 价差滚动窗口
OPEN_THRESHOLD = 1.5              # 开仓阈值（倍标准差）
CLOSE_THRESHOLD = 0.3             # 平仓阈值
STOP_THRESHOLD = 3.0              # 止损阈值
LOT = 1                           # 每手数量

def calc_zscore(spread_series):
    """计算价差的 Z-Score"""
    mean = np.mean(spread_series)
    std = np.std(spread_series)
    if std == 0:
        return 0.0
    return (spread_series[-1] - mean) / std

def main():
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    near_quote = api.get_quote(NEAR_SYMBOL)
    far_quote  = api.get_quote(FAR_SYMBOL)

    near_klines = api.get_kline_serial(NEAR_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    far_klines  = api.get_kline_serial(FAR_SYMBOL,  KLINE_DURATION, data_length=WINDOW + 1)

    near_pos = api.get_position(NEAR_SYMBOL)
    far_pos  = api.get_position(FAR_SYMBOL)

    position = 0  # 1=做空价差(买近卖远), -1=做多价差(卖近买远), 0=空仓

    print(f"策略启动：{NEAR_SYMBOL} vs {FAR_SYMBOL} 跨期套利")

    while True:
        api.wait_update()

        if not api.is_changing(near_klines.iloc[-1], "close") and \
           not api.is_changing(far_klines.iloc[-1], "close"):
            continue

        if len(near_klines) < WINDOW or len(far_klines) < WINDOW:
            continue

        # 计算价差序列
        near_close = near_klines["close"].values[-WINDOW:]
        far_close  = far_klines["close"].values[-WINDOW:]
        spread = near_close - far_close
        zscore = calc_zscore(spread)

        current_spread = near_quote.last_price - far_quote.last_price
        print(f"当前价差: {current_spread:.2f} | Z-Score: {zscore:.3f} | 持仓: {position}")

        # ---- 平仓逻辑 ----
        if position == 1 and abs(zscore) <= CLOSE_THRESHOLD:
            # 价差收窄，平仓
            api.insert_order(NEAR_SYMBOL, "SELL", "CLOSE", LOT, near_quote.bid_price1)
            api.insert_order(FAR_SYMBOL,  "BUY",  "CLOSE", LOT, far_quote.ask_price1)
            position = 0
            print(f"✅ 平仓：价差回归 zscore={zscore:.3f}")

        elif position == -1 and abs(zscore) <= CLOSE_THRESHOLD:
            api.insert_order(NEAR_SYMBOL, "BUY",  "CLOSE", LOT, near_quote.ask_price1)
            api.insert_order(FAR_SYMBOL,  "SELL", "CLOSE", LOT, far_quote.bid_price1)
            position = 0
            print(f"✅ 平仓：价差回归 zscore={zscore:.3f}")

        # ---- 止损逻辑 ----
        elif position == 1 and zscore > STOP_THRESHOLD:
            api.insert_order(NEAR_SYMBOL, "SELL", "CLOSE", LOT, near_quote.bid_price1)
            api.insert_order(FAR_SYMBOL,  "BUY",  "CLOSE", LOT, far_quote.ask_price1)
            position = 0
            print(f"🛑 止损出场 zscore={zscore:.3f}")

        elif position == -1 and zscore < -STOP_THRESHOLD:
            api.insert_order(NEAR_SYMBOL, "BUY",  "CLOSE", LOT, near_quote.ask_price1)
            api.insert_order(FAR_SYMBOL,  "SELL", "CLOSE", LOT, far_quote.bid_price1)
            position = 0
            print(f"🛑 止损出场 zscore={zscore:.3f}")

        # ---- 开仓逻辑 ----
        elif position == 0 and zscore > OPEN_THRESHOLD:
            # 价差偏高：卖近买远（做空价差）
            api.insert_order(NEAR_SYMBOL, "SELL", "OPEN", LOT, near_quote.bid_price1)
            api.insert_order(FAR_SYMBOL,  "BUY",  "OPEN", LOT, far_quote.ask_price1)
            position = 1
            print(f"📈 开仓做空价差 zscore={zscore:.3f}")

        elif position == 0 and zscore < -OPEN_THRESHOLD:
            # 价差偏低：买近卖远（做多价差）
            api.insert_order(NEAR_SYMBOL, "BUY",  "OPEN", LOT, near_quote.ask_price1)
            api.insert_order(FAR_SYMBOL,  "SELL", "OPEN", LOT, far_quote.bid_price1)
            position = -1
            print(f"📉 开仓做多价差 zscore={zscore:.3f}")

    api.close()

if __name__ == "__main__":
    main()
