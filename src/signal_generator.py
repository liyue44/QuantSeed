"""
信号生成模块 - signal_generator.py
=================================
独立于回测框架，基于纯pandas计算最新行情的交易信号。
用于生成"次日预选买入信号清单"，供人工审核。

核心逻辑：
1. 读取所有股票池的最新日线数据
2. 计算MA20和MA60
3. 筛选出最近发生金叉（MA20上穿MA60）的股票
4. 生成信号清单，包含信号强度、建议买入价等

第二阶段扩展点：
- 所有信号生成函数返回标准DataFrame，可直接推送至审核接口或数据库
- 可增加更多技术指标信号（MACD金叉、RSI超卖等）
- 可增加信号过滤规则（如成交量放大确认、大盘环境判断）
- 可增加信号评分系统，综合多个指标打分排序
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Optional

from config import (
    DATA_DIR, OUTPUT_DIR, MA_FAST, MA_SLOW,
    setup_logging, ensure_dirs
)
from data_manager import DataManager

logger = setup_logging("SignalGenerator")


class SignalGenerator:
    """
    独立信号生成器

    所有方法均为@staticmethod，返回标准DataFrame。
    第二阶段可直接复用这些方法，无需修改核心逻辑。
    """

    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: list) -> pd.DataFrame:
        """
        为DataFrame添加移动平均线列

        Args:
            df: 包含'收盘'列的DataFrame（按日期升序排列）
            periods: 均线周期列表，如[20, 60]

        Returns:
            添加了MA列的DataFrame

        第二阶段扩展点：可增加EMA、WMA等其他均线类型。
        """
        df = df.copy()
        for period in periods:
            col_name = f"ma{period}"
            df[col_name] = df["收盘"].rolling(window=period).mean()
        return df

    @staticmethod
    def detect_golden_cross(df: pd.DataFrame, fast: int = MA_FAST, slow: int = MA_SLOW) -> pd.DataFrame:
        """
        检测金叉信号（快线上穿慢线）

        判断条件：
        - 当天：MA_fast > MA_slow（快线在慢线上方）
        - 前一天：MA_fast <= MA_slow（快线在慢线下方或等于）
        即：发生了上穿

        Args:
            df: 已包含MA列的DataFrame
            fast: 快线周期
            slow: 慢线周期

        Returns:
            添加了'golden_cross'布尔列的DataFrame

        第二阶段扩展点：可增加死叉检测、背离检测等。
        """
        df = df.copy()
        fast_col = f"ma{fast}"
        slow_col = f"ma{slow}"

        if fast_col not in df.columns or slow_col not in df.columns:
            df = SignalGenerator.calculate_ma(df, [fast, slow])

        # 金叉条件：今天快线>慢线 且 昨天快线<=慢线
        today_above = df[fast_col] > df[slow_col]
        yesterday_below = df[fast_col].shift(1) <= df[slow_col].shift(1)
        df["golden_cross"] = today_above & yesterday_below

        # 死叉条件：今天快线<慢线 且 昨天快线>=慢线
        today_below = df[fast_col] < df[slow_col]
        yesterday_above = df[fast_col].shift(1) >= df[slow_col].shift(1)
        df["death_cross"] = today_below & yesterday_above

        return df

    @staticmethod
    def calculate_signal_strength(df: pd.DataFrame, fast: int = MA_FAST, slow: int = MA_SLOW) -> pd.Series:
        """
        计算信号强度（金叉时的乖离率）

        乖离率 = (MA_fast - MA_slow) / MA_slow * 100
        正值越大，表示快线偏离慢线越远，趋势越强。

        第二阶段扩展点：可综合成交量、波动率等因素构建复合信号强度。
        """
        fast_col = f"ma{fast}"
        slow_col = f"ma{slow}"
        divergence = (df[fast_col] - df[slow_col]) / df[slow_col] * 100
        return divergence

    @staticmethod
    def generate_signals(
        codes: Optional[list] = None,
        lookback_days: int = 5,
    ) -> pd.DataFrame:
        """
        主函数：生成最新交易信号

        扫描股票池所有股票，筛选出最近N天内发生金叉的股票。
        返回标准DataFrame，包含信号详情。

        Args:
            codes: 股票代码列表，None则使用默认股票池
            lookback_days: 回看天数，在此天数内发生金叉的都会被选出

        Returns:
            DataFrame包含字段：
            - code: 股票代码（带后缀）
            - pure_code: 纯数字代码
            - name: 股票名称
            - cross_date: 金叉发生日期
            - latest_date: 最新数据日期
            - latest_close: 最新收盘价
            - suggested_buy_price: 建议买入价（金叉次日开盘价，近似为最新价）
            - signal_strength: 信号强度（乖离率%）
            - ma_fast: 快线值
            - ma_slow: 慢线值
            - days_since_cross: 距金叉天数

        第二阶段扩展点：
        - 返回的DataFrame可直接通过API推送到审核系统
        - 可写入数据库（如SQLite/PostgreSQL）
        - 可通过消息队列发送到交易终端
        """
        ensure_dirs()
        dm = DataManager()
        codes = codes or dm.stock_pool

        signals = []
        today = datetime.now()

        logger.info(f"开始生成信号，扫描 {len(codes)} 只股票...")

        for code in codes:
            try:
                filepath = os.path.join(DATA_DIR, f"{code}.csv")
                if not os.path.exists(filepath):
                    continue

                # 读取数据
                df = pd.read_csv(filepath, dtype={"日期": str})
                if df.empty or len(df) < MA_SLOW + 10:
                    continue

                df["日期"] = pd.to_datetime(df["日期"])
                df = df.sort_values("日期").reset_index(drop=True)

                # 计算均线和金叉
                df = SignalGenerator.detect_golden_cross(df, MA_FAST, MA_SLOW)

                # 计算信号强度
                df["signal_strength"] = SignalGenerator.calculate_signal_strength(df, MA_FAST, MA_SLOW)

                # 筛选最近lookback_days内的金叉
                cutoff_date = today - timedelta(days=lookback_days)
                recent_crosses = df[
                    (df["golden_cross"] == True) &
                    (df["日期"] >= pd.Timestamp(cutoff_date))
                ]

                for _, row in recent_crosses.iterrows():
                    cross_date = row["日期"]
                    days_since = (today - cross_date).days

                    # 获取股票名称
                    name = dm.get_stock_name(code)

                    signals.append({
                        "code": code,
                        "pure_code": dm._code_to_akshare(code),
                        "name": name,
                        "cross_date": cross_date.strftime("%Y-%m-%d"),
                        "latest_date": df["日期"].iloc[-1].strftime("%Y-%m-%d"),
                        "latest_close": round(float(row["收盘"]), 2),
                        "suggested_buy_price": round(float(row["开盘"]), 2),
                        "signal_strength": round(float(row.get("signal_strength", 0)), 4),
                        "ma_fast": round(float(row.get(f"ma{MA_FAST}", 0)), 2),
                        "ma_slow": round(float(row.get(f"ma{MA_SLOW}", 0)), 2),
                        "days_since_cross": days_since,
                    })

            except Exception as e:
                logger.warning(f"处理 {code} 信号失败：{e}")
                continue

        if not signals:
            logger.warning("未生成任何信号")
            return pd.DataFrame()

        # 构建DataFrame并排序（按信号强度降序）
        result = pd.DataFrame(signals)
        result = result.sort_values("signal_strength", ascending=False).reset_index(drop=True)

        # 保存信号到CSV
        output_path = os.path.join(OUTPUT_DIR, "signals.csv")
        result.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"信号生成完成，共 {len(result)} 条，已保存至 {output_path}")

        return result

    @staticmethod
    def get_market_trend(codes: Optional[list] = None) -> pd.DataFrame:
        """
        获取市场趋势概况（所有股票的均线状态）

        Returns:
            DataFrame包含每只股票的最新价格、均线位置、趋势判断

        第二阶段扩展点：可用于判断整体市场环境，辅助仓位管理。
        """
        dm = DataManager()
        codes = codes or dm.stock_pool

        trends = []
        for code in codes:
            try:
                filepath = os.path.join(DATA_DIR, f"{code}.csv")
                if not os.path.exists(filepath):
                    continue

                df = pd.read_csv(filepath, dtype={"日期": str})
                if df.empty:
                    continue

                df["日期"] = pd.to_datetime(df["日期"])
                df = df.sort_values("日期").reset_index(drop=True)
                df = SignalGenerator.calculate_ma(df, [MA_FAST, MA_SLOW])

                latest = df.iloc[-1]
                close = float(latest["收盘"])
                ma_fast_val = float(latest.get(f"ma{MA_FAST}", np.nan))
                ma_slow_val = float(latest.get(f"ma{MA_SLOW}", np.nan))

                # 趋势判断
                if pd.notna(ma_fast_val) and pd.notna(ma_slow_val):
                    if close > ma_fast_val > ma_slow_val:
                        trend = "多头排列"
                    elif close < ma_fast_val < ma_slow_val:
                        trend = "空头排列"
                    elif ma_fast_val > ma_slow_val:
                        trend = "短期偏多"
                    else:
                        trend = "短期偏空"
                else:
                    trend = "数据不足"

                trends.append({
                    "code": code,
                    "name": dm.get_stock_name(code),
                    "close": close,
                    f"ma{MA_FAST}": round(ma_fast_val, 2) if pd.notna(ma_fast_val) else None,
                    f"ma{MA_SLOW}": round(ma_slow_val, 2) if pd.notna(ma_slow_val) else None,
                    "trend": trend,
                })

            except Exception as e:
                logger.warning(f"分析 {code} 趋势失败：{e}")

        return pd.DataFrame(trends)


# ==================== 模块自测 ====================
if __name__ == "__main__":
    # 测试信号生成
    signals = SignalGenerator.generate_signals()
    if not signals.empty:
        print("\n======== 最新金叉信号 ========")
        print(signals.to_string(index=False))
    else:
        print("当前无金叉信号")

    # 测试市场趋势
    trends = SignalGenerator.get_market_trend()
    if not trends.empty:
        print("\n======== 市场趋势概况 ========")
        print(trends.to_string(index=False))
