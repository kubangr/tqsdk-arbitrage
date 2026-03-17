#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
螺纹钢产业链三角套利策略 (RB Industrial Chain Triangle Arbitrage)
=====================================================================

策略思路：
---------
本策略基于黑色系产业链的三角套利关系：
  铁矿石 → 焦炭 → 螺纹钢
  
产业链利润公式：
  利润 = 螺纹钢价格 - (铁矿石价格 × 1.6 + 焦炭价格 × 0.5 + 加工费)

当产业链利润偏离历史均值时，进行三个品种的联合套利。

交易逻辑：
  1. 监控铁矿石、焦炭、螺纹钢三个品种
  2. 计算产业链利润（简化：RB - 1.6*I - 0.5*J）
  3. 当利润偏离20日均值超过1.2倍标准差时入场
  4. 使用协整系数优化配平比例

品种配置（使用主力合约）：
  - 铁矿石：DCE.i2501
  - 焦炭：DCE.j2501
  - 螺纹钢：SHFE.rb2501

配比优化：
  - 基于历史回归系数动态调整
  - 螺纹钢:铁矿石 ≈ 1:1.5~1.8
  - 螺纹钢:焦炭 ≈ 1:0.4~0.6

风险控制：
---------
- 最大持仓：每边不超过3组
- 止损：产业链利润偏离超过2倍标准差
- 止盈：回归至0.3倍标准差

