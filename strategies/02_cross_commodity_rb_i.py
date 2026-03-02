#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略02 - 铁矿石+螺纹钢跨品种套利（Cross-Commodity Spread）
原理：
    铁矿石（i）是螺纹钢（rb）的主要原料，两者价格长期协整。
    利用钢厂利润 = 螺纹钢价格 - 1.6×铁矿石价格 - 固定成本 的均值回归特性。
    当"钢厂利润"大幅偏离历史均值时，认为基本面失衡，做均值回归。

参数：
    - 利润窗口：120根K线（30分钟）
    - 比价系数：1.6（生产1吨螺纹钢需约1.6吨铁矿石）
    - 固定成本：1200元（焦炭+其他费用估算）
    - 开仓阈值：1.5σ
    - 平仓阈值：0.5σ

适用行情：黑色系品种基本面失衡时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
RB_SYMBOL  = "SHFE.rb2405"      # 螺纹钢主力
I_SYMBOL   = "DCE.i2405"         # 铁矿石主力
KLINE_DURATION = 30 * 60         # 30分钟K线
WINDOW = 120                      # 滚动窗口
RATIO = 1.6                       # 铁矿石吨耗比
FIXED_COST = 1200                 # 固定成本估算（元/吨）
OPEN_THRESHOLD = 1.5
CLOSE_THRESHOLD = 0.5
STOP_THRESHOLD = 3.0
LOT = 1

def calc_profit_zscore(rb_close, i_close):
    """计算钢厂利润的 Z-Score"""
    profit = rb_close - RATIO * i_close - FIXED_COST
    mean = np.mean(profit)
    std = np.std(profit)
    if std == 0:
        return 0.0, profit[-1]
    return (profit[-1] - mean) / std, profit[-1]

def main():
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    rb_quote = api.get_quote(RB_SYMBOL)
    i_quote  = api.get_quote(I_SYMBOL)

    rb_klines = api.get_kline_serial(RB_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    i_klines  = api.get_kline_serial(I_SYMBOL,  KLINE_DURATION, data_length=WINDOW + 1)

    position = 0  # 1=利润偏高做空(卖rb买i), -1=利润偏低做多(买rb卖i), 0=空仓

    print(f"策略启动：{RB_SYMBOL} vs {I_SYMBOL} 跨品种套利（钢厂利润回归）")

    while True:
        api.wait_update()

        if not api.is_changing(rb_klines.iloc[-1], "close") and \
           not api.is_changing(i_klines.iloc[-1], "close"):
            continue

        if len(rb_klines) < WINDOW or len(i_klines) < WINDOW:
            continue

        rb_close = rb_klines["close"].values[-WINDOW:]
        i_close  = i_klines["close"].values[-WINDOW:]
        zscore, profit = calc_profit_zscore(rb_close, i_close)

        print(f"钢厂利润: {profit:.0f}元 | Z-Score: {zscore:.3f} | 持仓: {position}")

        # 平仓
        if position != 0 and abs(zscore) <= CLOSE_THRESHOLD:
            if position == 1:
                api.insert_order(RB_SYMBOL, "BUY",  "CLOSE", LOT, rb_quote.ask_price1)
                api.insert_order(I_SYMBOL,  "SELL", "CLOSE", LOT, i_quote.bid_price1)
            else:
                api.insert_order(RB_SYMBOL, "SELL", "CLOSE", LOT, rb_quote.bid_price1)
                api.insert_order(I_SYMBOL,  "BUY",  "CLOSE", LOT, i_quote.ask_price1)
            position = 0
            print(f"✅ 利润回归平仓 zscore={zscore:.3f}")

        # 止损
        elif position == 1 and zscore < -STOP_THRESHOLD:
            api.insert_order(RB_SYMBOL, "BUY",  "CLOSE", LOT, rb_quote.ask_price1)
            api.insert_order(I_SYMBOL,  "SELL", "CLOSE", LOT, i_quote.bid_price1)
            position = 0
            print(f"🛑 止损 zscore={zscore:.3f}")

        elif position == -1 and zscore > STOP_THRESHOLD:
            api.insert_order(RB_SYMBOL, "SELL", "CLOSE", LOT, rb_quote.bid_price1)
            api.insert_order(I_SYMBOL,  "BUY",  "CLOSE", LOT, i_quote.ask_price1)
            position = 0
            print(f"🛑 止损 zscore={zscore:.3f}")

        # 开仓
        elif position == 0 and zscore > OPEN_THRESHOLD:
            # 利润偏高→做空利润：卖rb买i
            api.insert_order(RB_SYMBOL, "SELL", "OPEN", LOT, rb_quote.bid_price1)
            api.insert_order(I_SYMBOL,  "BUY",  "OPEN", LOT, i_quote.ask_price1)
            position = 1
            print(f"📈 利润偏高，做空利润 zscore={zscore:.3f}")

        elif position == 0 and zscore < -OPEN_THRESHOLD:
            # 利润偏低→做多利润：买rb卖i
            api.insert_order(RB_SYMBOL, "BUY",  "OPEN", LOT, rb_quote.ask_price1)
            api.insert_order(I_SYMBOL,  "SELL", "OPEN", LOT, i_quote.bid_price1)
            position = -1
            print(f"📉 利润偏低，做多利润 zscore={zscore:.3f}")

    api.close()

if __name__ == "__main__":
    main()
