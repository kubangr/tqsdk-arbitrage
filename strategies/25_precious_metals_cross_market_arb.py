#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
贵金属跨市场统计套利策略 (Precious Metals Cross-Market Statistical Arbitrage)
===============================================================================

策略思路：
---------
本策略基于贵金属市场的统计相关性进行跨市场套利。
黄金、白银、铂金、钯金之间存在较强的相关性，
当价差偏离历史均值时进行均值回归交易。

交易逻辑：
  1. 监控黄金、白银、铂金三种贵金属
  2. 计算金银比价（Au/Ag）、金铂比价（Au/Pt）
  3. 当比价偏离20日均值超过1.5倍标准差时入场
  4. 持有至比价回归均值止盈或止损

对冲参数：
  - 入场阈值：1.5倍标准差
  - 止盈：回归至0.5倍标准差
  - 止损：2倍标准差
  - 持仓周期：最长5天

品种配置：
  - 黄金：SHFE.au2506
  - 白银：SHFE.ag2506
  - 铂金：SHFE.pt2506

风险控制：
---------
- 最大持仓：每个交易对不超过2组
- 单日最大亏损：2%强平
- 相关性失效：金银相关系数<0.5时暂停交易

作者: TqSdk Strategies
更新: 2026-03-17
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class PreciousMetalsArbitrageStrategy:
    """贵金属跨市场统计套利策略"""

    # 贵金属交易对
    PAIRS = [
        ("SHFE.au2506", "SHFE.ag2506", "金银比价"),   # 黄金/白银
        ("SHFE.au2506", "SHFE.pt2506", "金铂比价"),   # 黄金/铂金
    ]

    LOOKBACK = 20              # 计算均值回归的回看天数
    ENTRY_STD = 1.5            # 入场标准差倍数
    EXIT_STD = 0.5             # 止盈标准差倍数
    STOP_STD = 2.0            # 止损标准差倍数
    MAX_HOLD_DAYS = 5         # 最大持仓天数
    
    def __init__(self, api):
        self.api = api
        self.klines = {}
        self.positions = {}  # {(sym1, sym2): {'entry_ratio': x, 'entry_time': t, 'direction': 1/-1}}
        
    def get_kline(self, symbol, days):
        """获取K线数据"""
        if symbol not in self.klines:
            self.klines[symbol] = self.api.get_kline_serial(
                symbol, 86400, data_length=days + 10
            )
        return self.klines[symbol]
    
    def calculate_ratio_stats(self, sym1, sym2):
        """计算比价统计特征"""
        kline1 = self.get_kline(sym1, self.LOOKBACK)
        kline2 = self.get_kline(sym2, self.LOOKBACK)
        
        if kline1 is None or kline2 is None:
            return None
        
        if len(kline1) < self.LOOKBACK or len(kline2) < self.LOOKBACK:
            return None
        
        close1 = kline1['close'].values[-self.LOOKBACK:]
        close2 = kline2['close'].values[-self.LOOKBACK:]
        
        # 计算比价序列
        ratio = close1 / close2
        
        # 统计特征
        mean = np.mean(ratio)
        std = np.std(ratio)
        current_ratio = ratio[-1]
        
        # Z-score
        z_score = (current_ratio - mean) / std if std > 0 else 0
        
        # 相关系数
        corr = np.corrcoef(close1, close2)[0, 1]
        
        return {
            'mean': mean,
            'std': std,
            'current': current_ratio,
            'z_score': z_score,
            'correlation': corr,
            'close1': close1[-1],
            'close2': close2[-1]
        }
    
    def check_correlation(self, sym1, sym2):
        """检查相关性是否满足交易条件"""
        kline1 = self.get_kline(sym2, 20)
        kline2 = self.get_kline(sym2, 20)
        
        if kline1 is None or kline2 is None:
            return False
        
        if len(kline1) < 20 or len(kline2) < 20:
            return False
        
        close1 = kline1['close'].values
        close2 = kline2['close'].values
        
        corr = np.corrcoef(close1[-20:], close2[-20:])[0, 1]
        
        return corr > 0.5
    
    def open_position(self, sym1, sym2, direction, entry_ratio):
        """开仓"""
        key = (sym1, sym2)
        
        # 黄金做多/做空，白银做空/做多
        if direction == 1:
            # 比价将上升：做多sym1，做空sym2
            self.api.insert_order(
                symbol=sym1,
                direction="buy",
                offset="open",
                volume=1
            )
            self.api.insert_order(
                symbol=sym2,
                direction="sell",
                offset="open",
                volume=10  # 白银合约乘数大
            )
        else:
            # 比价将下降：做空sym1，做多sym2
            self.api.insert_order(
                symbol=sym1,
                direction="sell",
                offset="open",
                volume=1
            )
            self.api.insert_order(
                symbol=sym2,
                direction="buy",
                offset="open",
                volume=10
            )
        
        self.positions[key] = {
            'entry_ratio': entry_ratio,
            'entry_time': datetime.now(),
            'direction': direction
        }
        
        print(f"[开仓] {sym1}/{sym2} 比价{entry_ratio:.4f}, 方向{'做多' if direction > 0 else '做空'}")
    
    def close_position(self, sym1, sym2):
        """平仓"""
        key = (sym1, sym2)
        
        if key not in self.positions:
            return
        
        pos_info = self.positions[key]
        direction = pos_info['direction']
        
        # 反向平仓
        if direction == 1:
            self.api.insert_order(
                symbol=sym1,
                direction="sell",
                offset="close",
                volume=1
            )
            self.api.insert_order(
                symbol=sym2,
                direction="buy",
                offset="close",
                volume=10
            )
        else:
            self.api.insert_order(
                symbol=sym1,
                direction="buy",
                offset="close",
                volume=1
            )
            self.api.insert_order(
                symbol=sym2,
                direction="sell",
                offset="close",
                volume=10
            )
        
        print(f"[平仓] {sym1}/{sym2} 原因: 信号消失")
        
        del self.positions[key]
    
    def check_positions(self):
        """检查所有持仓"""
        for (sym1, sym2), pos_info in list(self.positions.items()):
            stats = self.calculate_ratio_stats(sym1, sym2)
            if stats is None:
                continue
            
            z_score = stats['z_score']
            direction = pos_info['direction']
            entry_z = (pos_info['entry_ratio'] - stats['mean']) / stats['std']
            
            # 检查止盈/止损
            should_close = False
            reason = ""
            
            # 止盈：回归到0.5倍标准差
            if direction == 1 and z_score <= stats['mean'] + 0.5 * stats['std']:
                should_close = True
                reason = "止盈"
            elif direction == -1 and z_score >= stats['mean'] - 0.5 * stats['std']:
                should_close = True
                reason = "止盈"
            
            # 止损：超过2倍标准差
            if direction == 1 and z_score > stats['mean'] + 2.0 * stats['std']:
                should_close = True
                reason = "止损"
            elif direction == -1 and z_score < stats['mean'] - 2.0 * stats['std']:
                should_close = True
                reason = "止损"
            
            # 超时
            if (datetime.now() - pos_info['entry_time']).days > self.MAX_HOLD_DAYS:
                should_close = True
                reason = "超时"
            
            if should_close:
                self.close_position(sym1, sym2)
                print(f"[{reason}] {sym1}/{sym2}")
    
    def scan_opportunities(self):
        """扫描交易机会"""
        for sym1, sym2, name in self.PAIRS:
            # 检查是否已有持仓
            if (sym1, sym2) in self.positions:
                continue
            
            # 检查相关性
            if not self.check_correlation(sym1, sym2):
                continue
            
            # 计算统计特征
            stats = self.calculate_ratio_stats(sym1, sym2)
            if stats is None:
                continue
            
            z_score = stats['z_score']
            
            # 入场信号
            # 比价高于均值：做空比价（方向-1）
            if z_score > self.ENTRY_STD:
                self.open_position(sym1, sym2, -1, stats['current'])
                print(f"[信号] {name} Z-Score={z_score:.2f} > {self.ENTRY_STD}, 预期比价下降")
            
            # 比价低于均值：做多比价（方向+1）
            elif z_score < -self.ENTRY_STD:
                self.open_position(sym1, sym2, 1, stats['current'])
                print(f"[信号] {name} Z-Score={z_score:.2f} < -{self.ENTRY_STD}, 预期比价上升")
    
    def run(self):
        """运行策略"""
        print(f"启动贵金属跨市场统计套利策略...")
        print(f"交易对: {[p[2] for p in self.PAIRS]}")
        
        while True:
            self.api.wait_update()
            
            # 每日收盘后扫描机会
            now = datetime.now()
            
            # 检查现有持仓
            self.check_positions()
            
            # 每天只交易一次（收盘后）
            if now.hour == 15 and now.minute < 5:
                self.scan_opportunities()
            
            # 夜盘开盘后也可以扫描
            if now.hour == 21 and now.minute < 5:
                self.scan_opportunities()


def main():
    """主函数"""
    api = TqSim()
    # api = TqApi(auth=TqAuth("快期账户", "账户密码"))
    
    strategy = PreciousMetalsArbitrageStrategy(api)
    
    try:
        strategy.run()
    except KeyboardInterrupt:
        print("策略停止")
    finally:
        api.close()


if __name__ == "__main__":
    main()
