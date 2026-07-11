"""
量化交易知识库 - knowledge_base.py
==================================
交互式知识词典，按类别折叠展示量化交易核心概念。
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render_knowledge_base():
    """渲染量化交易知识库主页面"""

    st.markdown("""
    <style>
    .knowledge-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1rem;
    }
    .term-box {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin: 0.5rem 0;
    }
    .example-box {
        background: #fff3cd;
        border: 1px solid #ffc107;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="knowledge-card">
    <h2>📖 量化交易知识库</h2>
    <p>从市场基础到策略逻辑，像翻词典一样学习量化交易核心概念。</p>
    </div>
    """, unsafe_allow_html=True)

    # ==================== 一、市场基础 ====================
    st.markdown("---")
    st.header("🏦 一、市场基础")

    # 1.1 OHLCV 与 K线
    with st.expander("📊 OHLCV是什么？如何看懂一根K线？", expanded=False):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("""
            ### OHLCV 五要素
            - **O (Open 开盘价)**：交易日第一笔成交价格
            - **H (High 最高价)**：当日最高成交价格
            - **L (Low 最低价)**：当日最低成交价格
            - **C (Close 收盘价)**：交易日最后一笔成交价格
            - **V (Volume 成交量)**：当日成交的股票数量（单位：手，1手=100股）

            ### 阳线 vs 阴线
            - **阳线（红色）**：收盘价 > 开盘价，表示当日上涨
            - **阴线（绿色）**：收盘价 < 开盘价，表示当日下跌

            ### 一根K线包含的信息
            从一根K线可以读出：当日多空力量对比、价格波动范围、市场情绪方向。
            实体越长，趋势越强；影线越长，分歧越大。
            """)
        with col2:
            # 画一根K线示意图
            _draw_candlestick_demo()

    # 1.2 复权
    with st.expander("🔄 什么是复权？前复权、后复权的区别与用途", expanded=False):
        st.markdown("""
        ### 为什么需要复权？
        股票在发生**分红、送股、配股**等事件时，股价会出现跳空缺口。
        这个缺口不是市场交易造成的，而是"除权除息"处理的结果。
        如果不做复权处理，K线图上会出现"假缺口"，影响技术分析。
        """)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            #### 📌 前复权（常用）
            - **做法**：保持最新价格不变，向前调整历史价格
            - **效果**：历史价格被"压低"，K线连续平滑
            - **用途**：技术分析、策略回测、看趋势
            - **优点**：最新价格就是真实市价
            - **缺点**：历史价格不是真实成交价
            """)
        with col2:
            st.markdown("""
            #### 📌 后复权
            - **做法**：保持上市首日价格不变，向后调整后续价格
            - **效果**：后续价格被"抬高"，能看到真实涨幅
            - **用途**：计算长期投资收益率
            - **优点**：能看到股票从上市至今的真实涨幅
            - **缺点**：当前价格不是真实市价
            """)

        st.info(
            "💡 **QuantSeed使用前复权数据**进行回测，因为我们需要最新的真实市价来做交易决策。"
        )

        # 复权对比示意图
        _draw_adjust_demo()

    # 1.3 A股交易规则
    with st.expander("📜 A股基本交易规则", expanded=False):
        st.markdown("""
        | 规则 | 说明 |
        |------|------|
        | **T+1 制度** | 当天买入的股票，下一个交易日才能卖出。这防止了日内过度投机。 |
        | **涨跌停限制** | 主板 ±10%（ST股 ±5%），创业板/科创板 ±20%。涨跌停价内可正常交易。 |
        | **交易单位** | 买入必须是100股（1手）的整数倍，卖出可以不足1手。 |
        | **交易时间** | 9:30-11:30（上午），13:00-15:00（下午）。9:15-9:25为集合竞价。 |
        | **手续费** | 券商佣金（约万2.5）+ 印花税（卖出时千1）+ 过户费。 |
        | **最小变动** | 0.01元/股。 |

        > ⚠️ **对策略的影响**：T+1意味着金叉信号出现当天买入，最快第二天才能卖出。
        > QuantSeed在回测中已模拟T+1延迟（`set_coc(True)`），使用次日开盘价成交。
        """)

    # ==================== 二、核心术语 ====================
    st.markdown("---")
    st.header("📝 二、核心术语")

    # 2.1 趋势类
    with st.expander("📈 趋势类术语", expanded=False):
        tab_a, tab_b, tab_c, tab_d = st.tabs([
            "金叉", "死叉", "多头排列", "空头排列"
        ])

        with tab_a:
            st.markdown("""
            ### 🔺 金叉 (Golden Cross)
            **定义**：短期均线从下方向上穿过长期均线。

            **通俗理解**：就像一辆快车（短期均线）从后面追上了慢车（长期均线）并超车，
            说明近期价格在加速上涨，市场由弱转强。

            **QuantSeed中的金叉**：MA20（20日均线）上穿 MA60（60日均线）

            **示例计算**：
            ```
            昨天: MA20 = 10.20, MA60 = 10.25  → MA20 < MA60（空头）
            今天: MA20 = 10.30, MA60 = 10.27  → MA20 > MA60（多头）
            判断: 发生金叉！短期趋势转强。
            ```
            """)

        with tab_b:
            st.markdown("""
            ### 🔻 死叉 (Death Cross)
            **定义**：短期均线从上方向下穿过长期均线。

            **通俗理解**：快车减速了，被慢车反超，说明价格上涨乏力，市场由强转弱。

            **交易意义**：死叉是卖出/止损信号。在QuantSeed的双均线策略中，
            金叉买入、死叉卖出。

            **示例计算**：
            ```
            昨天: MA20 = 10.30, MA60 = 10.27  → MA20 > MA60（多头）
            今天: MA20 = 10.22, MA60 = 10.26  → MA20 < MA60（空头）
            判断: 发生死叉！建议卖出。
            ```
            """)

        with tab_c:
            st.markdown("""
            ### 🔼 多头排列
            **定义**：短期均线在长期均线上方，且股价在短期均线上方。
            即：**收盘价 > MA20 > MA60**

            **市场含义**：多头完全主导，上涨趋势健康且强劲。这是最理想的持仓状态。

            **可视化**：
            ```
            价格层级（从上到下）:
            ════════  收盘价 15.50（最上面，最强势）
            ────────  MA20   14.80
            ········  MA60   13.20（最下面）
            ```
            """)

        with tab_d:
            st.markdown("""
            ### 🔽 空头排列
            **定义**：短期均线在长期均线下方，且股价在短期均线下方。
            即：**收盘价 < MA20 < MA60**

            **市场含义**：空头完全主导，下跌趋势持续。此时应空仓观望。

            **可视化**：
            ```
            价格层级（从上到下）:
            ········  MA60   13.20（最上面）
            ────────  MA20   12.50
            ════════  收盘价 11.80（最下面，最弱势）
            ```
            """)

    # 2.2 形态类
    with st.expander("🏔️ 形态类术语", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            #### 🧱 支撑位 (Support)
            价格下跌过程中遇到的"地板"——买方力量增强，阻止价格继续下跌。
            均线（如MA20、MA60）常充当动态支撑位。
            """)
            st.markdown("""
            #### 🔒 阻力位 (Resistance)
            价格上涨过程中遇到的"天花板"——卖方力量增强，阻止价格继续上涨。
            前期高点、整数关口常充当阻力位。
            """)
        with col2:
            st.markdown("""
            #### 🚀 突破 (Breakout)
            价格有效穿过重要的阻力位或支撑位，通常伴随成交量放大。
            突破阻力位是买入信号，跌破支撑位是卖出信号。
            """)
            st.markdown("""
            #### ↩️ 回踩 (Pullback)
            价格突破后小幅回落，测试突破位置（原阻力变支撑）。
            回踩不破是确认信号，回踩破位则可能是假突破。
            """)

    # 2.3 风险评价
    with st.expander("⚖️ 风险评价指标", expanded=False):
        st.markdown("""
        #### 📉 最大回撤 (Max Drawdown)
        **定义**：在选定周期内，账户净值从最高点到最低点的最大跌幅。

        **通俗理解**：如果你运气最差，在最高点买入最低点卖出，会亏多少。

        **计算公式**：`MaxDD = (峰值 - 谷值) / 峰值`

        <div class="example-box">
        <b>示例</b>：账户从100万涨到150万（峰值），然后跌到90万（谷值）<br>
        最大回撤 = (150-90)/150 = <b>40%</b><br>
        这意味着策略在极端情况下可能亏损40%！回撤越大，策略风险越高。
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 📊 夏普比率 (Sharpe Ratio)
        **定义**：每承担一单位风险，能获得多少超额回报。

        **通俗理解**：你的收益是靠"本事"赚的还是靠"运气"冒风险换来的？
        夏普比率越高，说明策略越"聪明"。

        **计算公式**：`Sharpe = (年化收益 - 无风险利率) / 年化波动率`

        <div class="example-box">
        <b>参考标准</b>：<br>
        &lt; 0：不如存银行<br>
        0~0.5：收益尚可，但风险较大<br>
        0.5~1.0：还不错<br>
        1.0~2.0：优秀<br>
        &gt; 2.0：卓越（但要警惕过拟合）
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 🎯 胜率 (Win Rate)
        **定义**：盈利交易次数占总交易次数的比例。

        **注意**：高胜率不一定意味着赚钱！如果每次赚1块但亏10块，90%胜率也会亏损。
        胜率必须配合盈亏比来看。

        #### 💰 盈亏比 (Profit Factor)
        **定义**：平均盈利金额 / 平均亏损金额。

        **公式**：`盈亏比 = 总盈利 / |总亏损|`

        <div class="example-box">
        <b>示例</b>：<br>
        10次交易，6次盈利共赚1200元，4次亏损共亏400元<br>
        胜率 = 60% | 盈亏比 = 1200/400 = <b>3.0</b><br>
        这个策略低胜率但高盈亏比，靠"截断亏损、让利润奔跑"赚钱。
        </div>
        """, unsafe_allow_html=True)

    # ==================== 三、策略逻辑 ====================
    st.markdown("---")
    st.header("🧠 三、策略逻辑")

    with st.expander("🔍 双均线策略详解：赚趋势的钱", expanded=False):
        st.markdown("""
        ### 核心理念
        双均线策略属于**趋势跟踪策略**。它的底层逻辑很简单：

        > 📈 **市场有惯性**——一旦趋势形成，它往往会持续一段时间。
        > 我们要做的就是：趋势来了跟上，趋势走了离开。

        ### 交易规则（QuantSeed实现）
        - **买入信号**：MA20 上穿 MA60（金叉），全仓买入
        - **卖出信号**：MA20 下穿 MA60（死叉），全仓卖出
        - **仓位管理**：95%仓位买入（留5%现金防手续费）
        - **交易延迟**：T+1 模拟，信号出现后次日在开盘价成交

        ### 为什么在震荡市会失效？
        震荡市中，价格在区间内反复波动，MA20和MA60频繁交叉。
        策略会不断发出买入-卖出信号，产生大量"假突破"：

        ```
        震荡市典型表现：
        金叉买入 → 价格没涨反而跌 → 死叉卖出 → 亏损
        死叉卖出 → 价格没跌反而涨 → 金叉买入 → 追高
        反复被"打脸"，手续费不断累积 ← 这就是震荡市的"磨损"
        ```

        **解决方案（第二阶段）**：
        - 增加趋势过滤器（如ADX指标，只在强趋势市交易）
        - 增加成交量确认（金叉需放量才有效）
        - 多时间框架验证（日线金叉 + 周线多头排列）
        """)

        # 震荡市示意图
        _draw_choppy_market_demo()

    with st.expander("🌐 延伸阅读：其他策略思想", expanded=False):
        st.markdown("""
        #### 🔄 均值回归 (Mean Reversion)
        **思想**：价格会围绕一个"均值"上下波动，偏离太远就会回归。
        就像弹簧，拉太远会弹回来。

        **典型策略**：布林带策略——价格触及下轨买入，触及上轨卖出。
        **适用场景**：震荡市效果好，趋势市容易被套。

        ---

        #### 🚀 动量效应 (Momentum)
        **思想**：近期涨得好的股票，未来一段时间会继续涨；近期跌的会继续跌。
        "强者恒强，弱者恒弱"。

        **典型策略**：买入过去N个月涨幅最大的股票，持有一段时间后轮换。
        **适用场景**：趋势市效果好，市场转折点容易回撤。

        ---

        #### 🧩 因子投资 (Factor Investing)
        **思想**：股票收益可以由少数几个"因子"来解释，如：
        - **价值因子**：买便宜的（低市盈率、低市净率）
        - **规模因子**：小盘股长期收益高于大盘股
        - **质量因子**：买盈利好、负债低的公司
        - **动量因子**：买近期表现好的

        **代表**：Fama-French 三因子/五因子模型。
        QuantSeed 第二阶段可引入多因子选股。
        """)


# ==================== 辅助绘图函数 ====================

def _draw_candlestick_demo():
    """画K线结构示意"""
    # 阳线数据
    fig = go.Figure()

    # 画一根阳线（矩形实体）
    # 阳线: O=10, C=12, H=13, L=9
    fig.add_trace(go.Bar(
        x=["今日"], y=[2], base=[10],  # 实体从10到12
        marker_color="#ef5350", name="阳线实体",
        width=0.3,
    ))
    # 上影线
    fig.add_shape(type="line", x0="今日", x1="今日", y0=12, y1=13,
                  line=dict(color="#ef5350", width=1.5))
    # 下影线
    fig.add_shape(type="line", x0="今日", x1="今日", y0=9, y1=10,
                  line=dict(color="#ef5350", width=1.5))
    # 最高价标记
    fig.add_annotation(x="今日", y=13.3, text="H=13.00", showarrow=False, font=dict(size=10, color="#666"))
    # 收盘价标记
    fig.add_annotation(x="今日", y=12.3, text="C=12.00 ▲", showarrow=False, font=dict(size=10, color="#ef5350"))
    # 开盘价标记
    fig.add_annotation(x="今日", y=9.7, text="O=10.00", showarrow=False, font=dict(size=10, color="#666"))
    # 最低价标记
    fig.add_annotation(x="今日", y=8.7, text="L=9.00", showarrow=False, font=dict(size=10, color="#666"))

    fig.update_layout(
        title="<b>K线结构示意（阳线）</b>",
        height=350,
        yaxis_title="价格 (元)",
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_range=[8, 14],
    )
    fig.update_yaxes(gridcolor="#eee")

    st.plotly_chart(fig, width="stretch")


def _draw_adjust_demo():
    """画复权对比示意"""
    dates = pd.date_range("2023-01-01", periods=5, freq="ME")
    # 模拟：第3期发生10送10（1拆2）
    raw_price = [20, 22, 24, 12, 13]  # 除权后价格腰斩
    forward_adj = [10, 11, 12, 12, 13]  # 前复权：历史价格减半
    backward_adj = [20, 22, 24, 24, 26]  # 后复权：除权后价格翻倍

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=raw_price, mode="lines+markers",
                              name="不复权（有缺口）", line=dict(color="gray", dash="dash")))
    fig.add_trace(go.Scatter(x=dates, y=forward_adj, mode="lines+markers",
                              name="前复权（推荐）", line=dict(color="#1f77b4", width=2.5)))
    fig.add_trace(go.Scatter(x=dates, y=backward_adj, mode="lines+markers",
                              name="后复权", line=dict(color="#ff7f0e", width=2)))

    fig.update_layout(
        title="<b>复权对比示意图</b>（第3期发生10送10除权）",
        height=300,
        hovermode="x unified",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_yaxes(title="价格 (元)", gridcolor="#eee")
    fig.update_xaxes(title="日期")
    st.plotly_chart(fig, width="stretch")


def _draw_choppy_market_demo():
    """画震荡市假信号示意"""
    np.random.seed(42)
    n = 80
    dates = pd.date_range("2024-01-01", periods=n)
    # 模拟震荡行情
    price = 10 + np.cumsum(np.random.randn(n) * 0.15)
    # 拉回10附近
    price = 10 + (price - np.mean(price)) * 0.3
    ma20 = pd.Series(price).rolling(20).mean()
    ma60 = pd.Series(price).rolling(60).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=price, mode="lines",
                              name="收盘价", line=dict(color="#333", width=1.5)))
    fig.add_trace(go.Scatter(x=dates, y=ma20, mode="lines",
                              name="MA20", line=dict(color="#1f77b4", width=1.5)))
    fig.add_trace(go.Scatter(x=dates, y=ma60, mode="lines",
                              name="MA60", line=dict(color="#ff7f0e", width=1.5)))

    # 标记假金叉位置
    cross_dates = [dates[25], dates[45], dates[65]]
    for i, d in enumerate(cross_dates):
        fig.add_annotation(x=d, y=price[list(dates).index(d)] + 0.4,
                           text="❌ 假金叉", showarrow=True, arrowhead=1,
                           font=dict(color="red", size=11))

    fig.update_layout(
        title="<b>震荡市中的假信号</b>（价格反复穿越均线，产生无效交易）",
        height=300,
        hovermode="x unified",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_yaxes(title="价格", gridcolor="#eee")
    st.plotly_chart(fig, width="stretch")
