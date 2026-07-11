"""
策略模块 - strategy.py
=====================
基于backtrader框架实现的双均线交叉策略。

策略逻辑：
- 买入信号：快线(MA20)上穿慢线(MA60)，且当前无持仓
- 卖出信号：快线(MA20)下穿慢线(MA60)，且当前有持仓
- 以信号次日开盘价成交，每次全仓买入（留5%现金防手续费）
- 考虑T+1限制，使用cheat-on-open机制模拟次日开盘成交

第二阶段扩展点：
- 可增加更多策略类（如MACD、RSI、布林带等）
- 可增加多策略组合与权重分配
- 可增加风控模块（止损、止盈、最大持仓数等）
"""

import backtrader as bt
import logging
from config import MA_FAST, MA_SLOW, POSITION_SIZE, setup_logging

logger = setup_logging("Strategy")


class DualMAStrategy(bt.Strategy):
    """
    双均线交叉策略

    参数：
        ma_fast: 快线周期（默认20日）
        ma_slow: 慢线周期（默认60日）
        position_size: 仓位比例（默认0.95，即95%仓位）

    第二阶段扩展点：
    - 可继承此类，增加止损/止盈逻辑
    - 可增加动态仓位管理（根据波动率调整仓位）
    - 可增加多时间框架分析
    """

    params = (
        ("ma_fast", MA_FAST),
        ("ma_slow", MA_SLOW),
        ("position_size", POSITION_SIZE),
    )

    def __init__(self):
        """
        初始化策略指标和跟踪变量。
        使用backtrader的Indicator系统计算均线，自动处理NaN。
        """
        # 计算两条简单移动平均线
        self.ma_fast = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_fast
        )
        self.ma_slow = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_slow
        )

        # 交叉信号：1表示金叉(快线上穿慢线)，-1表示死叉(快线下穿慢线)
        self.crossover = bt.indicators.CrossOver(self.ma_fast, self.ma_slow)

        # 记录交易明细
        self.order = None          # 当前未成交的订单
        self.trade_count = 0       # 总交易次数（一买一卖算一次）

        # 交易记录列表（第二阶段可序列化存入数据库）
        self.trade_records = []

        logger.info(
            f"策略初始化完成：MA({self.params.ma_fast}) vs MA({self.params.ma_slow})"
        )

    def log(self, txt: str, dt=None):
        """策略日志输出"""
        dt = dt or self.datas[0].datetime.date(0)
        logger.info(f"{dt.isoformat()} {txt}")

    def notify_order(self, order: bt.Order):
        """
        订单状态变化回调。

        在此记录每笔订单的成交信息，包括价格、数量、手续费等。
        第二阶段扩展点：可将订单信息推送到消息队列或写入交易日志数据库。
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，等待成交
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"买入 {order.data._name} | "
                    f"价格: {order.executed.price:.2f} | "
                    f"数量: {order.executed.size:.0f} | "
                    f"手续费: {order.executed.comm:.2f}"
                )
                # 记录买入交易
                self.trade_records.append({
                    "date": self.datas[0].datetime.date(0),
                    "code": order.data._name,
                    "direction": "BUY",
                    "price": order.executed.price,
                    "size": order.executed.size,
                    "value": order.executed.value,
                    "commission": order.executed.comm,
                })
            else:
                self.log(
                    f"卖出 {order.data._name} | "
                    f"价格: {order.executed.price:.2f} | "
                    f"数量: {order.executed.size:.0f} | "
                    f"手续费: {order.executed.comm:.2f}"
                )
                self.trade_count += 1

                # 记录卖出交易（包含盈亏）
                self.trade_records.append({
                    "date": self.datas[0].datetime.date(0),
                    "code": order.data._name,
                    "direction": "SELL",
                    "price": order.executed.price,
                    "size": order.executed.size,
                    "value": order.executed.value,
                    "commission": order.executed.comm,
                })

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单异常：{order.getstatusname()}")

        # 重置订单状态
        self.order = None

    def notify_trade(self, trade: bt.Trade):
        """
        交易完成回调（一买一卖完成后触发）。

        在此记录每笔完整交易的盈亏情况。
        第二阶段扩展点：可计算每笔交易的持仓天数、最大浮盈浮亏等细节。
        """
        if trade.isclosed:
            self.log(
                f"交易完成 | 毛利: {trade.pnl:.2f} | "
                f"净利: {trade.pnlcomm:.2f} | "
                f"持仓天数: {trade.barlen}"
            )

    def next(self):
        """
        每个bar（交易日）调用的核心逻辑。

        由于设置了cheat-on-open，self.data.open[0]是下个bar的开盘价，
        self.data.close[0]是当前bar的收盘价。
        这样可以用当前bar收盘计算出的信号，在下个bar开盘时成交，模拟T+1。
        """
        # 如果有未成交订单，等待
        if self.order:
            return

        # 检查交叉信号
        if self.crossover > 0:
            # 金叉：快线上穿慢线 → 买入信号
            if not self.position:
                # 全仓买入（留部分现金）
                self.order = self.order_target_percent(
                    target=self.params.position_size
                )
                self.log(
                    f"🔵 金叉信号 | "
                    f"MA{self.params.ma_fast}: {self.ma_fast[0]:.2f} | "
                    f"MA{self.params.ma_slow}: {self.ma_slow[0]:.2f}"
                )

        elif self.crossover < 0:
            # 死叉：快线下穿慢线 → 卖出信号
            if self.position:
                # 清仓
                self.order = self.close()
                self.log(
                    f"🔴 死叉信号 | "
                    f"MA{self.params.ma_fast}: {self.ma_fast[0]:.2f} | "
                    f"MA{self.params.ma_slow}: {self.ma_slow[0]:.2f}"
                )
