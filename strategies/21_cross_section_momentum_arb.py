"""
策略名称：截面动量套利策略（黑色系多品种）
策略类型：截面动量 + 多品种套利
品种：SHFE.rb / SHFE.hc / DCE.i / DCE.jm / DCE.j
描述：
    对黑色系5个品种计算20日截面动量得分（涨幅排名），
    做多排名前1位品种、做空排名末1位品种，形成多空截面套利组合。
    每20根日K线重新排名换仓，持仓期间不做择时，纯截面配对。
"""

from tqsdk import TqApi, TqAuth, TqSim
from tqsdk.tafunc import time_to_datetime
import numpy as np
import time

# ===== 参数 =====
SYMBOLS = [
    "SHFE.rb2501", "SHFE.hc2501", "DCE.i2501", "DCE.jm2501", "DCE.j2501"
]
LOOKBACK = 20          # 动量回看周期（日K根数）
REBALANCE_BARS = 20    # 换仓周期（日K根数）
VOLUME = 1             # 每条腿手数

api = TqApi(TqSim(), auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

# 获取各品种日K线
klines = {sym: api.get_kline_serial(sym, 86400, data_length=LOOKBACK + 5) for sym in SYMBOLS}

bar_count = 0
long_sym = None
short_sym = None

try:
    while True:
        api.wait_update()

        # 检查是否有K线更新（任意品种）
        updated = any(api.is_changing(klines[sym].iloc[-1], "datetime") for sym in SYMBOLS)
        if not updated:
            continue

        bar_count += 1
        if bar_count % REBALANCE_BARS != 0:
            continue

        # ---- 截面动量得分：20日收益率 ----
        scores = {}
        for sym in SYMBOLS:
            kl = klines[sym]
            if len(kl) < LOOKBACK:
                continue
            ret = (kl["close"].iloc[-1] - kl["close"].iloc[-LOOKBACK]) / kl["close"].iloc[-LOOKBACK]
            scores[sym] = ret

        if len(scores) < len(SYMBOLS):
            continue

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        new_long = ranked[0][0]   # 动量最强
        new_short = ranked[-1][0] # 动量最弱

        print(f"[截面动量] 动量排名: {[(s, f'{v:.2%}') for s, v in ranked]}")
        print(f"  做多: {new_long}  做空: {new_short}")

        # ---- 平旧仓 ----
        if long_sym and long_sym != new_long:
            pos = api.get_position(long_sym)
            if pos.pos_long > 0:
                api.insert_order(long_sym, direction="SELL", offset="CLOSE", volume=pos.pos_long)
                print(f"  平多: {long_sym}")
        if short_sym and short_sym != new_short:
            pos = api.get_position(short_sym)
            if pos.pos_short > 0:
                api.insert_order(short_sym, direction="BUY", offset="CLOSE", volume=pos.pos_short)
                print(f"  平空: {short_sym}")

        api.wait_update()

        # ---- 开新仓 ----
        pos_long = api.get_position(new_long)
        if pos_long.pos_long == 0:
            api.insert_order(new_long, direction="BUY", offset="OPEN", volume=VOLUME)
            print(f"  开多: {new_long}")

        pos_short = api.get_position(new_short)
        if pos_short.pos_short == 0:
            api.insert_order(new_short, direction="SELL", offset="OPEN", volume=VOLUME)
            print(f"  开空: {new_short}")

        long_sym = new_long
        short_sym = new_short

        time.sleep(0.1)

finally:
    api.close()