作者: TqSdk Strategies
更新: 2026-03-17
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TriangleArbitrageStrategy:
    """螺纹钢产业链三角套利策略"""

    # 产业链品种
    CHAIN = {
        'rb': 'SHFE.rb2501',   # 螺纹钢
        'i': 'DCE.i2501',     # 铁矿石
        'j': 'DCE.j2501',     # 焦炭
    }

    # 产业链系数（经验值，可优化）
    COEFF_RB = 1.0
    COEFF_I = 1.6     # 1.6吨铁矿石产1吨螺纹钢
    COEFF_J = 0.5     # 0.5吨焦炭产1吨螺纹钢
    
    LOOKBACK = 20             # 回看天数
    ENTRY_STD = 1.2           # 入场标准差
    EXIT_STD = 0.3            # 止盈标准差
    STOP_STD = 2.0            # 止损标准差
    MAX_HOLD_DAYS = 5         # 最大持仓天数
    
    def __init__(self, api):
        self.api = api
        self.klines = {}
        self.position = None  # {'entry_profit': x, 'entry_time': t, 'direction': 1/-1}
        
    def get_kline(self, symbol, days):
        """获取K线数据"""
        if symbol not in self.klines:
            self.klines[symbol] = self.api.get_kline_serial(
                symbol, 86400, data_length=days + 10
            )
        return self.klines[symbol]
    
    def calculate_chain_profit(self):
        """计算产业链利润"""
        kline_rb = self.get_kline(self.CHAIN['rb'], self.LOOKBACK)
        kline_i = self.get_kline(self.CHAIN['i'], self.LOOKBACK)
        kline_j = self.get_kline(self.CHAIN['j'], self.LOOKBACK)
        
        if kline_rb is None or kline_i is None or kline_j is None:
            return None
        
        if len(kline_rb) < self.LOOKBACK or len(kline_i) < self.LOOKBACK or len(kline_j) < self.LOOKBACK:
            return None
        
        rb = kline_rb['close'].values[-self.LOOKBACK:]
        i = kline_i['close'].values[-self.LOOKBACK:]
        j = kline_j['close'].values[-self.LOOKBACK:]
        
        # 计算产业链利润
        profit = rb - (self.COEFF_I * i + self.COEFF_J * j)
        
        mean = np.mean(profit)
        std = np.std(profit)
        current_profit = profit[-1]
        z_score = (current_profit - mean) / std if std > 0 else 0
        
        return {
            'mean': mean,
            'std': std,
            'current': current_profit,
            'z_score': z_score,
            'rb': rb[-1],
            'i': i[-1],
            'j': j[-1]
        }
    
    def calculate_optimal_ratio(self):
        """计算最优配比（基于回归）"""
        kline_rb = self.get_kline(self.CHAIN['rb'], 60)
        kline_i = self.get_kline(self.CHAIN['i'], 60)
        kline_j = self.get_kline(self.CHAIN['j'], 60)
        
        if kline_rb is None or kline_i is None or kline_j is None:
            return self.COEFF_I, self.COEFF_J
        
        if len(kline_rb) < 30:
            return self.COEFF_I, self.COEFF_J
        
        # 简单线性回归
        rb = kline_rb['close'].values[-30:]
        i = kline_i['close'].values[-30:]
        j = kline_j['close'].values[-30:]
        
        # RB = a*I + b*J + c
        X = np.column_stack([i, j])
        try:
            coeffs, residuals, rank, s = np.linalg.lstsq(X, rb, rcond=None)
            return coeffs[0], coeffs[1]
        except:
            return self.COEFF_I, self.COEFF_J
    
    def open_position(self, direction, entry_profit):
        """开仓"""
        # 获取当前最优配比
        coeff_i, coeff_j = self.calculate_optimal_ratio()
        
        if direction == 1:
            # 产业链利润将上升：做多螺纹钢，做空铁矿石+焦炭
            # 做多RB
            self.api.insert_order(
                symbol=self.CHAIN['rb'],
                direction="buy",
                offset="open",
                volume=1
            )
            # 做空铁矿石
            self.api.insert_order(
                symbol=self.CHAIN['i'],
                direction="sell",
                offset="open",
                volume=int(coeff_i * 1.5)  # 取整
            )
            # 做空焦炭
            self.api.insert_order(
                symbol=self.CHAIN['j'],
                direction="sell",
                offset="open",
                volume=int(coeff_j * 1.5)
            )
        else:
            # 产业链利润将下降：做空螺纹钢，做多铁矿石+焦炭
            self.api.insert_order(
                symbol=self.CHAIN['rb'],
                direction="sell",
                offset="open",
                volume=1
            )
            self.api.insert_order(
                symbol=self.CHAIN['i'],
                direction="buy",
                offset="open",
                volume=int(coeff_i * 1.5)
            )
            self.api.insert_order(
                symbol=self.CHAIN['j'],
                direction="buy",
                offset="open",
                volume=int(coeff_j * 1.5)
            )
        
        self.position = {
            'entry_profit': entry_profit,
            'entry_time': datetime.now(),
            'direction': direction,
            'coeff_i': coeff_i,
            'coeff_j': coeff_j
        }
        
        print(f"[开仓] 产业链{'利润上升' if direction > 0 else '利润下降'}, 入场利润:{entry_profit:.2f}")
    
    def close_position(self):
        """平仓"""
        if self.position is None:
            return
        
        direction = self.position['direction']
        coeff_i = self.position['coeff_i']
        coeff_j = self.position['coeff_j']
        
        if direction == 1:
            # 平多仓
            self.api.insert_order(
                symbol=self.CHAIN['rb'],
                direction="sell",
                offset="close",
                volume=1
            )
            self.api.insert_order(
                symbol=self.CHAIN['i'],
                direction="buy",
                offset="close",
                volume=int(coeff_i * 1.5)
            )
            self.api.insert_order(
                symbol=self.CHAIN['j'],
                direction="buy",
                offset="close",
                volume=int(coeff_j * 1.5)
            )
        else:
            # 平空仓
            self.api.insert_order(
                symbol=self.CHAIN['rb'],
                direction="buy",
                offset="close",
                volume=1
            )
            self.api.insert_order(
                symbol=self.CHAIN['i'],
                direction="sell",
                offset="close",
                volume=int(coeff_i * 1.5)
            )
            self.api.insert_order(
                symbol=self.CHAIN['j'],
                direction="sell",
                offset="close",
                volume=int(coeff_j * 1.5)
            )
        
        print(f"[平仓] 产业链套利")
        self.position = None
    
    def check_position(self):
        """检查持仓"""
        if self.position is None:
            return
        
        stats = self.calculate_chain_profit()
        if stats is None:
            return
        
        z_score = stats['z_score']
        direction = self.position['direction']
        
        should_close = False
        reason = ""
        
        # 止盈
        if direction == 1 and z_score <= self.EXIT_STD:
            should_close = True
            reason = "止盈"
        elif direction == -1 and z_score >= -self.EXIT_STD:
            should_close = True
            reason = "止盈"
        
        # 止损
        if direction == 1 and z_score > self.STOP_STD:
            should_close = True
            reason = "止损"
        elif direction == -1 and z_score < -self.STOP_STD:
            should_close = True
            reason = "止损"
        
        # 超时
        if (datetime.now() - self.position['entry_time']).days > self.MAX_HOLD_DAYS:
            should_close = True
            reason = "超时"
        
        if should_close:
            self.close_position()
            print(f"[{reason}] 产业链套利")
    
    def scan_opportunity(self):
        """扫描交易机会"""
        if self.position is not None:
            return
        
        stats = self.calculate_chain_profit()
        if stats is None:
            return
        
        z_score = stats['z_score']
        
        # 利润高于均值：做空产业链利润（方向-1）
        if z_score > self.ENTRY_STD:
            self.open_position(-1, stats['current'])
            print(f"[信号] 产业链利润Z-Score={z_score:.2f} > {self.ENTRY_STD}, 预期利润下降")
        
        # 利润低于均值：做多产业链利润（方向+1）
        elif z_score < -self.ENTRY_STD:
            self.open_position(1, stats['current'])
            print(f"[信号] 产业链利润Z-Score={z_score:.2f} < -{self.ENTRY_STD}, 预期利润上升")
    
    def run(self):
        """运行策略"""
        print(f"启动螺纹钢产业链三角套利策略...")
        print(f"品种: 螺纹钢({self.CHAIN['rb']}), 铁矿石({self.CHAIN['i']}), 焦炭({self.CHAIN['j']})")
        
        while True:
            self.api.wait_update()
            
            now = datetime.now()
            
            # 检查持仓
            self.check_position()
            
            # 每天扫描一次
            if now.hour == 15 and now.minute < 5:
                self.scan_opportunity()
            
            if now.hour == 21 and now.minute < 5:
                self.scan_opportunity()


def main():
    """主函数"""
    api = TqSim()
    # api = TqApi(auth=TqAuth("快期账户", "账户密码"))
    
    strategy = TriangleArbitrageStrategy(api)
    
    try:
        strategy.run()
    except KeyboardInterrupt:
        print("策略停止")
    finally:
        api.close()


if __name__ == "__main__":
    main()
