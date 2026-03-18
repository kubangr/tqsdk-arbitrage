#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略28 - 截面动量轮转套利策略（Cross-Sectional Momentum Rotation Arbitrage）
==============================================================================

原理：
    传统动量策略做多历史最强、做空历史最弱。但动量有"动量崩溃"风险，
    即最强品种反转时亏损巨大。本策略在此基础上加入"动量加速度"维度，
    做多"动量在增强"的品种，做空"动量在减弱"的品种，实现动量轮转。

    因子设计：
    - 一阶动量（return_20）：20日收益率
    - 动量加速度（mom_accel）：20日动量相对40日前的变化率

    当某品种加速度为正时，说明动量正在增强，做多；
    当某品种加速度为负时，说明动量正在减弱，做空。
    品种数量 ≥ 5 时效果更好。

参数：
    - 回看周期：20根日K（动量）+ 40根日K（加速度基准）
    - 换仓周期：10根日K
    - 品种：黑色系5品种

适用行情：板块内品种走势分化、动量风格轮转明显时
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
MOM_PERIOD = 20                # 动量回看周期
ACCEL_PERIOD = 40              # 加速度基准回看周期
REBALANCE_BARS = 10            # 换仓周期
LOT = 1                        # 每条腿手数
# ==================================


def calc_return(kl, period):
    """计算区间收益率"""
    if len(kl) < period + 1:
        return np.nan
    return (kl["close"].iloc[-1] - kl["close"].iloc[-period]) / kl["close"].iloc[-period]


def calc_acceleration(kl, short_period, long_period):
    """
    计算动量加速度：短期动量 - 长期动量
    > 0：动量正在增强；< 0：动量正在减弱
    """
    if len(kl) < long_period + 1:
        return np.nan
    mom_short = calc_return(kl, short_period)
    mom_long = (kl["close"].iloc[-1] - kl["close"].iloc[-long_period]) / kl["close"].iloc[-long_period]
    return mom_short - mom_long


def normalize_cross_sectional(values_dict):
    """截面标准化：Z-score归一化"""
    vals = [v for v in values_dict.values() if v is not None and not np.isnan(v)]
    if len(vals) < 2:
        return {}
    mean = np.mean(vals)
    std = np.std(vals)
    if std == 0:
        return {k: 0.0 for k in values_dict}
    return {k: (v - mean) / std if v is not None and not np.isnan(v) else 0.0 for k, v in values_dict.items()}


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    klines = {sym: api.get_kline_serial(sym, KLINE_DUR, data_length=ACCEL_PERIOD + 5)
              for sym in SYMBOLS}

    bar_count = 0
    long_sym = None
    short_sym = None

    print("[策略启动] 截面动量轮转套利 | 品种: 黑色系5品种 | 换仓周期: 10根日K")

    try:
        while True:
            api.wait_update()

            updated = any(
                api.is_changing(klines[sym].iloc[-1], "datetime")
                for sym in SYMBOLS
            )
            if not updated:
                continue

            bar_count += 1
            if bar_count % REBALANCE_BARS != 0:
                continue

            # ---- 计算动量加速度 ----
            accel_scores = {}
            mom_scores = {}
            for sym in SYMBOLS:
                kl = klines[sym]
                accel = calc_acceleration(kl, MOM_PERIOD, ACCEL_PERIOD)
                mom = calc_return(kl, MOM_PERIOD)
                accel_scores[sym] = accel
                mom_scores[sym] = mom

            if any(v is None or np.isnan(v) for v in accel_scores.values()):
                continue

            # ---- 截面标准化 ----
            accel_norm = normalize_cross_sectional(accel_scores)
            mom_norm = normalize_cross_sectional(mom_scores)

            # ---- 综合得分：动量加速度为主（60%），动量强度为辅（40%） ----
            composite = {}
            for sym in SYMBOLS:
                score = 0.6 * accel_norm.get(sym, 0) + 0.4 * mom_norm.get(sym, 0)
                composite[sym] = score

            ranked = sorted(composite.items(), key=lambda x: x[1], reverse=True)
            new_long = ranked[0][0]
            new_short = ranked[-1][0]

            print(f"[动量轮转] 动量排名: {[(s, f'accel={accel_scores[s]:.2%}', f'mom={mom_scores[s]:.2%}') for s, _ in ranked]}")
            print(f"  综合得分: {[(s, f'{v:.3f}') for s, v in ranked]}")
            print(f"  动量增强(做多): {new_long} | 动量减弱(做空): {new_short}")

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
                    print(f"  平空: {new_short}")

            api.wait_update()

            # ---- 开新仓 ----
            if not new_long == long_sym:
                pos = api.get_position(new_long)
                if pos.pos_long == 0:
                    api.insert_order(new_long, direction="BUY", offset="OPEN", volume=LOT)
                    print(f"  开多: {new_long}")
            if not new_short == short_sym:
                pos = api.get_position(new_short)
                if pos.pos_short == 0:
                    api.insert_order(new_short, direction="SELL", offset="OPEN", volume=LOT)
                    print(f"  开空: {new_short}")

            long_sym = new_long
            short_sym = new_short

            time.sleep(0.1)

    finally:
        api.close()


if __name__ == "__main__":
    main()
