#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
农产品跨品种套利：豆粕菜粕价差策略
==================================

策略思路：
---------
豆粕(DCE.m)和菜粕(CZCE.rm)都是饲料蛋白原料，存在较强的替代关系。
当两者价差偏离历史均值时，存在回归交易机会。
本策略基于价差的均值回归特性进行套利。

原理：
-----
- 豆粕：大豆压榨产物，蛋白含量高
- 菜粕：菜籽压榨产物，有一定的芥子酸影响
- 正常情况下，豆粕价格高于菜粕，但价差存在周期性波动

注意：本策略为跨交易所套利，需要注意合约乘数和波动性差异

作者: TqSdk Arbitrage
"""

from tqsdk import TqApi, TqAuth, TqSim
from tqsdk.ta import MA, STD
import pandas as pd
import numpy as np
from datetime import datetime


class MealSpreadStrategy:
    """豆粕菜粕价差套利策略"""
    
    def __init__(self, api, params=None):
        """
        初始化策略
        
        Args:
            api: TqApi实例
            params: 策略参数
        """
        self.api = api
        self.params = params or {}
        
        # 交易品种
        self.symbol_m = self.params.get('symbol_m', 'DCE.m2405')   # 豆粕
        self.symbol_rm = self.params.get('symbol_rm', 'CZCE.rm2405')  # 菜粕
        
        # 配比：根据合约乘数和价格调整
        # 豆粕合约乘数10吨/手，菜粕合约乘数10吨/手
        self.m_volume = 1
        self.rm_volume = self.params.get('rm_volume', 1)
        
        # 策略参数
        self.lookback = self.params.get('lookback', 40)        # 回看周期
        self.entry_threshold = self.params.get('entry_threshold', 0.12)  # 入场阈值(价差百分比)
        self.exit_threshold = self.params.get('exit_threshold', 0.03)    # 平仓阈值
        
        # 持仓状态
        self.position = None  # 'm_long_rm_short' or 'm_short_rm_long' or None
        
    def get_spread_data(self, n=100):
        """
        获取价差数据
        
        Returns:
            pd.DataFrame: 包含价格和价差的数据
        """
        try:
            # 获取K线数据
            kline_m = self.api.get_kline_serial(self.symbol_m, n)
            kline_rm = self.api.get_kline_serial(self.symbol_rm, n)
            
            if kline_m is None or kline_rm is None:
                return None
                
            df_m = pd.DataFrame(kline_m)
            df_rm = pd.DataFrame(kline_rm)
            
            # 同步数据
            min_len = min(len(df_m), len(df_rm))
            df_m = df_m.iloc[-min_len:]
            df_rm = df_rm.iloc[-min_len:]
            
            # 计算价差（豆粕 - 菜粕）
            spread = df_m['close'] - df_rm['close']
            
            # 计算价差百分比（相对于菜粕价格）
            spread_pct = spread / df_rm['close']
            
            # 计算均值和标准差
            spread_ma = spread.rolling(self.lookback).mean()
            spread_std = spread.rolling(self.lookback).std()
            
            # 计算Z-Score
            zscore = (spread - spread_ma) / spread_std
            
            result = pd.DataFrame({
                'm_close': df_m['close'].values,
                'rm_close': df_rm['close'].values,
                'spread': spread.values,
                'spread_pct': spread_pct.values,
                'spread_ma': spread_ma.values,
                'zscore': zscore.values
            })
            
            return result
            
        except Exception as e:
            print(f"获取数据失败: {e}")
            return None
    
    def open_position(self, direction):
        """
        开仓
        
        Args:
            direction: 'm_long_rm_short' 或 'm_short_rm_long'
        """
        if direction == 'm_long_rm_short':
            # 做多豆粕，做空菜粕
            print(f"[开仓] 做多{self.symbol_m}, 做空{self.symbol_rm}")
            self.api.insert_order(
                symbol=self.symbol_m, 
                direction="BUY", 
                offset="OPEN", 
                volume=self.m_volume
            )
            self.api.insert_order(
                symbol=self.symbol_rm, 
                direction="SELL", 
                offset="OPEN", 
                volume=self.rm_volume
            )
        else:
            # 做空豆粕，做多菜粕
            print(f"[开仓] 做空{self.symbol_m}, 做多{self.symbol_rm}")
            self.api.insert_order(
                symbol=self.symbol_m, 
                direction="SELL", 
                offset="OPEN", 
                volume=self.m_volume
            )
            self.api.insert_order(
                symbol=self.symbol_rm, 
                direction="BUY", 
                offset="OPEN", 
                volume=self.rm_volume
            )
            
        self.position = direction
    
    def close_position(self):
        """平仓"""
        if self.position is None:
            return
            
        if self.position == 'm_long_rm_short':
            # 平多豆粕，空菜粕
            print(f"[平仓] 平多{self.symbol_m}, 平空{self.symbol_rm}")
            self.api.insert_order(
                symbol=self.symbol_m, 
                direction="SELL", 
                offset="CLOSE", 
                volume=self.m_volume
            )
            self.api.insert_order(
                symbol=self.symbol_rm, 
                direction="BUY", 
                offset="CLOSE", 
                volume=self.rm_volume
            )
        else:
            # 平空豆粕，多菜粕
            print(f"[平仓] 平空{self.symbol_m}, 平多{self.symbol_rm}")
            self.api.insert_order(
                symbol=self.symbol_m, 
                direction="BUY", 
                offset="CLOSE", 
                volume=self.m_volume
            )
            self.api.insert_order(
                symbol=self.symbol_rm, 
                direction="SELL", 
                offset="CLOSE", 
                volume=self.rm_volume
            )
            
        self.position = None
    
    def check_signal(self):
        """检查交易信号"""
        data = self.get_spread_data()
        if data is None or len(data) < self.lookback + 5:
            return
            
        latest = data.iloc[-1]
        zscore = latest['zscore']
        spread = latest['spread']
        spread_pct = latest['spread_pct']
        
        print(f"\n[{datetime.now()}]")
        print(f"  豆粕: {latest['m_close']:.2f}, 菜粕: {latest['rm_close']:.2f}")
        print(f"  价差: {spread:.2f} ({spread_pct*100:.2f}%), Z-Score: {zscore:.2f}")
        
        if self.position is None:
            # 无持仓，检查入场信号
            if zscore > self.entry_threshold:
                # 价差偏高，做空豆粕，做多菜粕
                self.open_position('m_short_rm_long')
            elif zscore < -self.entry_threshold:
                # 价差偏低，做多豆粕，做空菜粕
                self.open_position('m_long_rm_short')
        else:
            # 有持仓，检查出场信号
            if abs(zscore) < self.exit_threshold:
                print("  -> 价差回归，平仓")
                self.close_position()
            # 止损
            elif (self.position == 'm_long_rm_short' and zscore < -self.entry_threshold - 1) or \
                 (self.position == 'm_short_rm_long' and zscore > self.entry_threshold + 1):
                print("  -> 止损")
                self.close_position()
    
    def run(self):
        """主循环"""
        print("=" * 60)
        print("豆粕菜粕跨品种套利策略启动")
        print(f"交易品种: {self.symbol_m} vs {self.symbol_rm}")
        print(f"配比: 豆粕{self.m_volume}手 : 菜粕{self.rm_volume}手")
        print(f"入场阈值: ±{self.entry_threshold}, 平仓阈值: ±{self.exit_threshold}")
        print("=" * 60)
        
        while True:
            try:
                # 等待行情更新
                self.api.wait_update()
                
                # 每日开盘后检查信号
                trading_time = self.api.get_trading_time()
                if self.api.is_changing(trading_time, "date"):
                    self.check_signal()
                    
            except KeyboardInterrupt:
                print("\n策略停止")
                break
            except Exception as e:
                print(f"运行错误: {e}")


def main():
    """主函数"""
    # 使用模拟账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 策略参数
    params = {
        'symbol_m': 'DCE.m2405',
        'symbol_rm': 'CZCE.rm2405',
        'rm_volume': 1,
        'lookback': 40,
        'entry_threshold': 0.12,
        'exit_threshold': 0.03
    }
    
    # 启动策略
    strategy = MealSpreadStrategy(api, params)
    strategy.run()


if __name__ == "__main__":
    main()
