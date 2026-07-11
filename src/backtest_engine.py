"""
回测引擎模块 - backtest_engine.py
===============================
封装backtrader的cerebro引擎，提供简洁的回测运行接口。
负责：添加数据、配置手续费、添加分析器、运行回测、提取结果。

第二阶段扩展点：
- 可增加多策略组合回测
- 可增加参数优化（Grid Search / 遗传算法）
- 可增加Benchmark对比（如与沪深300指数对比）
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

from config import (
    INITIAL_CASH, COMMISSION_RATE, SLIPPAGE,
    MA_FAST, MA_SLOW, POSITION_SIZE,
    setup_logging
)
from data_manager import DataManager
from strategy import DualMAStrategy

logger = setup_logging("BacktestEngine")


class BacktestEngine:
    """
    回测引擎封装类

    使用示例：
        engine = BacktestEngine(
            initial_cash=1000000,
            commission=0.00025,
            start_date="2020-01-01",
            end_date="2024-12-31"
        )
        engine.add_data_from_manager(data_manager, codes=["000001.XSHE", "600519.XSHG"])
        result = engine.run()
        print(result["summary"])
    """

    def __init__(
        self,
        initial_cash: float = INITIAL_CASH,
        commission: float = COMMISSION_RATE,
        start_date: str = "2020-01-01",
        end_date: Optional[str] = None,
    ):
        """
        初始化回测引擎

        Args:
            initial_cash: 初始资金
            commission: 手续费率（如0.00025表示万2.5）
            start_date: 回测开始日期
            end_date: 回测结束日期，None表示至今
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        self.cerebro = None
        self.results = None
        self.strategy_instance = None
        self.data_feeds = []

        logger.info(
            f"回测引擎初始化 | 初始资金: {initial_cash:,.0f} | "
            f"手续费: {commission:.4%} | 日期: {start_date} ~ {self.end_date}"
        )

    def _create_cerebro(self):
        """创建并配置cerebro引擎"""
        cerebro = bt.Cerebro()

        # 设置初始资金
        cerebro.broker.setcash(self.initial_cash)

        # 设置手续费（买卖双向）
        cerebro.broker.setcommission(commission=self.commission)

        # 设置滑点
        cerebro.broker.set_slippage_perc(perc=SLIPPAGE)

        # 添加分析器
        # 夏普比率（年化，使用无风险利率为0的简化版本）
        cerebro.addanalyzer(
            bt.analyzers.SharpeRatio_A,
            _name="sharpe",
            riskfreerate=0.0,
            annualize=True,
        )

        # 最大回撤
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

        # 收益率分析
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        # 年度收益率
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annual_return")

        # 交易分析
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        # VWR（Value-Weighted Return，资金加权收益率）
        cerebro.addanalyzer(bt.analyzers.VWR, _name="vwr")

        # 设置cheat-on-open：在next()中可使用次日开盘价成交，模拟T+1
        cerebro.broker.set_coc(True)

        logger.info("Cerebro引擎配置完成")
        return cerebro

    def add_data_from_manager(
        self,
        data_manager: DataManager,
        codes: Optional[List[str]] = None,
    ):
        """
        从DataManager加载数据并添加到cerebro

        Args:
            data_manager: DataManager实例
            codes: 股票代码列表，默认全部
        """
        codes = codes or data_manager.get_available_stocks()
        logger.info(f"准备加载 {len(codes)} 只股票的数据...")

        for code in codes:
            df = data_manager.load_data_for_backtrader(
                code, self.start_date, self.end_date
            )
            if df is None or df.empty:
                logger.warning(f"跳过 {code}：无可用数据")
                continue

            # 将pandas DataFrame转换为backtrader数据源
            data_feed = bt.feeds.PandasData(
                dataname=df,
                datetime=None,     # 使用index作为datetime
                open="open",
                high="high",
                low="low",
                close="close",
                volume="volume",
                openinterest=-1,   # 无持仓量数据
            )

            # 给数据源命名（用于交易记录中的标的标识）
            data_feed._name = code

            self.data_feeds.append(data_feed)

        if not self.data_feeds:
            raise ValueError("没有成功加载任何数据，无法进行回测")

        logger.info(f"成功加载 {len(self.data_feeds)} 只股票的数据")

    def run(self) -> Dict[str, Any]:
        """
        执行回测并返回结构化结果

        Returns:
            包含以下字段的字典：
            - summary: 绩效概览（年化收益、最大回撤、夏普比率等）
            - trades: 交易明细列表
            - equity_curve: 净值曲线DataFrame
            - initial_value: 初始资金
            - final_value: 最终资金
        """
        # 创建cerebro引擎
        self.cerebro = self._create_cerebro()

        # 添加数据源
        for data_feed in self.data_feeds:
            self.cerebro.adddata(data_feed)

        # 添加策略
        self.cerebro.addstrategy(DualMAStrategy)

        # 记录初始资金
        start_value = self.cerebro.broker.getvalue()
        logger.info(f"回测开始 | 初始资金: {start_value:,.2f}")

        # 运行回测
        self.results = self.cerebro.run()

        # 记录最终资金
        end_value = self.cerebro.broker.getvalue()
        logger.info(f"回测结束 | 最终资金: {end_value:,.2f}")

        # 提取结果
        return self._extract_results(start_value, end_value)

    def _extract_results(
        self, start_value: float, end_value: float
    ) -> Dict[str, Any]:
        """
        从回测结果中提取结构化数据

        第二阶段扩展点：
        - 可增加更多风险指标（Calmar比率、Sortino比率、信息比率等）
        - 可将结果序列化为JSON存入数据库
        - 可生成PDF/HTML格式的详细回测报告
        """
        if not self.results:
            raise RuntimeError("尚未运行回测，请先调用run()")

        strat = self.results[0]
        self.strategy_instance = strat

        # ========== 1. 绩效概览 ==========
        total_return = (end_value - start_value) / start_value

        # 计算回测年数
        start_dt = pd.to_datetime(self.start_date)
        end_dt = pd.to_datetime(self.end_date)
        years = max((end_dt - start_dt).days / 365.25, 0.01)

        # 年化收益率（CAGR）
        annual_return = (end_value / start_value) ** (1 / years) - 1 if years > 0 else 0

        # 夏普比率
        sharpe = None
        try:
            sharpe_analysis = strat.analyzers.sharpe.get_analysis()
            sharpe = sharpe_analysis.get("sharperatio", None)
            if sharpe is None:
                # 尝试其他key
                for key in sharpe_analysis:
                    if isinstance(sharpe_analysis[key], (int, float)):
                        sharpe = sharpe_analysis[key]
                        break
        except Exception as e:
            logger.warning(f"提取夏普比率失败：{e}")

        # 最大回撤
        max_drawdown = None
        try:
            dd_analysis = strat.analyzers.drawdown.get_analysis()
            max_drawdown = dd_analysis.get("max", {}).get("drawdown", None)
            if max_drawdown is None:
                max_drawdown = dd_analysis.get("drawdown", None)
        except Exception as e:
            logger.warning(f"提取最大回撤失败：{e}")

        # 交易统计
        trade_stats = self._extract_trade_stats(strat)

        summary = {
            "initial_value": start_value,
            "final_value": end_value,
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "total_trades": trade_stats.get("total_trades", 0),
            "win_rate": trade_stats.get("win_rate", 0),
            "profit_factor": trade_stats.get("profit_factor", 0),
            "avg_win": trade_stats.get("avg_win", 0),
            "avg_loss": trade_stats.get("avg_loss", 0),
            "commission_total": trade_stats.get("commission_total", 0),
        }

        # ========== 2. 交易明细 ==========
        trade_records = getattr(strat, "trade_records", [])

        # ========== 3. 净值曲线 ==========
        equity_curve = self._build_equity_curve()

        return {
            "summary": summary,
            "trades": trade_records,
            "equity_curve": equity_curve,
            "initial_value": start_value,
            "final_value": end_value,
        }

    def _extract_trade_stats(self, strat) -> Dict[str, Any]:
        """从TradeAnalyzer提取交易统计"""
        try:
            trade_analysis = strat.analyzers.trades.get_analysis()
        except Exception as e:
            logger.warning(f"提取交易分析失败：{e}")
            return {}

        total = trade_analysis.get("total", {}).get("total", 0)
        won = trade_analysis.get("won", {}).get("total", 0)
        lost = trade_analysis.get("lost", {}).get("total", 0)

        # 胜率
        win_rate = won / total if total > 0 else 0

        # 盈亏比（平均盈利 / 平均亏损）
        avg_win = trade_analysis.get("won", {}).get("pnl", {}).get("average", 0)
        avg_loss = abs(trade_analysis.get("lost", {}).get("pnl", {}).get("average", 0))

        profit_factor = None
        if avg_loss and avg_loss > 0 and avg_win:
            profit_factor = avg_win / avg_loss

        return {
            "total_trades": total,
            "won": won,
            "lost": lost,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "commission_total": trade_analysis.get("total", {}).get("commission", 0),
        }

    def _build_equity_curve(self) -> pd.DataFrame:
        """
        构建净值曲线DataFrame。
        通过重新运行策略并记录每日净值来实现。

        第二阶段扩展点：可增加benchmark曲线对比（如沪深300指数）。
        """
        if not self.data_feeds:
            return pd.DataFrame()

        try:
            return self.get_equity_curve_detailed()
        except Exception as e:
            logger.warning(f"构建净值曲线失败：{e}")
            return pd.DataFrame()

    def get_equity_curve_detailed(self) -> pd.DataFrame:
        """
        获取详细的每日净值曲线。
        通过重新运行回测并记录每日净值来实现。
        """
        # 使用自定义的ValueRecorder策略来记录每日净值
        class ValueRecorder(DualMAStrategy):
            def __init__(self):
                super().__init__()
                self.daily_values = []

            def next(self):
                super().next()
                # 记录每个交易日的净值（以第一个数据源的日期为准）
                if len(self.datas) > 0:
                    dt = self.datas[0].datetime.date(0)
                    # 避免同一天重复记录（多股票时）
                    if not self.daily_values or self.daily_values[-1]["date"] != dt:
                        self.daily_values.append({
                            "date": dt,
                            "value": self.broker.getvalue(),
                            "cash": self.broker.getcash(),
                        })

        # 重新创建cerebro并运行
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.initial_cash)
        cerebro.broker.setcommission(commission=self.commission)
        cerebro.broker.set_slippage_perc(perc=SLIPPAGE)
        cerebro.broker.set_coc(True)

        for data_feed in self.data_feeds:
            cerebro.adddata(data_feed)

        cerebro.addstrategy(ValueRecorder)
        results = cerebro.run()

        recorder = results[0]
        if hasattr(recorder, "daily_values") and recorder.daily_values:
            df = pd.DataFrame(recorder.daily_values)
            df["date"] = pd.to_datetime(df["date"])
            # 计算回撤
            df["peak"] = df["value"].cummax()
            df["drawdown"] = (df["value"] - df["peak"]) / df["peak"]
            return df

        return pd.DataFrame()
