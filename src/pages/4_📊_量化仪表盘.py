"""
QuantSeed 量化仪表盘 - 需要密码 quantseed
=======================================
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 密码保护
if "quantseed_verified" not in st.session_state:
    st.session_state.quantseed_verified = False

if not st.session_state.quantseed_verified:
    st.title("🔐 量化仪表盘")
    st.markdown("### 请输入密码访问")

    # 同时支持 URL 参数
    query_pwd = st.query_params.get("pwd", "")
    if query_pwd == "quantseed":
        st.session_state.quantseed_verified = True
        st.rerun()

    pwd = st.text_input("密码", type="password", placeholder="请输入量化模块密码")
    if st.button("✅ 验证", type="primary"):
        if pwd == "quantseed":
            st.session_state.quantseed_verified = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

# ==================== 已通过验证，显示仪表盘 ====================

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from config import (
    PAGE_TITLE, PAGE_LAYOUT, SIDEBAR_STATE,
    INITIAL_CASH, COMMISSION_RATE, MA_FAST, MA_SLOW,
    setup_logging, ensure_dirs, DATA_DIR, OUTPUT_DIR,
)
from data_manager import DataManager
from backtest_engine import BacktestEngine
from signal_generator import SignalGenerator

ensure_dirs()
logger = setup_logging("App")

st.set_page_config(
    page_title=PAGE_TITLE,
    layout=PAGE_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)


@st.cache_resource
def get_data_manager() -> DataManager:
    return DataManager()


def init_session_state():
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

# ==================== 响应式 CSS ====================
st.markdown("""
<style>
    @media (max-width: 768px) {
        .stApp { padding: 0.5rem !important; }
        h1 { font-size: 1.4rem !important; }
        h3 { font-size: 1rem !important; }
        .stButton button {
            font-size: 0.85rem !important;
            padding: 0.5rem 0.8rem !important;
        }
        [data-testid="stMetric"] {
            padding: 0.4rem !important;
        }
        [data-testid="stMetric"] label {
            font-size: 0.7rem !important;
        }
        [data-testid="stMetric"] div[data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
        }
    }
    @media (max-width: 480px) {
        h1 { font-size: 1.2rem !important; }
        .stButton button { font-size: 0.8rem !important; padding: 0.4rem 0.6rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 标题栏 ====================
st.title("🌱 QuantSeed 量化种子")
st.markdown("### 离线回测与策略监控平台")
st.markdown("---")

# ==================== 侧边栏 ====================
with st.sidebar:
    st.header("📋 控制台")

    # 返回主页
    if st.button("🏠 返回主页", width="stretch"):
        st.switch_page("app.py")

    st.divider()

    # ---- 数据管理区域 ----
    st.subheader("📥 数据管理")
    dm = get_data_manager()

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

    # ---- 自定义股票管理 ----
    st.subheader("➕ 自定义股票")

    if "show_add_stock" not in st.session_state:
        st.session_state.show_add_stock = False

    if st.button("➕ 添加股票", width="stretch"):
        st.session_state.show_add_stock = not st.session_state.show_add_stock

    if st.session_state.show_add_stock:
        st.markdown("---")
        st.markdown("#### 🔍 添加自定义股票")

        new_code = st.text_input(
            "股票代码",
            key="add_stock_code",
            placeholder="如 600519 或 600519.XSHG",
            help="6开头自动识别为上海(XSHG)，0/3开头自动识别为深圳(XSHE)"
        )

        col_v, col_a = st.columns(2)
        with col_v:
            if st.button("🔍 验证代码", width="stretch", key="btn_verify"):
                if not new_code.strip():
                    st.error("请输入股票代码")
                else:
                    with st.spinner("正在验证..."):
                        try:
                            import requests
                            from config import API_BASE_URL
                            resp = requests.post(
                                f"{API_BASE_URL}/api/stocks/custom/verify",
                                json={"code": new_code.strip()},
                                timeout=15,
                            )
                            data = resp.json()
                            if data.get("valid"):
                                if data.get("exists"):
                                    st.warning(f"⚠️ {data['message']}")
                                else:
                                    st.success(f"✅ {data['message']}")
                                    st.session_state.verified_code = new_code.strip()
                                    if "name" in data:
                                        st.session_state.verified_name = data["name"]
                            else:
                                st.error(data.get("detail", "验证失败"))
                        except Exception as e:
                            st.error(f"验证请求失败：{e}")

        with col_a:
            if st.button("✅ 确认添加", width="stretch", key="btn_add", type="primary"):
                code_to_add = st.session_state.get("verified_code", new_code.strip())
                if not code_to_add:
                    st.error("请先验证股票代码")
                else:
                    with st.spinner("正在添加..."):
                        try:
                            import requests
                            from config import API_BASE_URL
                            resp = requests.post(
                                f"{API_BASE_URL}/api/stocks/custom/add",
                                json={"code": code_to_add},
                                timeout=15,
                            )
                            data = resp.json()
                            if data.get("success"):
                                st.success(f"✅ {data['message']}")
                                st.session_state.verified_code = None
                                st.session_state.verified_name = None
                                st.session_state.show_add_stock = False
                                # 清除 DataManager 缓存
                                get_data_manager.clear()
                                st.cache_resource.clear()
                                st.rerun()
                            else:
                                st.error(data.get("detail", "添加失败"))
                        except Exception as e:
                            st.error(f"添加请求失败：{e}")

    # 显示已添加的自定义股票
    try:
        import requests
        from config import API_BASE_URL
        resp = requests.get(f"{API_BASE_URL}/api/stocks/custom/list", timeout=5)
        if resp.status_code == 200:
            custom_stocks = resp.json().get("stocks", [])
            if custom_stocks:
                st.markdown("---")
                st.markdown("##### 📌 我的自定义股票")
                for s in custom_stocks:
                    col_s, col_d = st.columns([4, 1])
                    with col_s:
                        st.markdown(f"**{s['name']}** · `{s['code']}`")
                    with col_d:
                        if st.button("🗑️", key=f"del_{s['code']}", help=f"删除 {s['code']}"):
                            try:
                                del_resp = requests.delete(
                                    f"{API_BASE_URL}/api/stocks/custom/{s['code']}",
                                    timeout=5,
                                )
                                if del_resp.status_code == 200:
                                    st.success(f"已删除 {s['name']}")
                                    get_data_manager.clear()
                                    st.cache_resource.clear()
                                    st.rerun()
                                else:
                                    st.error("删除失败")
                            except Exception as e:
                                st.error(f"删除请求失败：{e}")
    except Exception:
        pass

    st.divider()

    # ---- 回测参数 ----
    st.subheader("⚙️ 回测参数")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", value=datetime(2020, 1, 1),
                                    min_value=datetime(2018, 1, 1), max_value=datetime.now())
    with col2:
        end_date = st.date_input("结束日期", value=datetime.now(),
                                  min_value=datetime(2018, 1, 1), max_value=datetime.now())

    initial_cash = st.number_input("初始资金（元）", min_value=10000, max_value=100000000,
                                    value=int(INITIAL_CASH), step=100000, format="%d")
    commission = st.number_input("手续费率", min_value=0.0, max_value=0.01,
                                  value=COMMISSION_RATE, step=0.0001, format="%.4f")

    available_stocks = dm.get_available_stocks()
    if available_stocks:
        selected_stocks = st.multiselect(
            "选择回测股票", options=available_stocks,
            default=available_stocks[:5] if len(available_stocks) >= 5 else available_stocks)
    else:
        selected_stocks = []
        st.warning("暂无可用数据，请先更新数据")

    if st.button("🚀 开始回测", width="stretch", type="primary"):
        if not selected_stocks:
            st.error("请先选择至少一只回测股票")
        else:
            with st.spinner("回测运行中..."):
                try:
                    engine = BacktestEngine(
                        initial_cash=initial_cash, commission=commission,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                    )
                    engine.add_data_from_manager(dm, codes=selected_stocks)
                    result = engine.run()
                    equity_curve = engine.get_equity_curve_detailed()
                    st.session_state.backtest_result = result
                    st.session_state.equity_curve = equity_curve
                    st.success("回测完成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"回测失败：{e}")

    st.divider()
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
    st.caption(f"策略: MA{MA_FAST} × MA{MA_SLOW} | 仓位: 95% | T+1模拟")


# ==================== 主区域 ====================
tab1, tab2, tab3, tab4 = st.tabs(["📊 回测仪表盘", "📋 交易明细", "📡 信号预览", "📈 数据概览"])

with tab1:
    if st.session_state.backtest_result is None:
        st.info("👈 请在左侧设置参数并点击「开始回测」")
    else:
        result = st.session_state.backtest_result
        summary = result["summary"]
        st.subheader("📊 绩效概览")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_return = summary.get("total_return", 0)
            st.metric("总收益率", f"{total_return:.2%}",
                      delta=f"¥{summary.get('final_value', 0) - summary.get('initial_value', 0):,.0f}")
        with col2:
            max_dd = summary.get("max_drawdown", 0) or 0
            if isinstance(max_dd, (int, float)) and max_dd > 1:
                max_dd = max_dd / 100
            st.metric("最大回撤", f"{max_dd:.2%}", delta_color="inverse")
        with col3:
            sharpe = summary.get("sharpe_ratio")
            st.metric("夏普比率", f"{sharpe:.2f}" if sharpe is not None else "N/A")
        with col4:
            st.metric("交易次数", summary.get("total_trades", 0))

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("年化收益率", f"{summary.get('annual_return', 0):.2%}")
        with col2:
            st.metric("胜率", f"{summary.get('win_rate', 0):.1%}")
        with col3:
            pf = summary.get("profit_factor")
            st.metric("盈亏比", f"{pf:.2f}" if pf else "N/A")
        with col4:
            st.metric("手续费合计", f"¥{summary.get('commission_total', 0):,.2f}")

        st.subheader("📈 资金曲线")
        equity = st.session_state.equity_curve
        if equity is not None and not equity.empty and "date" in equity.columns:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                vertical_spacing=0.05, row_heights=[0.7, 0.3],
                                subplot_titles=("净值曲线", "回撤区域"))
            fig.add_trace(go.Scatter(
                x=equity["date"], y=equity["value"], mode="lines",
                name="账户净值", line=dict(color="#1f77b4", width=2),
                fill="tozeroy", fillcolor="rgba(31, 119, 180, 0.1)",
                hovertemplate="日期: %{x}<br>净值: ¥%{y:,.0f}<extra></extra>",
            ), row=1, col=1)
            fig.add_hline(y=summary["initial_value"], line_dash="dash",
                          line_color="gray", annotation_text="初始资金", row=1, col=1)
            if "drawdown" in equity.columns:
                dd_values = equity["drawdown"] * 100
                fig.add_trace(go.Scatter(
                    x=equity["date"], y=dd_values, mode="lines",
                    name="回撤率", line=dict(color="#d62728", width=1),
                    fill="tozeroy", fillcolor="rgba(214, 39, 40, 0.2)",
                    hovertemplate="日期: %{x}<br>回撤: %{y:.2f}%<extra></extra>",
                ), row=2, col=1)
            fig.update_layout(height=500, hovermode="x unified", showlegend=True,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                              margin=dict(l=10, r=10, t=40, b=10))
            fig.update_yaxes(title_text="净值 (¥)", row=1, col=1)
            fig.update_yaxes(title_text="回撤 (%)", row=2, col=1)
            fig.update_xaxes(title_text="日期", row=2, col=1)
            st.plotly_chart(fig, width="stretch")
            with st.expander("📊 详细绩效数据"):
                st.json({k: v for k, v in summary.items() if v is not None})
        else:
            st.info("暂无详细净值曲线数据。")

with tab2:
    if st.session_state.backtest_result is None:
        st.info("请先运行回测")
    else:
        trades = st.session_state.backtest_result.get("trades", [])
        if not trades:
            st.info("回测期间无交易记录")
        else:
            st.subheader(f"📋 交易明细（共 {len(trades)} 笔）")
            trades_df = pd.DataFrame(trades)
            if "code" in trades_df.columns:
                all_codes = trades_df["code"].unique().tolist()
                filter_code = st.selectbox("按股票筛选", options=["全部"] + all_codes)
                if filter_code != "全部":
                    trades_df = trades_df[trades_df["code"] == filter_code]
            display_df = trades_df.copy()
            if "date" in display_df.columns:
                display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")
            if "date" in display_df.columns:
                display_df = display_df.sort_values("date", ascending=False)
            st.dataframe(display_df, width="stretch", height=400)

with tab3:
    st.subheader("📡 策略信号预览")
    if st.session_state.signals_df is not None and not st.session_state.signals_df.empty:
        signals = st.session_state.signals_df
        st.markdown(f"### 🔔 发现 {len(signals)} 个金叉信号")
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
                    st.metric("信号强度", f"{row.get('signal_strength', 0):.2f}%")
                with col5:
                    st.metric("金叉日期", str(row.get("cross_date", "")))
                st.divider()
        with st.expander("📊 查看完整信号表"):
            st.dataframe(signals, width="stretch")
    else:
        st.info("暂无信号数据，请点击左侧「生成今日信号」按钮")

    if st.session_state.trends_df is not None and not st.session_state.trends_df.empty:
        st.markdown("---")
        st.subheader("📈 市场趋势概况")
        trends = st.session_state.trends_df
        if "trend" in trends.columns:
            trend_counts = trends["trend"].value_counts()
            cols = st.columns(len(trend_counts))
            for i, (trend_name, count) in enumerate(trend_counts.items()):
                with cols[i]:
                    st.metric(trend_name, count)
        st.dataframe(trends, width="stretch")

with tab4:
    st.subheader("📦 数据概览")
    available_stocks = dm.get_available_stocks()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("股票池总数", len(dm.stock_pool))
    with col2:
        st.metric("已下载", len(available_stocks))
    with col3:
        st.metric("待下载", len(dm.stock_pool) - len(available_stocks))

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
                        "代码": code, "名称": name, "记录数": len(df),
                        "最早日期": df["日期"].min().strftime("%Y-%m-%d"),
                        "最新日期": df["日期"].max().strftime("%Y-%m-%d"),
                    })
            except Exception:
                pass
        if stock_info:
            st.dataframe(pd.DataFrame(stock_info), width="stretch")

st.markdown("---")
st.caption("QuantSeed v2.0 | Phase 1 - 离线回测与策略监控")
