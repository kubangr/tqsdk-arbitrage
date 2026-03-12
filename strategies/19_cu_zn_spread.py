#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
有色金属跨品种套利：铜锌套利策略
================================

策略思路：
---------
铜和锌都属于有色金属，价格具有较强的相关性。
由于两者供需关系和价格周期存在差异，当价差偏离正常范围时可以进行套利。
本策略基于铜锌比价进行均值回归交易。

原理：
-----
- 铜( Cu )主要用于电线、电子产品等高端制造业
- 锌( Zn )主要用于镀锌、合金等
- 两者价格比值在历史区间内波动，当突破阈值时存在回归机会

作者: TqSdk Arbitrage
"""

from tqsdk import TqApi, TqAuth, TqSim
from tqsdk.ta import MA, ATR
import pandas as pd
import numpy as np
from datetime import datetime


class CuZnSpreadStrategy:
    """铜锌跨品种套利策略"""
    
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
        self.symbol_cu = self.params.get('symbol_cu', 'SHFE.cu2405')  # 沪铜
        self.symbol_zn = self.params.get('symbol_zn', 'SHFE.zn2405')  # 沪锌
        
        # 配比：铜1手 : 锌1手（根据合约乘数调整）
        self.cu_volume = 1
        self.zn_volume = self.params.get('zn_volume', 1)
        
        # 策略参数
        self.lookback = self.params.get('lookback', 30)        # 回看周期
        self.entry_threshold = self.params.get('entry_threshold', 0.15)  # 入场阈值
        self.exit_threshold = self.params.get('exit_threshold', 0.03)   # 平仓阈值
        
        # 持仓状态
        self.position = None  # 'cu_long_zn_short' or 'cu_short_zn_long' or None
        
    def get_spread_data(self, n=100):
        """
        获取价差数据
        
        Returns:
            pd.DataFrame: 包含价格和比值的数据
        """
        try:
            # 获取K线数据
            kline_cu = self.api.get_kline_serial(self.symbol_cu, n)
            kline_zn = self.api.get_kline_serial(self.symbol_zn, n)
            
            if kline_cu is None or kline_zn is None:
                return None
                
            df_cu = pd.DataFrame(kline_cu)
            df_zn = pd.DataFrame(kline_zn)
            
            # 同步数据
            min_len = min(len(df_cu), len(df_zn))
            df_cu = df_cu.iloc[-min_len:]
            df_zn = df_zn.iloc[-min_len:]
            
            # 计算铜锌比值
            ratio = df_cu['close'] / df_zn['close']
            
            # 计算均值和标准差
            ratio_ma = ratio.rolling(self.lookback).mean()
            ratio_std = ratio.rolling(self.lookback).std()
            
            # 计算Z-Score
            zscore = (ratio - ratio_ma) / ratio_std
            
            result = pd.DataFrame({
                'cu_close': df_cu['close'].values,
                'zn_close': df_zn['close'].values,
                'ratio': ratio.values,
                'ratio_ma': ratio_ma.values,
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
            direction: 'cu_long_zn_short' 或 'cu_short_zn_long'
        """
        if direction == 'cu_long_zn_short':
            # 做多铜，做空锌
            print(f"[开仓] 做多{self.symbol_cu}, 做空{self.symbol_zn}")
            self.api.insert_order(
                symbol=self.symbol_cu, 
                direction="BUY", 
                offset="OPEN", 
                volume=self.cu_volume
            )
            self.api.insert_order(
                symbol=self.symbol_zn, 
                direction="SELL", 
                offset="OPEN", 
                volume=self.zn_volume
            )
        else:
            # 做空铜，做多锌
            print(f"[开仓] 做空{self.symbol_cu}, 做多{self.symbol_zn}")
            self.api.insert_order(
                symbol=self.symbol_cu, 
                direction="SELL", 
                offset="OPEN", 
                volume=self.cu_volume
            )
            self.api.insert_order(
                symbol=self.symbol_zn, 
                direction="BUY", 
                offset="OPEN", 
                volume=self.zn_volume
            )
            
        self.position = direction
    
    def close_position(self):
        """平仓"""
        if self.position is None:
            return
            
        if self.position == 'cu_long_zn_short':
            # 平多铜，空锌
            print(f"[平仓] 平多{self.symbol_cu}, 平空{self.symbol_zn}")
            self.api.insert_order(
                symbol=self.symbol_cu, 
                direction="SELL", 
                offset="CLOSE", 
                volume=self.cu_volume
            )
            self.api.insert_order(
                symbol=self.symbol_zn, 
                direction="BUY", 
                offset="CLOSE", 
                volume=self.zn_volume
            )
        else:
            # 平空铜，多锌
            print(f"[平仓] 平空{self.symbol_cu}, 平多{self.symbol_zn}")
            self.api.insert_order(
                symbol=self.symbol_cu, 
                direction="BUY", 
                offset="CLOSE", 
                volume=self.cu_volume
            )
            self.api.insert_order(
                symbol=self.symbol_zn, 
                direction="SELL", 
                offset="CLOSE", 
                volume=self.zn_volume
            )
            
        self.position = None
    
    def check_signal(self):
        """检查交易信号"""
        data = self.get_spread_data()
        if data is None or len(data) < self.lookback + 5:
            return
            
        latest = data.iloc[-1]
        zscore = latest['zscore']
        ratio = latest['ratio']
        
        print(f"\n[{datetime.now()}]")
        print(f"  铜价: {latest['cu_close']:.2f}, 锌价: {latest['zn_close']:.2f}")
        print(f"  铜锌比: {ratio:.4f}, Z-Score: {zscore:.2f}")
        
        if self.position is None:
            # 无持仓，检查入场信号
            if zscore > self.entry_threshold:
                # 比值偏高，做空铜，做多锌
                self.open_position('cu_short_zn_long')
            elif zscore < -self.entry_threshold:
                # 比值偏低，做多铜，做空锌
                self.open_position('cu_long_zn_short')
        else:
            # 有持仓，检查出场信号
            if abs(zscore) < self.exit_threshold:
                print("  -> 价差回归，平仓")
                self.close_position()
            # 止损：Z-Score向不利方向移动超过2
            elif (self.position == 'cu_long_zn_short' and zscore < -self.entry_threshold - 1) or \
                 (self.position == 'cu_short_zn_long' and zscore > self.entry_threshold + 1):
                print("  -> 止损")
                self.close_position()
    
    def run(self):
        """主循环"""
        print("=" * 60)
        print("铜锌跨品种套利策略启动")
        print(f"交易品种: {self.symbol_cu} vs {self.symbol_zn}")
        print(f"配比: 铜{self.cu_volume}手 : 锌{self.zn_volume}手")
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
        'symbol_cu': 'SHFE.cu2405',
        'symbol_zn': 'SHFE.zn2405',
        'zn_volume': 1,
        'lookback': 30,
        'entry_threshold': 0.15,
        'exit_threshold': 0.03
    }
    
    # 启动策略
    strategy = CuZnSpreadStrategy(api, params)
    strategy.run()


if __name__ == "__main__":
    main()
