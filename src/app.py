"""
QuantSeed 主界面 - app.py
========================
基于Streamlit构建的多功能仪表盘。

功能模块：
1. 侧边栏 - 数据更新、回测参数设置、信号监控
2. 主区域 - 绩效概览卡片、资金曲线图、交易明细表、信号预览表

运行方式：
    streamlit run src/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys

# 将src目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    PAGE_TITLE, PAGE_LAYOUT, SIDEBAR_STATE,
    INITIAL_CASH, COMMISSION_RATE, MA_FAST, MA_SLOW,
    setup_logging, ensure_dirs, DATA_DIR, OUTPUT_DIR,
)
from data_manager import DataManager
from backtest_engine import BacktestEngine
from signal_generator import SignalGenerator

# 初始化
ensure_dirs()
logger = setup_logging("App")

# ==================== 页面配置 ====================
st.set_page_config(
    page_title=PAGE_TITLE,
    layout=PAGE_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)

# ==================== 缓存与全局状态 ====================


@st.cache_resource
def get_data_manager() -> DataManager:
    """获取DataManager单例（缓存）"""
    return DataManager()


def init_session_state():
    """初始化session_state"""
    defaults = {
        "backtest_result": None,
        "equity_curve": None,
        "signals_df": None,
        "trends_df": None,
        "update_status": None,
        "data_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# ==================== 标题栏 ====================
st.title("🌱 QuantSeed 量化种子")
st.markdown("### 离线回测与策略监控平台")

st.markdown("---")

# ==================== 侧边栏 ====================
with st.sidebar:
    st.header("📋 控制台")

    # ---- 数据管理区域 ----
    st.subheader("📥 数据管理")
    dm = get_data_manager()

    # 显示当前数据状态
    available = dm.get_available_stocks()
    st.metric("已下载股票数", f"{len(available)}/{len(dm.stock_pool)}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 更新数据", width="stretch", type="primary"):
            with st.spinner("正在下载数据，请耐心等待..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                total = len(dm.stock_pool)
                for idx, code in enumerate(dm.stock_pool):
                    status_text.text(f"正在处理: {code} ({idx+1}/{total})")
                    try:
                        dm.download_data(codes=[code])
                    except Exception:
                        pass
                    progress_bar.progress((idx + 1) / total)

                progress_bar.empty()
                status_text.empty()
                st.session_state.update_status = "数据更新完成！"
                st.session_state.data_loaded = True
                st.success("数据更新完成！")
                st.rerun()

    with col2:
        if st.button("📊 查看数据状态", width="stretch"):
            st.session_state.data_loaded = True
            st.rerun()

    st.divider()

    # ---- 回测参数设置 ----
    st.subheader("⚙️ 回测参数")

    # 日期范围
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "开始日期",
            value=datetime(2020, 1, 1),
            min_value=datetime(2018, 1, 1),
            max_value=datetime.now(),
        )
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=datetime.now(),
            min_value=datetime(2018, 1, 1),
            max_value=datetime.now(),
        )

    # 初始资金
    initial_cash = st.number_input(
        "初始资金（元）",
        min_value=10000,
        max_value=100000000,
        value=int(INITIAL_CASH),
        step=100000,
        format="%d",
    )

    # 手续费
    commission = st.number_input(
        "手续费率",
        min_value=0.0,
        max_value=0.01,
        value=COMMISSION_RATE,
        step=0.0001,
        format="%.4f",
        help="如万2.5填0.00025",
    )

    # 选择回测股票
    available_stocks = dm.get_available_stocks()
    if available_stocks:
        selected_stocks = st.multiselect(
            "选择回测股票",
            options=available_stocks,
            default=available_stocks[:5] if len(available_stocks) >= 5 else available_stocks,
            help="建议选择3-10只股票以获得较好的回测效果",
        )
    else:
        selected_stocks = []
        st.warning("暂无可用数据，请先更新数据")

    # 开始回测按钮
    if st.button("🚀 开始回测", width="stretch", type="primary"):
        if not selected_stocks:
            st.error("请先选择至少一只回测股票")
        else:
            with st.spinner("回测运行中..."):
                try:
                    engine = BacktestEngine(
                        initial_cash=initial_cash,
                        commission=commission,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                    )
                    engine.add_data_from_manager(dm, codes=selected_stocks)
                    result = engine.run()

                    # 获取详细净值曲线
                    equity_curve = engine.get_equity_curve_detailed()

                    st.session_state.backtest_result = result
                    st.session_state.equity_curve = equity_curve
                    st.success("回测完成！")
                    st.rerun()

                except Exception as e:
                    st.error(f"回测失败：{e}")
                    logger.error(f"回测执行异常：{e}", exc_info=True)

    st.divider()

    # ---- 信号监控区域 ----
    st.subheader("📡 信号监控")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 生成今日信号", width="stretch"):
            with st.spinner("正在分析信号..."):
                try:
                    signals = SignalGenerator.generate_signals()
                    st.session_state.signals_df = signals
                    if not signals.empty:
                        st.success(f"发现 {len(signals)} 个金叉信号！")
                    else:
                        st.info("当前无金叉信号")
                    st.rerun()
                except Exception as e:
                    st.error(f"信号生成失败：{e}")
                    logger.error(f"信号生成异常：{e}", exc_info=True)

    with col2:
        if st.button("📈 市场趋势", width="stretch"):
            with st.spinner("分析市场趋势..."):
                try:
                    trends = SignalGenerator.get_market_trend()
                    st.session_state.trends_df = trends
                    st.success(f"分析了 {len(trends)} 只股票")
                    st.rerun()
                except Exception as e:
                    st.error(f"趋势分析失败：{e}")

    st.divider()

    # ---- 学习中心入口 ----
    st.subheader("📚 学习中心")
    st.caption("左侧导航栏 → 知识库 | 算法可视化 | 实时行情")

    st.divider()

    # ---- 配置信息 ----
    st.caption(f"策略: MA{MA_FAST} × MA{MA_SLOW} | 仓位: 95% | T+1模拟")


# ==================== 主区域 ====================

# 创建标签页
tab1, tab2, tab3, tab4 = st.tabs(["📊 回测仪表盘", "📋 交易明细", "📡 信号预览", "📈 数据概览"])

# ==================== Tab 1: 回测仪表盘 ====================
with tab1:
    if st.session_state.backtest_result is None:
        st.info("👈 请在左侧设置参数并点击「开始回测」")
        st.markdown("""
        ### 快速入门
        1. **更新数据**：点击左侧「更新数据」按钮下载行情数据
        2. **设置参数**：选择回测日期和股票
        3. **开始回测**：点击「开始回测」运行策略
        4. **查看结果**：在仪表盘中分析策略绩效
        """)
    else:
        result = st.session_state.backtest_result
        summary = result["summary"]

        # ---- 概览指标卡片 ----
        st.subheader("📊 绩效概览")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_return = summary.get("total_return", 0)
            st.metric(
                label="总收益率",
                value=f"{total_return:.2%}",
                delta=f"¥{summary.get('final_value', 0) - summary.get('initial_value', 0):,.0f}",
            )

        with col2:
            max_dd = summary.get("max_drawdown", 0) or 0
            if isinstance(max_dd, (int, float)) and max_dd > 1:
                max_dd = max_dd / 100
            st.metric(
                label="最大回撤",
                value=f"{max_dd:.2%}",
                delta=None,
                delta_color="inverse",
            )

        with col3:
            sharpe = summary.get("sharpe_ratio")
            sharpe_str = f"{sharpe:.2f}" if sharpe is not None else "N/A"
            st.metric(
                label="夏普比率",
                value=sharpe_str,
            )

        with col4:
            st.metric(
                label="交易次数",
                value=summary.get("total_trades", 0),
            )

        # 第二行指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("年化收益率", f"{summary.get('annual_return', 0):.2%}")
        with col2:
            st.metric("胜率", f"{summary.get('win_rate', 0):.1%}")
        with col3:
            pf = summary.get("profit_factor")
            pf_str = f"{pf:.2f}" if pf else "N/A"
            st.metric("盈亏比", pf_str)
        with col4:
            st.metric("手续费合计", f"¥{summary.get('commission_total', 0):,.2f}")

        # ---- 资金曲线图 ----
        st.subheader("📈 资金曲线")

        equity = st.session_state.equity_curve
        if equity is not None and not equity.empty and "date" in equity.columns:
            # 使用Plotly绘制交互式双面板图
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.7, 0.3],
                subplot_titles=("净值曲线", "回撤区域"),
            )

            # 净值曲线
            fig.add_trace(
                go.Scatter(
                    x=equity["date"],
                    y=equity["value"],
                    mode="lines",
                    name="账户净值",
                    line=dict(color="#1f77b4", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(31, 119, 180, 0.1)",
                    hovertemplate="日期: %{x}<br>净值: ¥%{y:,.0f}<extra></extra>",
                ),
                row=1, col=1,
            )

            # 初始资金参考线
            fig.add_hline(
                y=summary["initial_value"],
                line_dash="dash",
                line_color="gray",
                annotation_text="初始资金",
                row=1, col=1,
            )

            # 回撤区域
            if "drawdown" in equity.columns:
                dd_values = equity["drawdown"] * 100  # 转为百分比
                fig.add_trace(
                    go.Scatter(
                        x=equity["date"],
                        y=dd_values,
                        mode="lines",
                        name="回撤率",
                        line=dict(color="#d62728", width=1),
                        fill="tozeroy",
                        fillcolor="rgba(214, 39, 40, 0.2)",
                        hovertemplate="日期: %{x}<br>回撤: %{y:.2f}%<extra></extra>",
                    ),
                    row=2, col=1,
                )

            fig.update_layout(
                height=500,
                hovermode="x unified",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=40, b=10),
            )

            fig.update_yaxes(title_text="净值 (¥)", row=1, col=1)
            fig.update_yaxes(title_text="回撤 (%)", row=2, col=1)
            fig.update_xaxes(title_text="日期", row=2, col=1)

            st.plotly_chart(fig, width="stretch")

            # 关键数据展示
            with st.expander("📊 详细绩效数据"):
                st.json({k: v for k, v in summary.items() if v is not None})
        else:
            st.info("暂无详细净值曲线数据。请确保回测已正确运行。")

# ==================== Tab 2: 交易明细 ====================
with tab2:
    if st.session_state.backtest_result is None:
        st.info("请先运行回测")
    else:
        trades = st.session_state.backtest_result.get("trades", [])
        if not trades:
            st.info("回测期间无交易记录")
        else:
            st.subheader(f"📋 交易明细（共 {len(trades)} 笔）")

            # 转换为DataFrame
            trades_df = pd.DataFrame(trades)

            # 按股票筛选
            if "code" in trades_df.columns:
                all_codes = trades_df["code"].unique().tolist()
                filter_code = st.selectbox(
                    "按股票筛选",
                    options=["全部"] + all_codes,
                )
                if filter_code != "全部":
                    trades_df = trades_df[trades_df["code"] == filter_code]

            # 按买卖方向着色
            def color_direction(val):
                if val == "BUY":
                    return "color: #e74c3c; font-weight: bold"
                elif val == "SELL":
                    return "color: #27ae60; font-weight: bold"
                return ""

            # 格式化显示
            display_df = trades_df.copy()
            if "date" in display_df.columns:
                display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")
            if "price" in display_df.columns:
                display_df["price"] = display_df["price"].round(2)
            if "value" in display_df.columns:
                display_df["value"] = display_df["value"].round(2)
            if "commission" in display_df.columns:
                display_df["commission"] = display_df["commission"].round(2)

            # 按时间倒序
            if "date" in display_df.columns:
                display_df = display_df.sort_values("date", ascending=False)

            st.dataframe(
                display_df.style.map(color_direction, subset=["direction"]),
                width="stretch",
                height=400,
            )

# ==================== Tab 3: 信号预览 ====================
with tab3:
    st.subheader("📡 策略信号预览")

    # 显示已生成的信号
    if st.session_state.signals_df is not None and not st.session_state.signals_df.empty:
        signals = st.session_state.signals_df
        st.markdown(f"### 🔔 发现 {len(signals)} 个金叉信号")

        # 信号卡片展示
        for _, row in signals.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1, 2])
                with col1:
                    st.markdown(f"**{row.get('name', row['code'])}**")
                    st.caption(f"{row['code']}")
                with col2:
                    st.metric("最新价", f"¥{row['latest_close']}")
                with col3:
                    st.metric("建议买入价", f"¥{row['suggested_buy_price']}")
                with col4:
                    strength = row.get("signal_strength", 0)
                    st.metric("信号强度", f"{strength:.2f}%")
                with col5:
                    st.metric("金叉日期", str(row.get("cross_date", "")))
                st.divider()

        # 完整表格
        with st.expander("📊 查看完整信号表"):
            display_signals = signals.copy()
            st.dataframe(display_signals, width="stretch")

    else:
        st.info("暂无信号数据，请点击左侧「生成今日信号」按钮")

        # 如果已生成但为空
        if st.session_state.signals_df is not None and st.session_state.signals_df.empty:
            st.success("当前无符合条件的金叉信号，市场可能处于震荡或下跌趋势中。")

    # 市场趋势
    if st.session_state.trends_df is not None and not st.session_state.trends_df.empty:
        st.markdown("---")
        st.subheader("📈 市场趋势概况")
        trends = st.session_state.trends_df

        # 趋势分布统计
        if "trend" in trends.columns:
            trend_counts = trends["trend"].value_counts()
            cols = st.columns(len(trend_counts))
            for i, (trend_name, count) in enumerate(trend_counts.items()):
                with cols[i]:
                    st.metric(trend_name, count)

        st.dataframe(trends, width="stretch")

# ==================== Tab 4: 数据概览 ====================
with tab4:
    st.subheader("📦 数据概览")

    # 本地数据统计
    available_stocks = dm.get_available_stocks()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("股票池总数", len(dm.stock_pool))
    with col2:
        st.metric("已下载", len(available_stocks))
    with col3:
        st.metric("待下载", len(dm.stock_pool) - len(available_stocks))

    # 各股票数据情况
    if available_stocks:
        st.markdown("### 📋 各股票数据详情")
        stock_info = []
        for code in available_stocks:
            filepath = os.path.join(DATA_DIR, f"{code}.csv")
            try:
                df = pd.read_csv(filepath, dtype={"日期": str})
                if not df.empty:
                    df["日期"] = pd.to_datetime(df["日期"])
                    name = dm.get_stock_name(code)
                    stock_info.append({
                        "代码": code,
                        "名称": name,
                        "记录数": len(df),
                        "最早日期": df["日期"].min().strftime("%Y-%m-%d"),
                        "最新日期": df["日期"].max().strftime("%Y-%m-%d"),
                    })
            except Exception:
                pass

        if stock_info:
            info_df = pd.DataFrame(stock_info)
            st.dataframe(info_df, width="stretch")

    # 股票池管理
    st.markdown("### 🔧 股票池管理")
    with st.expander("查看/编辑股票池"):
        st.markdown("当前股票池代码：")
        codes_text = "\n".join(dm.stock_pool)
        edited_codes = st.text_area(
            "每行一个股票代码（格式：000001.XSHE）",
            value=codes_text,
            height=300,
        )
        if st.button("💾 保存股票池"):
            new_codes = [c.strip() for c in edited_codes.split("\n") if c.strip()]
            pd.DataFrame({"code": new_codes}).to_csv(
                os.path.join(DATA_DIR, "..", "hs300_stocks.csv"),
                index=False,
                encoding="utf-8-sig",
            )
            st.success(f"已保存 {len(new_codes)} 只股票到股票池")
            st.rerun()


# ==================== 页脚 ====================
st.markdown("---")
st.caption(
    "QuantSeed v1.0 | Phase 1 - 离线回测与策略监控 | "
    "第二阶段将支持半自动化实盘监控"
)
