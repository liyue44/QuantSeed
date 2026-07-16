"""
实时行情演示与信号解读 - live_signal_viewer.py
==============================================
用最新市场数据展示行情面板、K线解读和交易信号工单。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import akshare as ak
from config import (
    DATA_DIR, OUTPUT_DIR, MA_FAST, MA_SLOW,
    setup_logging, ensure_dirs,
)
from data_manager import DataManager
from signal_generator import SignalGenerator

logger = setup_logging("LiveSignalViewer")
ensure_dirs()


def render_live_signal_viewer():
    """渲染实时行情演示与信号解读页面"""

    st.markdown("""
    <style>
    .stock-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.2s;
        cursor: pointer;
    }
    .stock-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-color: #4a6cf7;
    }
    .trend-bullish {
        color: #e74c3c;
        font-weight: bold;
    }
    .trend-bearish {
        color: #27ae60;
        font-weight: bold;
    }
    .trend-neutral {
        color: #f39c12;
        font-weight: bold;
    }
    .work-order {
        background: linear-gradient(135deg, #fff3e0, #ffe0b2);
        border: 2px solid #ff9800;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .interpretation-box {
        background: #f8f9fa;
        border-left: 4px solid #4a6cf7;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin: 1rem 0;
        line-height: 1.8;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    ## 📡 实时行情演示与信号解读

    用最新市场数据展示行情面板，对单只股票生成通俗易懂的行情解读，并输出关注信号工单。
    """)

    # 初始化 session state
    if "live_data" not in st.session_state:
        st.session_state.live_data = None
    if "selected_stock_detail" not in st.session_state:
        st.session_state.selected_stock_detail = None
    if "live_refresh_time" not in st.session_state:
        st.session_state.live_refresh_time = None

    # ==================== 行情面板 ====================
    st.markdown("### 📊 实时行情面板")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🔄 刷新行情", type="primary", use_container_width=True):
            with st.spinner("正在获取最新行情数据..."):
                try:
                    live_data = _fetch_live_data()
                    st.session_state.live_data = live_data
                    st.session_state.live_refresh_time = datetime.now().strftime("%H:%M:%S")
                    st.success(f"已刷新 {len(live_data)} 只股票行情")
                except Exception as e:
                    st.error(f"获取行情失败：{e}")

    with col2:
        # 使用本地已缓存的数据作为备选
        if st.button("📂 从本地数据加载", use_container_width=True):
            with st.spinner("从本地缓存加载..."):
                live_data = _load_from_local()
                st.session_state.live_data = live_data
                st.session_state.live_refresh_time = datetime.now().strftime("%H:%M:%S")
                if not live_data.empty:
                    st.success(f"已加载 {len(live_data)} 只股票行情")
                else:
                    st.warning("本地暂无数据，请先点击「刷新行情」")

    with col3:
        if st.session_state.live_refresh_time:
            st.metric("上次刷新", st.session_state.live_refresh_time)
        else:
            st.caption("尚未刷新")

    # ==================== 行情卡片网格 ====================
    live_data = st.session_state.live_data
    if live_data is None or live_data.empty:
        st.info("👆 点击「刷新行情」或「从本地数据加载」获取最新数据")
        st.markdown("""
        ### 功能说明
        - **刷新行情**：通过 akshare 实时获取最新日线数据
        - **从本地数据加载**：使用已下载到本地的数据（更快）
        - **点击任意股票卡片**：查看详细的K线解读和交易信号
        """)
        return

    # 数据时效性提示
    latest_dates = live_data["latest_date"].unique()
    if len(latest_dates) > 0:
        max_date = max(latest_dates)
        today = datetime.now()
        days_behind = (today - datetime.strptime(max_date, "%Y-%m-%d")).days

        if days_behind <= 1:
            st.success(f"✅ 数据日期：{max_date}（最新交易日，数据时效正常）")
        elif days_behind <= 3:
            st.warning(f"⚠️ 数据日期：{max_date}（已滞后 {days_behind} 天，可能是周末或节假日）")
        else:
            st.error(f"🔴 数据日期：{max_date}（已滞后 {days_behind} 天，请检查数据源或点击「刷新行情」）")

        st.caption("> 💡 A股日线数据在交易日收盘后更新，非交易时间看到的是上一个交易日的数据，属于正常现象。")

    # 显示行情卡片网格（每行4个）
    _render_stock_cards(live_data)

    # ==================== 单只股票详细解读 ====================
    if st.session_state.selected_stock_detail:
        st.markdown("---")
        _render_stock_detail(st.session_state.selected_stock_detail)


def _fetch_live_data():
    """通过 akshare 获取股票池最新行情"""
    dm = DataManager()
    codes = dm.stock_pool[:12]  # 取前12只作为演示

    records = []
    for code in codes:
        try:
            tx_code = dm._code_to_tx(code)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")

            df = ak.stock_zh_a_hist_tx(
                symbol=tx_code,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
                timeout=10.0,
            )
            if df is None or df.empty:
                continue

            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            # 计算均线
            df["ma20"] = df["close"].rolling(20).mean()
            df["ma60"] = df["close"].rolling(60).mean()

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            # 涨跌幅
            change_pct = (latest["close"] - prev["close"]) / prev["close"] * 100 if prev["close"] != 0 else 0

            # 均线状态判断
            ma20_val = latest.get("ma20")
            ma60_val = latest.get("ma60")
            close_val = latest["close"]

            trend, trend_class = _determine_trend(close_val, ma20_val, ma60_val, df)

            name = dm.get_stock_name(code)

            records.append({
                "code": code,
                "name": name,
                "close": round(float(close_val), 2),
                "change_pct": round(float(change_pct), 2),
                "ma20": round(float(ma20_val), 2) if pd.notna(ma20_val) else None,
                "ma60": round(float(ma60_val), 2) if pd.notna(ma60_val) else None,
                "trend": trend,
                "trend_class": trend_class,
                "latest_date": latest["date"].strftime("%Y-%m-%d"),
                "df": df.to_json(date_format="iso"),  # 缓存完整数据
            })

        except Exception as e:
            logger.warning(f"获取 {code} 行情失败：{e}")
            continue

    return pd.DataFrame(records)


def _load_from_local():
    """从本地CSV文件加载数据"""
    dm = DataManager()
    codes = dm.get_available_stocks()[:12]
    records = []

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

            # 取最近120天
            cutoff = datetime.now() - timedelta(days=120)
            df = df[df["日期"] >= pd.Timestamp(cutoff)]

            if df.empty:
                continue

            # 计算均线
            df["close"] = pd.to_numeric(df["收盘"], errors="coerce")
            df["open"] = pd.to_numeric(df["开盘"], errors="coerce")
            df["high"] = pd.to_numeric(df["最高"], errors="coerce")
            df["low"] = pd.to_numeric(df["最低"], errors="coerce")
            df["ma20"] = df["close"].rolling(20).mean()
            df["ma60"] = df["close"].rolling(60).mean()

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            change_pct = (latest["close"] - prev["close"]) / prev["close"] * 100 if prev["close"] != 0 else 0

            ma20_val = latest.get("ma20")
            ma60_val = latest.get("ma60")
            close_val = latest["close"]

            trend, trend_class = _determine_trend_local(close_val, ma20_val, ma60_val, df)

            name = dm.get_stock_name(code)

            records.append({
                "code": code,
                "name": name,
                "close": round(float(close_val), 2),
                "change_pct": round(float(change_pct), 2),
                "ma20": round(float(ma20_val), 2) if pd.notna(ma20_val) else None,
                "ma60": round(float(ma60_val), 2) if pd.notna(ma60_val) else None,
                "trend": trend,
                "trend_class": trend_class,
                "latest_date": latest["日期"].strftime("%Y-%m-%d"),
            })

        except Exception as e:
            logger.warning(f"加载 {code} 本地数据失败：{e}")
            continue

    return pd.DataFrame(records)


def _determine_trend(close, ma20, ma60, df):
    """判断均线趋势状态"""
    if pd.isna(ma20) or pd.isna(ma60):
        return "数据不足", "neutral"

    # 检查最近是否刚发生金叉/死叉
    df_copy = df.copy()
    df_copy["golden"] = (df_copy["ma20"] > df_copy["ma60"]) & (df_copy["ma20"].shift(1) <= df_copy["ma60"].shift(1))
    df_copy["death"] = (df_copy["ma20"] < df_copy["ma60"]) & (df_copy["ma20"].shift(1) >= df_copy["ma60"].shift(1))

    latest_golden = df_copy[df_copy["golden"]]["date"].max() if df_copy["golden"].any() else None
    latest_death = df_copy[df_copy["death"]]["date"].max() if df_copy["death"].any() else None

    if close > ma20 > ma60:
        return "多头排列", "bullish"
    elif close < ma20 < ma60:
        return "空头排列", "bearish"
    elif ma20 > ma60:
        # 短期偏多，检查是否是刚金叉
        if latest_golden and (df["date"].iloc[-1] - latest_golden).days <= 3:
            return "金叉临界", "bullish"
        return "短期偏多", "bullish"
    else:
        if latest_death and (df["date"].iloc[-1] - latest_death).days <= 3:
            return "死叉临界", "bearish"
        return "短期偏空", "bearish"


def _determine_trend_local(close, ma20, ma60, df):
    """判断均线趋势状态（本地数据版本）"""
    if pd.isna(ma20) or pd.isna(ma60):
        return "数据不足", "neutral"

    df_copy = df.copy()
    df_copy["golden"] = (df_copy["ma20"] > df_copy["ma60"]) & (df_copy["ma20"].shift(1) <= df_copy["ma60"].shift(1))
    df_copy["death"] = (df_copy["ma20"] < df_copy["ma60"]) & (df_copy["ma20"].shift(1) >= df_copy["ma60"].shift(1))

    latest_golden = df_copy[df_copy["golden"]]["日期"].max() if df_copy["golden"].any() else None
    latest_death = df_copy[df_copy["death"]]["日期"].max() if df_copy["death"].any() else None

    if close > ma20 > ma60:
        return "多头排列", "bullish"
    elif close < ma20 < ma60:
        return "空头排列", "bearish"
    elif ma20 > ma60:
        if latest_golden is not None and (df["日期"].iloc[-1] - latest_golden).days <= 3:
            return "金叉临界", "bullish"
        return "短期偏多", "bullish"
    else:
        if latest_death is not None and (df["日期"].iloc[-1] - latest_death).days <= 3:
            return "死叉临界", "bearish"
        return "短期偏空", "bearish"


def _render_stock_cards(df):
    """渲染股票行情卡片网格"""
    st.markdown("### 📋 股票行情概览")

    cards_per_row = 3
    for i in range(0, len(df), cards_per_row):
        cols = st.columns(cards_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(df):
                break
            row = df.iloc[idx]
            with col:
                trend_icon = {"bullish": "🔴", "bearish": "🟢", "neutral": "🟡"}.get(
                    row.get("trend_class", "neutral"), "🟡"
                )
                change_color = "#ef5350" if row["change_pct"] >= 0 else "#26a69a"

                st.markdown(f"""
                <div style="border:1px solid #e0e0e0; border-radius:12px; padding:1rem; margin:0.3rem 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:bold; font-size:1.05rem;">{trend_icon} {row['name']}</span>
                        <span style="color:{change_color}; font-weight:bold;">{row['change_pct']:+.2f}%</span>
                    </div>
                    <div style="font-size:1.4rem; font-weight:bold; margin:0.3rem 0;">¥{row['close']}</div>
                    <div style="font-size:0.85rem; color:#888;">
                        MA20: ¥{row['ma20'] if row['ma20'] else 'N/A'} | MA60: ¥{row['ma60'] if row['ma60'] else 'N/A'}
                    </div>
                    <div style="font-size:0.85rem; margin-top:0.2rem;">
                        <span class="trend-{row.get('trend_class', 'neutral')}">{row['trend']}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#999; margin-top:0.2rem;">{row['code']}</div>
                    <div style="font-size:0.7rem; color:#bbb;">📅 {row.get('latest_date', '')}</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"📊 查看详情", key=f"detail_{idx}", use_container_width=True):
                    st.session_state.selected_stock_detail = row.to_dict()
                    st.rerun()


def _render_stock_detail(stock_info):
    """渲染单只股票的详细解读页面"""
    code = stock_info["code"]
    name = stock_info["name"]

    st.markdown(f"## 📈 {name}（{code}）详细解读")

    if st.button("← 返回行情面板"):
        st.session_state.selected_stock_detail = None
        st.rerun()

    st.markdown("---")

    # 获取完整日线数据用于绘图
    dm = DataManager()
    try:
        tx_code = dm._code_to_tx(code)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        df = ak.stock_zh_a_hist_tx(
            symbol=tx_code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
            timeout=10.0,
        )
        if df is None or df.empty:
            st.error("无法获取行情数据")
            return

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma60"] = df["close"].rolling(60).mean()

        # 检测交叉
        df["golden_cross"] = (df["ma20"] > df["ma60"]) & (df["ma20"].shift(1) <= df["ma60"].shift(1))
        df["death_cross"] = (df["ma20"] < df["ma60"]) & (df["ma20"].shift(1) >= df["ma60"].shift(1))

    except Exception as e:
        # 回退到本地数据
        st.warning(f"在线获取失败，使用本地数据：{e}")
        filepath = os.path.join(DATA_DIR, f"{code}.csv")
        if not os.path.exists(filepath):
            st.error("本地也无数据")
            return
        df = pd.read_csv(filepath, dtype={"日期": str})
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期").reset_index(drop=True)
        cutoff = datetime.now() - timedelta(days=365)
        df = df[df["日期"] >= pd.Timestamp(cutoff)]
        df = df.rename(columns={"日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low"})
        for c in ["close", "open", "high", "low"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma60"] = df["close"].rolling(60).mean()
        df["golden_cross"] = (df["ma20"] > df["ma60"]) & (df["ma20"].shift(1) <= df["ma60"].shift(1))
        df["death_cross"] = (df["ma20"] < df["ma60"]) & (df["ma20"].shift(1) >= df["ma60"].shift(1))

    # ==================== K线图 + 均线 + 信号 ====================
    _draw_detail_chart(df, name)

    # ==================== 行情解读 ====================
    st.markdown("### 🗣️ 行情解读")
    interpretation = _generate_interpretation(df, name, code)
    st.markdown(f'<div class="interpretation-box">{interpretation}</div>', unsafe_allow_html=True)

    # ==================== 信号工单 ====================
    _render_work_order(df, name, code)


def _draw_detail_chart(df, name):
    """绘制详情页K线图"""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.7, 0.3],
    )

    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线",
        increasing_line_color="#ef5350",
        decreasing_line_color="#26a69a",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["ma20"], mode="lines",
        name="MA20", line=dict(color="#1f77b4", width=2),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["ma60"], mode="lines",
        name="MA60", line=dict(color="#ff7f0e", width=2),
    ), row=1, col=1)

    # 金叉标注
    golden = df[df["golden_cross"]]
    if not golden.empty:
        fig.add_trace(go.Scatter(
            x=golden["date"], y=golden["low"] * 0.97,
            mode="markers+text",
            marker=dict(symbol="triangle-up", size=14, color="#e74c3c"),
            text=["🔺"] * len(golden),
            textposition="bottom center",
            name="金叉",
            hovertext=[f"金叉: {d.strftime('%Y-%m-%d')}<br>¥{c:.2f}"
                        for d, c in zip(golden["date"], golden["close"])],
            hoverinfo="text",
        ), row=1, col=1)

    # 死叉标注
    death = df[df["death_cross"]]
    if not death.empty:
        fig.add_trace(go.Scatter(
            x=death["date"], y=death["high"] * 1.03,
            mode="markers+text",
            marker=dict(symbol="triangle-down", size=14, color="#27ae60"),
            text=["🔻"] * len(death),
            textposition="top center",
            name="死叉",
            hovertext=[f"死叉: {d.strftime('%Y-%m-%d')}<br>¥{c:.2f}"
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
        title=f"<b>{name} - 近一年日K线图 + MA20/MA60 + 金叉死叉标注</b>",
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

    st.plotly_chart(fig, use_container_width=True)


def _generate_interpretation(df, name, code):
    """基于规则生成通俗易懂的行情解读文本"""
    latest = df.iloc[-1]
    close = latest["close"]
    ma20 = latest.get("ma20")
    ma60 = latest.get("ma60")
    latest_date = latest["date"].strftime("%Y-%m-%d")

    # 计算涨跌幅（与前一天比）
    if len(df) > 1:
        prev_close = df.iloc[-2]["close"]
        daily_change = (close - prev_close) / prev_close * 100
    else:
        daily_change = 0

    parts = [f"📅 数据日期：{latest_date}"]
    parts.append(f"💰 最新收盘价：¥{close:.2f}（当日{'上涨' if daily_change >= 0 else '下跌'}{abs(daily_change):.2f}%）")

    if pd.isna(ma20) or pd.isna(ma60):
        parts.append("\n⚠️ 均线数据不足，无法进行完整分析。建议积累更多交易日数据后再查看。")
        return "<br>".join(parts)

    parts.append(f"📊 MA20（20日均线）：¥{ma20:.2f}")
    parts.append(f"📊 MA60（60日均线）：¥{ma60:.2f}")

    # 趋势判断
    if close > ma20 > ma60:
        parts.append(f"\n✅ <b>当前状况：均线呈多头排列</b>，MA20在MA60上方，股价位于两条均线之上，属于<strong>强势上涨趋势</strong>。")
    elif close < ma20 < ma60:
        parts.append(f"\n⚠️ <b>当前状况：均线呈空头排列</b>，股价位于两条均线之下，属于<strong>下跌趋势</strong>。建议观望。")
    elif ma20 > ma60 and close < ma20:
        parts.append(f"\n📌 <b>当前状况：短期偏多</b>，MA20仍在MA60上方，但股价已跌破MA20，可能是短期回调。关注MA60支撑（¥{ma60:.2f}）。")
    else:
        parts.append(f"\n📌 <b>当前状况：短期偏空</b>，MA20在MA60下方。如果股价持续反弹并站上MA20（¥{ma20:.2f}），可能出现转机。")

    # 查找最近的金叉/死叉
    golden_dates = df[df["golden_cross"]]["date"]
    death_dates = df[df["death_cross"]]["date"]

    latest_golden = golden_dates.max() if not golden_dates.empty else None
    latest_death = death_dates.max() if not death_dates.empty else None

    if latest_golden is not None and not pd.isna(latest_golden):
        golden_row = df[df["date"] == latest_golden].iloc[0]
        golden_price = golden_row["close"]
        days_since = (df["date"].iloc[-1] - latest_golden).days
        if days_since >= 0:
            gain_since = (close - golden_price) / golden_price * 100 if golden_price > 0 else 0
            parts.append(f"\n🔺 <b>最近一次金叉</b>发生在 {latest_golden.strftime('%Y-%m-%d')}，当时收盘价 ¥{golden_price:.2f}，至今涨幅 <b>{gain_since:+.2f}%</b>。")

    if latest_death is not None and not pd.isna(latest_death):
        death_row = df[df["date"] == latest_death].iloc[0]
        death_price = death_row["close"]
        days_since = (df["date"].iloc[-1] - latest_death).days
        if days_since >= 0:
            change_since = (close - death_price) / death_price * 100 if death_price > 0 else 0
            parts.append(f"\n🔻 <b>最近一次死叉</b>发生在 {latest_death.strftime('%Y-%m-%d')}，当时收盘价 ¥{death_price:.2f}，至今变化 <b>{change_since:+.2f}%</b>。")

    # 策略建议
    parts.append("\n---")
    if ma20 > ma60 and close > ma20:
        parts.append(f"\n💡 <b>策略建议</b>：当前处于多头趋势，如果已持仓建议<strong>继续持有</strong>。下方支撑位关注MA20线 ¥{ma20:.2f}。若价格跌破MA20需警惕趋势转弱。")
    elif ma20 < ma60 and close < ma20:
        parts.append(f"\n💡 <b>策略建议</b>：当前处于空头趋势，建议<strong>空仓观望</strong>，等待金叉信号出现后再考虑入场。")
    else:
        parts.append(f"\n💡 <b>策略建议</b>：当前方向不明确，建议<strong>轻仓或观望</strong>，等待趋势明朗化。MA20(¥{ma20:.2f})和MA60(¥{ma60:.2f})之间的空间较小，可能即将选择方向。")

    # 检查最近是否刚发生金叉/死叉
    latest = df.iloc[-1]
    if latest.get("golden_cross") == True:
        parts.append(f"\n\n⚠️ <b>重要信号</b>：今日MA20已上穿MA60，形成<b>金叉买入信号</b>！这是明确的入场时机。下方有信号工单可供参考。")
    elif latest.get("death_cross") == True:
        parts.append(f"\n\n⚠️ <b>重要信号</b>：今日MA20已下穿MA60，形成<b>死叉卖出信号</b>！该股由多转空，建议注意风险。")

    return "<br>".join(parts)


def _render_work_order(df, name, code):
    """渲染信号工单"""
    latest = df.iloc[-1]

    # 检查最后一个交易日是否发生金叉
    is_golden_today = latest.get("golden_cross") == True
    # 也检查倒数第二个（有时最新数据延迟）
    if not is_golden_today and len(df) > 1:
        is_golden_today = df.iloc[-2].get("golden_cross") == True

    if not is_golden_today:
        st.info("📭 最近一个交易日未出现金叉信号，暂无需关注的买入工单。")
        return

    # 金叉当日的开盘价作为建议买入价参考
    if latest.get("golden_cross") == True:
        signal_row = latest
    else:
        signal_row = df.iloc[-2]

    close_price = signal_row["close"]
    ma20_val = signal_row.get("ma20", 0)
    ma60_val = signal_row.get("ma60", 0)
    signal_date = signal_row["date"].strftime("%Y-%m-%d")
    suggested_buy = round(float(close_price), 2)
    buy_low = round(suggested_buy * 0.99, 2)
    buy_high = round(suggested_buy * 1.01, 2)

    st.markdown(f"""
    <div class="work-order">
    <h3>🔔 关注买入信号工单</h3>
    <table style="width:100%; border-collapse:collapse;">
        <tr>
            <td style="padding:8px; font-weight:bold; width:30%;">📌 股票代码</td>
            <td style="padding:8px;">{code}</td>
        </tr>
        <tr>
            <td style="padding:8px; font-weight:bold;">🏷️ 股票名称</td>
            <td style="padding:8px;">{name}</td>
        </tr>
        <tr>
            <td style="padding:8px; font-weight:bold;">📡 信号类型</td>
            <td style="padding:8px; color:#e74c3c; font-weight:bold;">20日上穿60日（金叉）</td>
        </tr>
        <tr>
            <td style="padding:8px; font-weight:bold;">📅 信号日期</td>
            <td style="padding:8px;">{signal_date}</td>
        </tr>
        <tr>
            <td style="padding:8px; font-weight:bold;">💰 信号时收盘价</td>
            <td style="padding:8px;">¥{close_price:.2f}</td>
        </tr>
        <tr>
            <td style="padding:8px; font-weight:bold;">📊 快线 MA20</td>
            <td style="padding:8px;">¥{ma20_val:.2f}</td>
        </tr>
        <tr>
            <td style="padding:8px; font-weight:bold;">📊 慢线 MA60</td>
            <td style="padding:8px;">¥{ma60_val:.2f}</td>
        </tr>
        <tr>
            <td style="padding:8px; font-weight:bold;">🎯 建议观察买入价区间</td>
            <td style="padding:8px; color:#e74c3c; font-weight:bold; font-size:1.1rem;">¥{buy_low} ~ ¥{buy_high}</td>
        </tr>
        <tr>
            <td style="padding:8px; font-weight:bold;">📝 操作提示</td>
            <td style="padding:8px; font-size:0.9rem;">建议在次日开盘价 ±1% 范围内观察入场。注意T+1限制，买入后最早次个交易日才能卖出。</td>
        </tr>
    </table>
    </div>
    """, unsafe_allow_html=True)

    # 导出按钮
    work_order_data = {
        "股票代码": code,
        "股票名称": name,
        "信号类型": "20日上穿60日（金叉）",
        "信号日期": signal_date,
        "信号时收盘价": f"¥{close_price:.2f}",
        "MA20": f"¥{ma20_val:.2f}",
        "MA60": f"¥{ma60_val:.2f}",
        "建议观察买入价区间": f"¥{buy_low} ~ ¥{buy_high}",
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    col1, col2 = st.columns(2)
    with col1:
        json_str = json.dumps(work_order_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 导出为 JSON",
            data=json_str,
            file_name=f"signal_{code}_{signal_date}.json",
            mime="application/json",
            use_container_width=True, )
    with col2:
        txt_str = "\n".join(f"{k}: {v}" for k, v in work_order_data.items())
        st.download_button(
            label="📄 导出为 TXT",
            data=txt_str,
            file_name=f"signal_{code}_{signal_date}.txt",
            mime="text/plain",
            use_container_width=True, )
