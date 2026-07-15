"""
核心算法可视化解析 - algorithm_visualizer.py
==========================================
将双均线策略的每一步计算过程可视化展示，彻底弄懂算法细节。
使用 akshare 实时拉取数据，pandas 计算均线和交叉，plotly 交互式展示。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import akshare as ak
from config import MA_FAST, MA_SLOW, setup_logging

logger = setup_logging("AlgorithmVisualizer")

# 预设股票：代码 -> (名称, 腾讯格式代码)
PRESET_STOCKS = {
    "平安银行": ("000001.XSHE", "sz000001"),
    "贵州茅台": ("600519.XSHG", "sh600519"),
    "宁德时代": ("300750.XSHE", "sz300750"),
    "招商银行": ("600036.XSHG", "sh600036"),
    "比亚迪": ("002594.XSHE", "sz002594"),
    "中国平安": ("601318.XSHG", "sh601318"),
}


def render_algorithm_visualizer():
    """渲染核心算法可视化解析页面"""

    st.markdown("""
    <style>
    .step-card {
        background: #f0f4ff;
        border-left: 5px solid #4a6cf7;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .formula-box {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        font-family: 'Consolas', monospace;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
    .signal-buy {
        color: #e74c3c;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .signal-sell {
        color: #27ae60;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .pnl-positive {
        color: #e74c3c;
        font-weight: bold;
    }
    .pnl-negative {
        color: #27ae60;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    ## 🔬 双均线策略：核心算法可视化解析

    以"双均线金叉买入、死叉卖出"策略为例，将每一步计算过程拆开来看，消除所有神秘感。
    """)

    # ==================== 控制面板 ====================
    st.markdown("### ⚙️ 参数设置")
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        stock_choice = st.selectbox(
            "选择股票",
            options=list(PRESET_STOCKS.keys()),
            index=0,
        )
        selected_code, selected_tx = PRESET_STOCKS[stock_choice]

        # 也支持手动输入
        manual_code = st.text_input("或手动输入腾讯格式代码", placeholder="如 sz000001", value="")
        if manual_code.strip():
            selected_tx = manual_code.strip()
            selected_code = manual_code.strip()

    with col2:
        end_date = st.date_input("结束日期", value=datetime.now())
        start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365))

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 获取数据", type="primary", width="stretch"):
            st.session_state.viz_data_loaded = False
            st.rerun()

    # ==================== 数据获取 ====================
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    # 初始化缓存key
    if "viz_data_cache" not in st.session_state:
        st.session_state.viz_data_cache = {}
    if "viz_data_loaded" not in st.session_state:
        st.session_state.viz_data_loaded = False

    cache_key = f"{selected_tx}_{start_str}_{end_str}"

    if not st.session_state.viz_data_loaded or cache_key not in st.session_state.viz_data_cache:
        with st.spinner(f"正在从网络获取 {selected_code} 数据..."):
            df = _fetch_stock_data(selected_tx, start_str, end_str)
            if df is not None and not df.empty:
                # 计算均线和交叉信号
                df = _calculate_ma(df, MA_FAST, MA_SLOW)
                df = _detect_crosses(df, MA_FAST, MA_SLOW)
                st.session_state.viz_data_cache[cache_key] = df
                st.session_state.viz_data_loaded = True
            else:
                st.error(f"获取 {selected_code} 数据失败，请检查网络或代码格式")
                return

    df = st.session_state.viz_data_cache.get(cache_key)
    if df is None or df.empty:
        st.info("请选择股票并点击「获取数据」")
        return

    st.success(f"✅ 已获取 {len(df)} 条日线数据（{df['date'].iloc[0]} ~ {df['date'].iloc[-1]}）")

    # ==================== 算法步骤分步展示 ====================
    st.markdown("---")
    st.markdown("### 📋 算法步骤拆解")

    step_tabs = st.tabs([
        "Step 1: 获取原始数据",
        "Step 2: 计算均线",
        "Step 3: 识别信号",
        "Step 4: 模拟交易",
    ])

    # ---- Step 1: 原始数据 ----
    with step_tabs[0]:
        _render_step1_raw_data(df, selected_code, stock_choice)

    # ---- Step 2: 计算均线 ----
    with step_tabs[1]:
        _render_step2_ma(df, MA_FAST, MA_SLOW)

    # ---- Step 3: 识别信号 ----
    with step_tabs[2]:
        _render_step3_signals(df, MA_FAST, MA_SLOW)

    # ---- Step 4: 模拟交易 ----
    with step_tabs[3]:
        _render_step4_simulation(df, MA_FAST, MA_SLOW)

    # ==================== 核心代码展示 ====================
    st.markdown("---")
    st.markdown("### 💻 核心代码逻辑")
    with st.expander("查看完整Python实现代码", expanded=False):
        st.code('''
import akshare as ak
import pandas as pd
import numpy as np

# ===== 1. 获取日线数据 =====
df = ak.stock_zh_a_hist_tx(
    symbol="sz000001",     # 腾讯格式：sz(深圳)/sh(上海)+代码
    start_date="20240101",
    end_date="20240711",
    adjust="qfq"           # 前复权
)
# 返回列: date, open, close, high, low, amount

# ===== 2. 计算移动平均线 =====
df["ma20"] = df["close"].rolling(window=20).mean()
df["ma60"] = df["close"].rolling(window=60).mean()

# ===== 3. 检测金叉和死叉 =====
# 金叉：今天 MA20 > MA60 且 昨天 MA20 <= MA60
df["golden_cross"] = (
    (df["ma20"] > df["ma60"]) &
    (df["ma20"].shift(1) <= df["ma60"].shift(1))
)

# 死叉：今天 MA20 < MA60 且 昨天 MA20 >= MA60
df["death_cross"] = (
    (df["ma20"] < df["ma60"]) &
    (df["ma20"].shift(1) >= df["ma60"].shift(1))
)

# ===== 4. 模拟交易收益 =====
# 获取所有金叉日期
buy_signals = df[df["golden_cross"]].index
for buy_idx in buy_signals:
    buy_price = df.loc[buy_idx + 1, "open"]  # T+1: 次日开盘买入

    # 找下一个死叉作为卖出点
    sell_candidates = df.loc[buy_idx:, "death_cross"]
    if sell_candidates.any():
        sell_idx = sell_candidates[sell_candidates].index[0]
        sell_price = df.loc[sell_idx + 1, "open"]  # T+1: 死叉次日开盘卖出
        profit = (sell_price - buy_price) / buy_price  # 收益率
''', language="python")


# ==================== 辅助函数 ====================

def _fetch_stock_data(tx_code: str, start: str, end: str) -> pd.DataFrame:
    """从 akshare 获取日线数据"""
    try:
        df = ak.stock_zh_a_hist_tx(
            symbol=tx_code,
            start_date=start,
            end_date=end,
            adjust="qfq",
            timeout=15.0,
        )
        if df is not None and not df.empty:
            df = df.rename(columns={
                "date": "date", "open": "open", "close": "close",
                "high": "high", "low": "low", "amount": "amount"
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            # 确保数值类型
            for col in ["open", "close", "high", "low"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
    except Exception as e:
        st.error(f"数据获取异常：{e}")
    return pd.DataFrame()


def _calculate_ma(df: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    """计算移动平均线"""
    df = df.copy()
    df[f"ma{fast}"] = df["close"].rolling(window=fast).mean()
    df[f"ma{slow}"] = df["close"].rolling(window=slow).mean()
    return df


def _detect_crosses(df: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    """检测金叉和死叉"""
    df = df.copy()
    fast_col = f"ma{fast}"
    slow_col = f"ma{slow}"

    df["golden_cross"] = (
        (df[fast_col] > df[slow_col]) &
        (df[fast_col].shift(1) <= df[slow_col].shift(1))
    )
    df["death_cross"] = (
        (df[fast_col] < df[slow_col]) &
        (df[fast_col].shift(1) >= df[slow_col].shift(1))
    )
    return df


def _render_step1_raw_data(df, code, name):
    """Step 1: 展示原始数据"""
    st.markdown("""
    <div class="step-card">
    <h4>📥 Step 1: 获取原始日线数据</h4>
    <p>通过 <code>akshare.stock_zh_a_hist_tx()</code> 从腾讯数据源拉取前复权日线数据。
    每条数据包含：日期、开盘价、收盘价、最高价、最低价、成交额。</p>
    </div>
    """, unsafe_allow_html=True)

    # K线图（Plotly）
    fig = _make_candlestick_chart(df, name, show_ma=False)
    st.plotly_chart(fig, width="stretch")

    # 数据预览表
    with st.expander("📊 查看原始数据（最近20条）"):
        display_df = df.tail(20)[["date", "open", "close", "high", "low", "amount"]].copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df = display_df.sort_values("date", ascending=False)
        st.dataframe(display_df, width="stretch", hide_index=True)


def _render_step2_ma(df, fast, slow):
    """Step 2: 计算并展示均线"""
    st.markdown(f"""
    <div class="step-card">
    <h4>🧮 Step 2: 计算移动平均线</h4>
    <p>使用 <code>pandas.Series.rolling(window=N).mean()</code> 计算过去N天的收盘价平均值。</p>
    <div class="formula-box">
    MA<sub>{fast}</sub> = df["close"].rolling(window={fast}).mean()<br>
    MA<sub>{slow}</sub> = df["close"].rolling(window={slow}).mean()
    </div>
    </div>
    """, unsafe_allow_html=True)

    # 最新数值卡片
    latest = df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("最新收盘价", f"¥{latest['close']:.2f}")
    with col2:
        ma_fast_val = latest.get(f"ma{fast}")
        st.metric(
            f"MA{fast}（快线）",
            f"¥{ma_fast_val:.2f}" if pd.notna(ma_fast_val) else "N/A"
        )
    with col3:
        ma_slow_val = latest.get(f"ma{slow}")
        st.metric(
            f"MA{slow}（慢线）",
            f"¥{ma_slow_val:.2f}" if pd.notna(ma_slow_val) else "N/A"
        )

    # K线+均线图
    fig = _make_candlestick_chart(df, "收盘价 + 均线叠加", show_ma=True, fast=fast, slow=slow)
    st.plotly_chart(fig, width="stretch")

    st.info(
        f"💡 蓝色线是 MA{fast}（快线），更灵敏地反映短期价格变化；"
        f"橙色线是 MA{slow}（慢线），反映中长期趋势方向。"
    )


def _render_step3_signals(df, fast, slow):
    """Step 3: 识别金叉死叉信号"""
    st.markdown(f"""
    <div class="step-card">
    <h4>🎯 Step 3: 识别交易信号</h4>
    <p>用 <code>shift()</code> 比较今天和昨天的均线关系：</p>
    <div class="formula-box">
    金叉 = (MA{fast} > MA{slow}) AND (前一天 MA{fast} &lt;= MA{slow})<br>
    死叉 = (MA{fast} &lt; MA{slow}) AND (前一天 MA{fast} >= MA{slow})
    </div>
    </div>
    """, unsafe_allow_html=True)

    # 统计信号数量
    golden_count = int(df["golden_cross"].sum())
    death_count = int(df["death_cross"].sum())

    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔺 金叉次数", golden_count)
    with col2:
        st.metric("🔻 死叉次数", death_count)

    # K线图+均线+标注信号点
    fig = _make_candlestick_chart_with_signals(df, fast, slow)
    st.plotly_chart(fig, width="stretch")

    # 信号日期表
    if golden_count > 0 or death_count > 0:
        st.markdown("#### 📋 信号日期明细")
        signal_rows = []
        for _, row in df.iterrows():
            if row["golden_cross"]:
                signal_rows.append({
                    "日期": row["date"].strftime("%Y-%m-%d"),
                    "信号": "🔺 金叉",
                    "收盘价": f"¥{row['close']:.2f}",
                    f"MA{fast}": f"¥{row.get(f'ma{fast}', 0):.2f}" if pd.notna(row.get(f'ma{fast}')) else "N/A",
                    f"MA{slow}": f"¥{row.get(f'ma{slow}', 0):.2f}" if pd.notna(row.get(f'ma{slow}')) else "N/A",
                })
            if row["death_cross"]:
                signal_rows.append({
                    "日期": row["date"].strftime("%Y-%m-%d"),
                    "信号": "🔻 死叉",
                    "收盘价": f"¥{row['close']:.2f}",
                    f"MA{fast}": f"¥{row.get(f'ma{fast}', 0):.2f}" if pd.notna(row.get(f'ma{fast}')) else "N/A",
                    f"MA{slow}": f"¥{row.get(f'ma{slow}', 0):.2f}" if pd.notna(row.get(f'ma{slow}')) else "N/A",
                })

        if signal_rows:
            signal_df = pd.DataFrame(signal_rows)
            st.dataframe(signal_df, width="stretch", hide_index=True)
    else:
        st.info("所选时间范围内未出现金叉或死叉信号。尝试扩大日期范围。")


def _render_step4_simulation(df, fast, slow):
    """Step 4: 模拟交易收益"""
    st.markdown("""
    <div class="step-card">
    <h4>💰 Step 4: 模拟交易盈亏</h4>
    <p>规则：金叉次日开盘买入 → 死叉次日开盘卖出（模拟T+1）。计算每笔交易的收益率。</p>
    </div>
    """, unsafe_allow_html=True)

    # 找出所有金叉位置，配对到下一个死叉
    trades = _simulate_trades(df)

    if not trades:
        st.info("所选时间范围内没有完整的买卖配对（金叉→死叉）。")
        return

    # 统计（使用 profit_pct_raw 数值字段）
    total_trades = len(trades)
    wins = sum(1 for t in trades if t["profit_pct_raw"] > 0)
    losses = sum(1 for t in trades if t["profit_pct_raw"] <= 0)
    total_return = sum(t["profit_pct_raw"] for t in trades)
    avg_return = total_return / total_trades if total_trades > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("交易次数", total_trades)
    with col2:
        st.metric("胜率", f"{wins/total_trades*100:.1f}%" if total_trades > 0 else "N/A")
    with col3:
        st.metric("累计收益", f"{total_return:.2f}%")
    with col4:
        st.metric("平均收益", f"{avg_return:.2f}%")

    # 交易明细表
    st.markdown("#### 📊 每笔交易明细")
    trade_df = pd.DataFrame(trades)
    trade_df["收益率"] = trade_df["profit_pct_raw"].apply(lambda x: f"{x:+.2f}%")
    st.dataframe(trade_df, width="stretch", hide_index=True)

    # 收益分布图
    profit_values = [t["profit_pct_raw"] for t in trades]
    fig = go.Figure()
    colors = ["#ef5350" if p > 0 else "#27ae60" for p in profit_values]
    fig.add_trace(go.Bar(
        x=list(range(1, len(trades) + 1)),
        y=profit_values,
        marker_color=colors,
        text=[f"{p:+.2f}%" for p in profit_values],
        textposition="outside",
        name="每笔收益",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="<b>每笔交易收益率分布</b>",
        height=350,
        xaxis_title="交易序号",
        yaxis_title="收益率 (%)",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, width="stretch")


def _simulate_trades(df):
    """模拟交易：金叉次日买入 → 死叉次日卖出"""
    trades = []
    golden_idxs = df[df["golden_cross"]].index.tolist()

    for buy_idx in golden_idxs:
        if buy_idx + 1 >= len(df):
            continue
        buy_date = df.loc[buy_idx + 1, "date"]
        buy_price = df.loc[buy_idx + 1, "open"]

        if pd.isna(buy_price) or buy_price <= 0:
            continue

        # 在金叉之后找下一个死叉
        after_df = df.loc[buy_idx:]
        sell_mask = after_df["death_cross"]
        if not sell_mask.any():
            # 无死叉，以最后一天收盘价卖出
            sell_date = df.loc[df.index[-1], "date"]
            sell_price = df.loc[df.index[-1], "close"]
            sell_type = "（无死叉，持有至期末）"
        else:
            sell_idx = sell_mask[sell_mask].index[0]
            if sell_idx + 1 < len(df):
                sell_date = df.loc[sell_idx + 1, "date"]
                sell_price = df.loc[sell_idx + 1, "open"]
            else:
                sell_date = df.loc[sell_idx, "date"]
                sell_price = df.loc[sell_idx, "close"]
            sell_type = "（死叉卖出）"

        if pd.isna(sell_price) or sell_price <= 0:
            continue

        profit_pct = (sell_price - buy_price) / buy_price * 100
        hold_days = (sell_date - buy_date).days

        trades.append({
            "买入日期": buy_date.strftime("%Y-%m-%d"),
            "买入价": f"¥{buy_price:.2f}",
            "卖出日期": sell_date.strftime("%Y-%m-%d"),
            "卖出价": f"¥{sell_price:.2f}",
            "持仓天数": hold_days,
            "收益率": f"{profit_pct:+.2f}%",
            "profit_pct": f"{profit_pct:+.2f}%",  # 用于display
            "profit_pct_raw": round(profit_pct, 2),  # 用于图表
        })

    return trades


# ==================== 绘图函数 ====================

def _make_candlestick_chart(df, title, show_ma=False, fast=None, slow=None):
    """绘制K线图（可选叠加均线）"""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.7, 0.3],
    )

    # K线
    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线",
        increasing_line_color="#ef5350",
        decreasing_line_color="#26a69a",
    ), row=1, col=1)

    if show_ma and fast and slow:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[f"ma{fast}"], mode="lines",
            name=f"MA{fast}", line=dict(color="#1f77b4", width=1.8),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[f"ma{slow}"], mode="lines",
            name=f"MA{slow}", line=dict(color="#ff7f0e", width=1.8),
        ), row=1, col=1)

    # 成交量（如果有的话）
    if "amount" in df.columns:
        # 用成交额作为参考（腾讯源无volume列）
        amount_vals = pd.to_numeric(df["amount"], errors="coerce") / 1e8
        fig.add_trace(go.Bar(
            x=df["date"], y=amount_vals,
            name="成交额(亿)", marker_color="rgba(128,128,128,0.3)",
        ), row=2, col=1)

    fig.update_layout(
        title=f"<b>{title}</b>",
        height=450,
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(title_text="价格 (元)", row=1, col=1)
    fig.update_yaxes(title_text="成交额(亿)", row=2, col=1)
    fig.update_xaxes(title_text="日期", row=2, col=1)

    return fig


def _make_candlestick_chart_with_signals(df, fast, slow):
    """绘制K线图+均线+金叉死叉标注"""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.7, 0.3],
    )

    # K线
    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线",
        increasing_line_color="#ef5350",
        decreasing_line_color="#26a69a",
        showlegend=True,
    ), row=1, col=1)

    # 均线
    fig.add_trace(go.Scatter(
        x=df["date"], y=df[f"ma{fast}"], mode="lines",
        name=f"MA{fast}", line=dict(color="#1f77b4", width=1.8),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df[f"ma{slow}"], mode="lines",
        name=f"MA{slow}", line=dict(color="#ff7f0e", width=1.8),
    ), row=1, col=1)

    # 标注金叉（绿色向上箭头）
    golden = df[df["golden_cross"]]
    if not golden.empty:
        fig.add_trace(go.Scatter(
            x=golden["date"], y=golden["low"] * 0.97,
            mode="markers+text",
            marker=dict(symbol="triangle-up", size=14, color="#e74c3c"),
            text=["🔺"] * len(golden),
            textposition="bottom center",
            textfont=dict(size=10),
            name="金叉",
            hovertext=[f"金叉: {d.strftime('%Y-%m-%d')}<br>收盘: ¥{c:.2f}"
                        for d, c in zip(golden["date"], golden["close"])],
            hoverinfo="text",
        ), row=1, col=1)

    # 标注死叉（红色向下箭头）
    death = df[df["death_cross"]]
    if not death.empty:
        fig.add_trace(go.Scatter(
            x=death["date"], y=death["high"] * 1.03,
            mode="markers+text",
            marker=dict(symbol="triangle-down", size=14, color="#27ae60"),
            text=["🔻"] * len(death),
            textposition="top center",
            textfont=dict(size=10),
            name="死叉",
            hovertext=[f"死叉: {d.strftime('%Y-%m-%d')}<br>收盘: ¥{c:.2f}"
                        for d, c in zip(death["date"], death["close"])],
            hoverinfo="text",
        ), row=1, col=1)

    # 成交额
    if "amount" in df.columns:
        amount_vals = pd.to_numeric(df["amount"], errors="coerce") / 1e8
        fig.add_trace(go.Bar(
            x=df["date"], y=amount_vals,
            name="成交额(亿)", marker_color="rgba(128,128,128,0.3)",
        ), row=2, col=1)

    fig.update_layout(
        title="<b>K线图 + 均线 + 金叉/死叉信号标注</b>",
        height=500,
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(title_text="价格 (元)", row=1, col=1)
    fig.update_yaxes(title_text="成交额(亿)", row=2, col=1)
    fig.update_xaxes(title_text="日期", row=2, col=1)

    return fig
