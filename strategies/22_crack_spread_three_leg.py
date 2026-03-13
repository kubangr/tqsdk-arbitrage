"""
策略名称：焦化利润三腿套利策略（焦煤→焦炭→螺纹钢）
策略类型：加工利润三腿套利（Crack Spread）
品种：DCE.jm（焦煤）+ DCE.j（焦炭）+ SHFE.rb（螺纹钢）
描述：
    焦化链利润 = 1.3 × 焦炭价格 - 1.6 × 焦煤价格（近似1.6吨焦煤炼1.3吨焦炭）
    卷钢利润  = 螺纹钢价格 - 0.55 × 铁矿石价格 - 0.25 × 焦炭价格（近似）
    综合三腿利润 = 螺纹钢 - 0.35×焦煤 - 0.30×焦炭
    当三腿合成利润高于历史均值+2σ时做空利润（卖rb买jm买j）；
    低于均值-2σ时做多利润（买rb卖jm卖j）。
    使用100根小时K线的统计量动态更新阈值。
"""

from tqsdk import TqApi, TqAuth, TqSim
import numpy as np

# ===== 参数 =====
SYM_RB = "SHFE.rb2501"   # 螺纹钢
SYM_JM = "DCE.jm2501"    # 焦煤
SYM_J  = "DCE.j2501"     # 焦炭

# 三腿权重：合成利润 = rb - 0.35*jm - 0.30*j
W_RB  =  1.0
W_JM  = -0.35
W_J   = -0.30

LOOKBACK   = 100      # 统计窗口（小时K）
ENTRY_STD  = 2.0      # 开仓阈值（标准差倍数）
EXIT_STD   = 0.5      # 平仓阈值
VOL_RB     = 2        # 螺纹钢手数
VOL_JM     = 1        # 焦煤手数
VOL_J      = 1        # 焦炭手数

api = TqApi(TqSim(), auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

kl_rb = api.get_kline_serial(SYM_RB, 3600, data_length=LOOKBACK + 10)
kl_jm = api.get_kline_serial(SYM_JM, 3600, data_length=LOOKBACK + 10)
kl_j  = api.get_kline_serial(SYM_J,  3600, data_length=LOOKBACK + 10)

pos_rb = api.get_position(SYM_RB)
pos_jm = api.get_position(SYM_JM)
pos_j  = api.get_position(SYM_J)

current_side = 0   # 1=持有多利润 -1=持有空利润 0=空仓

def compute_spread(kl_rb, kl_jm, kl_j, n):
    return (W_RB  * kl_rb["close"].iloc[-n:].values
          + W_JM  * kl_jm["close"].iloc[-n:].values
          + W_J   * kl_j["close"].iloc[-n:].values)

def all_flat():
    return (pos_rb.pos_long == 0 and pos_rb.pos_short == 0 and
            pos_jm.pos_long == 0 and pos_jm.pos_short == 0 and
            pos_j.pos_long  == 0 and pos_j.pos_short  == 0)

try:
    while True:
        api.wait_update()

        if not api.is_changing(kl_rb.iloc[-1], "datetime"):
            continue

        spread_series = compute_spread(kl_rb, kl_jm, kl_j, LOOKBACK)
        mu    = float(np.mean(spread_series))
        sigma = float(np.std(spread_series))
        current_spread = spread_series[-1]

        zscore = (current_spread - mu) / (sigma + 1e-8)

        print(f"[三腿套利] 利润={current_spread:.1f}  均值={mu:.1f}  σ={sigma:.1f}  Z={zscore:.2f}  仓位={current_side}")

        # ---- 平仓逻辑 ----
        if current_side == 1 and zscore > -EXIT_STD:
            # 做多利润时利润回升到均值附近，平仓
            api.insert_order(SYM_RB, direction="SELL", offset="CLOSE", volume=VOL_RB)
            api.insert_order(SYM_JM, direction="BUY",  offset="CLOSE", volume=VOL_JM)
            api.insert_order(SYM_J,  direction="BUY",  offset="CLOSE", volume=VOL_J)
            current_side = 0
            print("  → 平仓（多利润）")
        elif current_side == -1 and zscore < EXIT_STD:
            api.insert_order(SYM_RB, direction="BUY",  offset="CLOSE", volume=VOL_RB)
            api.insert_order(SYM_JM, direction="SELL", offset="CLOSE", volume=VOL_JM)
            api.insert_order(SYM_J,  direction="SELL", offset="CLOSE", volume=VOL_J)
            current_side = 0
            print("  → 平仓（空利润）")

        # ---- 开仓逻辑 ----
        if current_side == 0:
            if zscore < -ENTRY_STD:
                # 利润偏低 → 做多利润：买rb 卖jm 卖j
                api.insert_order(SYM_RB, direction="BUY",  offset="OPEN", volume=VOL_RB)
                api.insert_order(SYM_JM, direction="SELL", offset="OPEN", volume=VOL_JM)
                api.insert_order(SYM_J,  direction="SELL", offset="OPEN", volume=VOL_J)
                current_side = 1
                print(f"  → 开多利润  Z={zscore:.2f}")
            elif zscore > ENTRY_STD:
                # 利润偏高 → 做空利润：卖rb 买jm 买j
                api.insert_order(SYM_RB, direction="SELL", offset="OPEN", volume=VOL_RB)
                api.insert_order(SYM_JM, direction="BUY",  offset="OPEN", volume=VOL_JM)
                api.insert_order(SYM_J,  direction="BUY",  offset="OPEN", volume=VOL_J)
                current_side = -1
                print(f"  → 开空利润  Z={zscore:.2f}")

finally:
    api.close()
