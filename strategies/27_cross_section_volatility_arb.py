#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略27 - 截面波动率套利策略（Cross-Sectional Volatility Arbitrage）
=====================================================================

原理：
    利用同板块品种间波动率的均值回归特性。波动率有强烈的聚集效应和均值回归特性：
    当某品种波动率处于历史高位（相对自身或相对板块均值）时，
    波动率大概率会回归，适合做空波动率（卖出跨式/宽跨式或做空波动率因子）；
    当波动率处于低位时，适合做多波动率。

    本策略采用截面波动率套利思路：
    对板块内多个品种计算20日实现波动率，做多低波、做空高波，
    等待波动率收敛后平仓。

参数：
    - 波动率计算周期：20根日K
    - 开仓阈值：0.8倍标准差
    - 平仓阈值：0.2倍标准差
    - 止损：2.0倍标准差
    - 品种：黑色系（rb/hc/i/jm/j）

适用行情：板块内品种波动率分化明显时
作者：kubangr / tqsdk-arbitrage
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np
import time

# ============ 参数配置 ============
SYMBOLS = [
    "SHFE.rb2501", "SHFE.hc2501", "DCE.i2501", "DCE.jm2501", "DCE.j2501"
]
KLINE_DUR = 86400              # 日K
VOL_PERIOD = 20                # 波动率计算周期
Z_OPEN = 0.8                   # 开仓Z-score阈值
Z_CLOSE = 0.2                  # 平仓Z-score阈值
Z_STOP = 2.0                   # 止损Z-score阈值
LOT = 1                        # 每条腿手数
# ==================================


def realized_volatility(close_series, period):
    """计算实现波动率：日收益率标准差 * sqrt(252) 年化"""
    if len(close_series) < period:
        return np.nan
    rets = close_series.pct_change().dropna()
    if len(rets) < period:
        return np.nan
    rv = rets[-period:].std() * np.sqrt(252)
    return rv


def calc_spread_zscore(vols):
    """计算波动率价差的Z-score（做多低波-做空高波）"""
    vals = list(vols.values())
    mean = np.mean(vals)
    std = np.std(vals)
    if std == 0:
        return None
    return {sym: (mean - v) / std for sym, v in vols.items()}


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    klines = {sym: api.get_kline_serial(sym, KLINE_DUR, data_length=VOL_PERIOD + 5)
              for sym in SYMBOLS}

    positions = {}    # {sym: "long"/"short"/None}
    entry_spread = {}  # 开仓时记录各腿的波动率差

    print("[策略启动] 截面波动率套利 | 品种: 黑色系5品种")

    try:
        while True:
            api.wait_update()

            updated = any(
                api.is_changing(klines[sym].iloc[-1], "datetime")
                for sym in SYMBOLS
            )
            if not updated:
                continue

            # ---- 计算各品种实现波动率 ----
            vols = {}
            for sym in SYMBOLS:
                kl = klines[sym]
                v = realized_volatility(kl["close"], VOL_PERIOD)
                vols[sym] = v

            if any(v is None or np.isnan(v) for v in vols.values()):
                continue

            # ---- Z-score化（正值=低波，负值=高波） ----
            z_scores = calc_spread_zscore(vols)
            if z_scores is None:
                continue

            ranked = sorted(z_scores.items(), key=lambda x: x[1], reverse=True)
            top_sym = ranked[0][0]   # 波动率最低 → 做多
            bot_sym = ranked[-1][0]  # 波动率最高 → 做空

            top_z = ranked[0][1]
            bot_z = ranked[-1][1]

            print(f"[波动率排名] {[(s, f'{vols[s]:.2%}', f'z={z_scores[s]:.2f}') for s, _ in ranked]}")
            print(f"  低波(做多): {top_sym} | 高波(做空): {bot_sym}")

            # ---- 开仓逻辑 ----
            # 当前无仓位且信号触发
            if not positions or all(v is None for v in positions.values()):
                if top_z > Z_OPEN and bot_z < -Z_OPEN:
                    # 记录初始spread差
                    entry_diff = vols[top_sym] - vols[bot_sym]

                    # 做多低波，做空高波
                    pos_top = api.get_position(top_sym)
                    pos_bot = api.get_position(bot_sym)

                    if pos_top.pos_long == 0:
                        api.insert_order(top_sym, direction="BUY", offset="OPEN", volume=LOT)
                        print(f"  开多低波: {top_sym} (波动率={vols[top_sym]:.4f})")
                        positions[top_sym] = "long"

                    if pos_bot.pos_short == 0:
                        api.insert_order(bot_sym, direction="SELL", offset="OPEN", volume=LOT)
                        print(f"  开空高波: {bot_sym} (波动率={vols[bot_sym]:.4f})")
                        positions[bot_sym] = "short"

                    entry_spread = {"long": top_sym, "short": bot_sym, "entry_diff": entry_diff}
                    print(f"  开仓波动率差: {entry_diff:.4f} | Z-score阈值: {Z_OPEN}")

            # ---- 平仓逻辑（均值回归） ----
            elif entry_spread:
                cur_diff = vols[entry_spread["long"]] - vols[entry_spread["short"]]
                cur_z = z_scores[entry_spread["long"]]  # 与做多低波的Z-score一致

                print(f"  当前spread: {cur_diff:.4f} | Z-score: {cur_z:.2f} | 初始spread: {entry_spread['entry_diff']:.4f}")

                # 止损：spread继续扩大
                if abs(cur_z) > Z_STOP:
                    print(f">>> 止损 | Z-score {cur_z:.2f} 超过阈值 {Z_STOP}")
                    for sym, side in list(positions.items()):
                        if side == "long":
                            p = api.get_position(sym)
                            if p.pos_long > 0:
                                api.insert_order(sym, direction="SELL", offset="CLOSE", volume=p.pos_long)
                        elif side == "short":
                            p = api.get_position(sym)
                            if p.pos_short > 0:
                                api.insert_order(sym, direction="BUY", offset="CLOSE", volume=p.pos_short)
                    positions = {}
                    entry_spread = {}
                    continue

                # 平仓：Z-score回归到阈值以内
                if abs(cur_z) < Z_CLOSE:
                    print(f">>> 平仓 | Z-score {cur_z:.2f} 回归到阈值 {Z_CLOSE}")
                    for sym, side in list(positions.items()):
                        if side == "long":
                            p = api.get_position(sym)
                            if p.pos_long > 0:
                                api.insert_order(sym, direction="SELL", offset="CLOSE", volume=p.pos_long)
                        elif side == "short":
                            p = api.get_position(sym)
                            if p.pos_short > 0:
                                api.insert_order(sym, direction="BUY", offset="CLOSE", volume=p.pos_short)
                    positions = {}
                    entry_spread = {}

            time.sleep(0.1)

    finally:
        api.close()


if __name__ == "__main__":
    main()
