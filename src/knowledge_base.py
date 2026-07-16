"""
量化交易知识库 - knowledge_base.py
==================================
交互式知识词典，按类别折叠展示量化交易核心概念。
内容整理自 quant-wiki.com 等公开量化百科。
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


# ==================== 数据：术语库 ====================
# 用结构化数据+渲染函数混合展示，便于后续扩展

TERM_LIBRARY = {
    "订单类型": {
        "市价单 (Market Order)": "按当前市场最优价立即成交，优点是成交快，缺点是在波动大时可能滑点严重。",
        "限价单 (Limit Order)": "指定价格或更优价格成交。买入限价单 ≤ 指定价，卖出限价单 ≥ 指定价。未成交则挂单等待。",
        "止损单 (Stop Loss)": "当价格触及触发价时转为市价单卖出，用于控制亏损。触发价通常设在买入价下方。",
        "止盈单 (Take Profit)": "当价格达到目标盈利价时自动卖出，锁定利润。",
        "IOC (Immediate or Cancel)": "立即成交剩余撤销，不能立即成交的部分自动撤单。",
        "FOK (Fill or Kill)": "全部成交或全部撤销，常用于大额订单。",
        "冰山订单 (Iceberg)": "大额订单拆分成多笔小单逐步暴露，隐藏真实交易量。",
        "TWAP/VWAP 算法单": "时间加权/成交量加权平均价算法拆单，降低市场冲击成本。",
    },
    "常用缩写": {
        "P&L": "盈亏 (Profit & Loss)",
        "MTM": "按市价计价 (Mark-to-Market)",
        "AUM": "资产管理规模 (Assets Under Management)",
        "HFT": "高频交易 (High Frequency Trading)",
        "MM": "做市商 (Market Maker)",
        "PB": "主经纪商/Prime Brokerage",
        "DMA": "直接市场准入 (Direct Market Access)",
        "EMS": "订单执行管理系统 (Execution Management System)",
        "OMS": "订单管理系统 (Order Management System)",
        "T+0 / T+1": "T+0当天可买卖，T+1买入次日才能卖出",
        "ETF": "交易型开放式指数基金",
        "LOF": "上市开放式基金",
        "QFII": "合格境外机构投资者",
        "RQFII": "人民币合格境外机构投资者",
        "IPO": "首次公开发行",
        "FICC": "固定收益、外汇与大宗商品业务",
    },
    "行业黑话": {
        "画图": "形容价格走势按某种形态发展，也常调侃技术分析像是在画图形。",
        "接盘": "在高位买入别人卖出的筹码，后续下跌被套。",
        "站岗": "高位买入后长期持股，亏损严重。",
        "割肉": "亏损卖出，止损离场。",
        "打板": "追涨停板买入，常见于短线交易。",
        "核按钮": "开盘即大单砸盘，价格快速跌停。",
        "柚子": "游资、市场短线大资金玩家。",
        "北向资金": "通过沪股通/深股通进入 A 股的香港及海外资金。",
        "南向资金": "内地投资者通过港股通投资港股。",
        "国家队": "指社保基金、中央汇金等具有官方背景的长期资金。",
        "量化私募": "以量化策略为主的私募证券投资基金。",
        "指数增强": "在跟踪指数基础上通过选股/择时获取超额收益。",
        "绝对收益": "追求正收益而非相对排名，常见于对冲基金。",
    },
}


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

    with st.expander("📊 OHLCV 是什么？如何看懂一根 K 线？"):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("""
            ### OHLCV 五要素
            - **O (Open 开盘价)**：交易日第一笔成交价格
            - **H (High 最高价)**：当日最高成交价格
            - **L (Low 最低价)**：当日最低成交价格
            - **C (Close 收盘价)**：当日最后一笔成交价格
            - **V (Volume 成交量)**：当日成交股数（A股通常以“手”计，1手=100股）

            ### 阳线 vs 阴线
            - **阳线（红色）**：收盘价 > 开盘价，表示上涨
            - **阴线（绿色）**：收盘价 < 开盘价，表示下跌

            ### 实体与影线
            - 实体越长，说明多空力量差距越大
            - 上影线长，表示上方抛压重；下影线长，表示下方支撑强
            """)
        with col2:
            _draw_candlestick_demo()

    with st.expander("🔄 前复权 vs 后复权：区别与用途"):
        st.markdown("""
        股票分红、送股、配股后股价会“除权除息”，形成非市场跳空。复权就是把这些缺口补回去，让K线连续。

        | 类型 | 做法 | 用途 | 优点 | 缺点 |
        |------|------|------|------|------|
        | 前复权 | 最新价不变，向前调整历史价 | 技术分析、策略回测 | 当前价真实 | 历史价非真实成交价 |
        | 后复权 | 上市首日价不变，向后调整 | 长期收益率计算 | 真实涨幅 | 当前价非市价 |

        > 💡 **QuantSeed 回测使用前复权数据**，确保交易决策基于真实市价。
        """)
        _draw_adjust_demo()

    with st.expander("📜 A 股基本交易规则"):
        st.markdown("""
        | 规则 | 说明 |
        |------|------|
        | **T+1** | 当天买入次日才能卖出 |
        | **涨跌停** | 主板 ±10%，ST ±5%，创业板/科创板 ±20% |
        | **交易单位** | 买入须为100股整数倍，卖出可零股 |
        | **交易时间** | 9:30-11:30，13:00-15:00；9:15-9:25 集合竞价 |
        | **手续费** | 佣金（约万2.5）+ 卖出印花税千1 + 过户费 |
        | **最小变动** | 0.01 元 |

        > ⚠️ 对策略影响：T+1 意味着金叉当天买入，最快次日开盘才能卖出。QuantSeed 回测已模拟该延迟。
        """)

    with st.expander("🌐 一级市场、二级市场与常见市场结构"):
        st.markdown("""
        - **一级市场**：新股/债券首次发行（IPO、定增），投资者向发行人购买。
        - **二级市场**：已发行证券在交易所买卖，价格由供需决定。
        - **主板/创业板/科创板/北交所**：A股不同上市板块，准入门槛、涨跌幅、投资者门槛不同。
        - **集合竞价 vs 连续竞价**：开盘/收盘用集合竞价撮合，盘中用连续竞价逐笔成交。
        - **牛市 / 熊市**：市场整体上涨/下跌的周期阶段。
        """)

    # ==================== 二、核心术语 ====================
    st.markdown("---")
    st.header("📝 二、核心术语")

    with st.expander("📈 趋势类术语"):
        tab_a, tab_b, tab_c, tab_d = st.tabs(["金叉", "死叉", "多头排列", "空头排列"])
        with tab_a:
            st.markdown("""
            ### 金叉 (Golden Cross)
            短期均线从下向上穿过长期均线，视为趋势转强信号。
            
            **QuantSeed 中**：MA20 上穿 MA60 即触发买入信号。
            
            **示例**：昨天 MA20=10.20、MA60=10.25；今天 MA20=10.30、MA60=10.27 → 金叉。
            """)
        with tab_b:
            st.markdown("""
            ### 死叉 (Death Cross)
            短期均线从上向下穿过长期均线，视为趋势走弱信号。
            
            **QuantSeed 中**：MA20 下穿 MA60 即触发卖出/平仓信号。
            """)
        with tab_c:
            st.markdown("""
            ### 多头排列
            短、中、长期均线依次从上到下排列（如 MA5 > MA20 > MA60），说明上涨动能健康。
            """)
        with tab_d:
            st.markdown("""
            ### 空头排列
            短、中、长期均线依次从下到上排列（如 MA5 < MA20 < MA60），说明下跌趋势占据主导。
            """)

    with st.expander("🕯️ K 线形态术语"):
        st.markdown("""
        | 形态 | 含义 |
        |------|------|
        | **锤子线** | 长下影线、短实体，出现在下跌末端可能反转向上 |
        | **十字星** | 开收价接近，多空平衡，可能变盘 |
        | **吞没形态** | 后一根K线实体完全包住前一根，强势反转信号 |
        | **早晨之星 / 黄昏之星** | 三根K线组合，分别暗示底部/顶部反转 |
        | **头肩顶/底** | 经典反转形态，确认颈线突破后趋势大概率改变 |
        """)

    with st.expander("📊 风险评价指标"):
        st.markdown("""
        ### 夏普比率 (Sharpe Ratio)
        衡量每承担一单位总风险所获得的超额收益。
        $$\\text{Sharpe} = \\frac{R_p - R_f}{\\sigma_p}$$
        - 通常 > 1 可接受，> 2 优秀，> 3 非常优秀。

        ### 最大回撤 (Max Drawdown)
        从最高点到最低点的跌幅，反映策略最坏情况。
        $$\\text{MDD} = \\max\\frac{Peak - Trough}{Peak}$$

        ### 胜率 (Win Rate)
        盈利交易次数 / 总交易次数。高胜率不代表盈利，还需结合盈亏比。

        ### 盈亏比 (Profit Factor)
        总盈利 / 总亏损。> 1 代表策略整体盈利，> 2 较稳健。

        ### 信息比率 (Information Ratio)
        超额收益 / 跟踪误差，衡量主动管理能力。

        ### 索提诺比率 (Sortino Ratio)
        与夏普类似，但只用下行波动率作为分母，更关注亏损风险。

        ### 卡玛比率 (Calmar Ratio)
        年化收益 / 最大回撤，衡量收益与极端风险的性价比。
        """)

    with st.expander("🔑 Alpha / Beta / 其他核心概念"):
        st.markdown("""
        - **Alpha（超额收益）**：超越市场基准的收益，是量化策略追求的核心目标。
        - **Beta（市场风险敞口）**：相对于市场的波动敏感度。Beta=1 表示与市场同涨同跌。
        - **Smart Beta**：通过规则化方式获取传统市值加权指数之外的因子暴露。
        - **因子 (Factor)**：能解释资产收益差异的持续性特征，如价值、动量、质量、低波动。
        - **IC (Information Coefficient)**：预测收益与实际收益的秩相关系数，衡量因子预测能力。
        - **IR (Information Ratio)**：IC 的均值 / 标准差，衡量因子稳定性。
        - **换手率 (Turnover)**：组合资产更换频率，高换手意味着高交易成本。
        - **拥挤度 (Crowding)**：同一策略被市场大量采用，可能导致因子失效或回撤加剧。
        """)

    # ==================== 三、策略逻辑 ====================
    st.markdown("---")
    st.header("🧠 三、策略逻辑")

    with st.expander("🌱 QuantSeed 双均线策略详解"):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("""
            ### 策略思想
            利用短期均线与长期均线的相对位置判断趋势：
            - 短线上穿长线 → 买入（金叉）
            - 短线下穿长线 → 卖出（死叉）

            ### 参数
            - 快线：MA20（20日均线）
            - 慢线：MA60（60日均线）
            - 仓位：满仓买入/卖出
            - 手续费：默认万 2.5

            ### 适用场景
            趋势明显的市场。震荡市会产生较多假信号，导致连续亏损。
            """)
        with col2:
            _draw_ma_cross_demo()

    with st.expander("⚠️ 双均线策略的缺陷与改进思路"):
        st.markdown("""
        #### 主要缺陷
        1. **滞后性**：均线基于历史价格，信号总是慢于价格启动。
        2. **震荡市假信号**：价格反复穿越均线，产生频繁小额亏损。
        3. **单一品种风险**：未分散持仓，单一股票黑天鹅会放大回撤。
        4. **未控制仓位**：满仓进出波动大。

        #### 改进思路
        - 加入趋势过滤器（如 ADX、大盘指数方向）
        - 多品种组合，降低单一风险
        - 引入波动率/风险平价仓位管理
        - 加入止损止盈规则
        - 使用指数移动平均 EMA 替代 SMA 提高灵敏度
        """)
        _draw_choppy_market_demo()

    with st.expander("🗂️ 常见量化策略类型"):
        st.markdown("""
        | 策略类型 | 核心逻辑 | 适用市场 |
        |----------|----------|----------|
        | **趋势跟踪** | 顺势而为，买强卖弱 | 趋势明显市场 |
        | **均值回归** | 价格偏离均值后回归 | 震荡市场 |
        | **动量策略** | 强者恒强，买入近期赢家 | 牛市/上升期 |
        | **因子投资** | 基于价值、质量、低波动等因子选股 | 中长期 |
        | **统计套利** | 配对交易、协整关系 | 震荡/相关性强市场 |
        | **市场中性** | 同时做多和做空，对冲市场风险 | 熊市/震荡市 |
        | **CTA** | 商品期货趋势/期限结构策略 | 商品、期货市场 |
        | **高频交易 (HFT)** | 利用微观结构、速度优势 | 高流动性市场 |
        | **事件驱动** | 财报、并购、分红、政策事件 | 事件窗口期 |
        | **GAA 全球资产配置** | 跨资产类别、跨市场配置 | 大类资产 |
        | **QEMN 质量-动量-低波动** | 综合多因子选股 | 股票池 |
        """)

    # ==================== 四、交易术语 ====================
    st.markdown("---")
    st.header("💼 四、交易术语")

    with st.expander("🛒 订单类型与执行方式"):
        for term, desc in TERM_LIBRARY["订单类型"].items():
            st.markdown(f"**{term}**：{desc}")

    with st.expander("⚖️ 做多、做空、杠杆与保证金"):
        st.markdown("""
        - **做多 (Long)**：先买入后卖出，赚取上涨差价。
        - **做空 (Short)**：先借入卖出后买回，赚取下跌差价。A股普通股票做空受限，需通过融券或股指期货实现。
        - **杠杆 (Leverage)**：用较少的自有资金控制更大头寸，放大收益也放大风险。
        - **保证金 (Margin)**：开仓或持仓所需最低资金，维持保证金不足会触发强制平仓。
        - **爆仓**：亏损超过保证金，仓位被强制平仓。
        - **穿仓**：亏损超过保证金甚至倒欠资金。
        """)

    with st.expander("🛑 止损、止盈与仓位管理"):
        st.markdown("""
        - **止损 (Stop Loss)**：预先设定最大可承受亏损，价格触及即平仓。
        - **止盈 (Take Profit)**：达到目标盈利后平仓，避免利润回吐。
        - **固定比例止损**：如亏损达到本金的 2% 离场。
        - **ATR 止损**：根据真实波动幅度动态设置止损距离。
        - **仓位管理**：决定每次投入多少资金。常见方法：固定金额、固定比例、凯利公式、风险平价。
        """)

    with st.expander("📉 滑点、冲击成本与交易成本"):
        st.markdown("""
        - **滑点 (Slippage)**：下单价格与实际成交价之间的差异，流动性差或波动大时更明显。
        - **冲击成本 (Market Impact)**：大额订单本身推动价格向不利方向移动。
        - **佣金 (Commission)**：券商收取的交易手续费。
        - **印花税**：A股卖出时按成交金额千分之一征收。
        - **机会成本**：因未成交或部分成交而错失的交易机会。
        """)

    # ==================== 五、技术指标 ====================
    st.markdown("---")
    st.header("📈 五、技术指标")

    with st.expander("📊 趋势类指标"):
        st.markdown("""
        | 指标 | 说明 | 常用信号 |
        |------|------|----------|
        | **MA / SMA** | 简单移动平均 | 价格上穿均线买入，下穿卖出 |
        | **EMA** | 指数移动平均，对近期价格更敏感 | 与 MA 类似 |
        | **MACD** | 快线(12)减慢线(26)，再加信号线(9) | DIF 上穿 DEA 买入；MACD 柱由负转正 |
        | **布林带 (Bollinger Bands)** | 中轨 MA ± 2 倍标准差 | 触及下轨可能超卖，触及上轨可能超买 |
        | **ADX** | 平均趋向指数 | ADX>25 表示趋势强，<20 表示震荡 |
        | **DMI** | 动向指标 | +DI 上穿 -DI 看多，反之看空 |
        """)

    with st.expander("🌡️ 震荡类指标"):
        st.markdown("""
        | 指标 | 说明 | 常用信号 |
        |------|------|----------|
        | **RSI** | 相对强弱指数 | RSI>70 超买，<30 超卖 |
        | **KDJ** | 随机指标 | K 上穿 D 金叉，下穿死叉 |
        | **CCI** | 商品通道指标 | 上穿 +100 强势，下穿 -100 弱势 |
        | **威廉指标 %R** | 与 RSI 类似 | 0~-20 超买，-80~-100 超卖 |
        """)

    with st.expander("📦 成交量与资金流指标"):
        st.markdown("""
        | 指标 | 说明 |
        |------|------|
        | **OBV** | 能量潮，累加/减成交量，判断资金流向 |
        | **VWAP** | 成交量加权平均价，机构常用基准 |
        | **MFI** | 资金流量指标，结合价格和成交量 |
        | **量价背离** | 价格新高但成交量未放大，可能趋势衰竭 |
        """)

    with st.expander("📉 波动率指标"):
        st.markdown("""
        | 指标 | 说明 |
        |------|------|
        | **ATR** | 平均真实波幅，衡量日内波动幅度，常用于止损和仓位管理 |
        | **历史波动率** | 过去一段时间收益率的标准差 |
        | **隐含波动率** | 期权价格反推出的市场对未来波动预期 |
        | **VIX** | 芝加哥期权交易所波动率指数，俗称“恐慌指数” |
        """)

    # ==================== 六、期权知识 ====================
    st.markdown("---")
    st.header("🎯 六、期权知识")

    with st.expander("📘 期权基本概念"):
        st.markdown("""
        - **期权 (Option)**：赋予持有者在约定时间以约定价格买入或卖出标的资产的权利。
        - **认购期权 / Call**：买入标的的权利（看多）。
        - **认沽期权 / Put**：卖出标的的权利（看空）。
        - **行权价 (Strike)**：约定的买卖价格。
        - **到期日 (Expiry)**：期权失效的日期。
        - **权利金 (Premium)**：购买期权所支付的价格。
        - **内在价值**：立即行权可获得的收益。
        - **时间价值**：权利金中超出内在价值的部分，随到期日临近衰减。
        - **实值 / 平值 / 虚值**：行权价与标的价格的关系。
        """)

    with st.expander("🔠 希腊字母 (Greeks)"):
        st.markdown("""
        | 希腊字母 | 含义 | 通俗理解 |
        |----------|------|----------|
        | **Delta** | 标的价格变化1单位，期权价格变化多少 | 期权的“股价敏感度” |
        | **Gamma** | Delta 变化的速度 | 价格越接近行权价，Gamma 越大 |
        | **Theta** | 时间衰减，每过一天期权价值减少多少 | 时间是期权卖方的朋友 |
        | **Vega** | 波动率变化1%，期权价格变化多少 | 波动率升，期权一般更贵 |
        | **Rho** | 利率变化对期权价格的影响 | 利率影响较小，长期期权更明显 |
        """)

    with st.expander("🧩 常见期权策略组合"):
        st.markdown("""
        | 策略 | 构建方式 | 适用场景 |
        |------|----------|----------|
        | **跨式组合 (Straddle)** | 同时买入同价 Call 和 Put | 预期大波动但方向不明 |
        | **宽跨式 (Strangle)** | 买入不同价 Call 和 Put，成本低于跨式 | 预期大波动 |
        | **蝶式价差 (Butterfly)** | 买入低/高行权价，卖出两份中间行权价 | 预期价格窄幅震荡 |
        | **铁鹰式 (Iron Condor)** | 卖出中间跨式，买入外侧 wing 保护 | 预期低波动，收时间价值 |
        | **备兑开仓 (Covered Call)** | 持有股票同时卖出 Call | 震荡市增强收益 |
        | **保护性看跌 (Protective Put)** | 持有股票同时买入 Put | 为持仓买保险 |
        | **领口策略 (Collar)** | 持有股票 + 买入 Put + 卖出 Call | 限制下行同时让渡部分上行 |
        """)

    with st.expander("🧮 期权定价与波动率模型"):
        st.markdown("""
        - **Black-Scholes 模型**：经典的欧式期权定价公式，假设标的服从几何布朗运动、波动率恒定。
        - **二叉树模型 (Binomial)**：离散时间定价模型，可处理美式期权提前行权。
        - **蒙特卡洛模拟**：通过随机路径模拟标的资产价格，估算复杂衍生品价值。
        - **GARCH 模型**：刻画波动率聚集现象，预测时变波动率。
        - **CAPM / 套利定价理论 (APT)**：资产定价与风险收益关系的基础模型。
        """)

    # ==================== 七、回测与风控 ====================
    st.markdown("---")
    st.header("🛡️ 七、回测与风控")

    with st.expander("🔬 回测原理与正确流程"):
        st.markdown("""
        回测是用历史数据验证策略表现的仿真过程。科学的回测流程：
        1. **明确假设**：策略逻辑、交易成本、信号产生与执行时点。
        2. **获取数据**：复权价格、成交量、财务数据等。
        3. **避免前视偏差**：只用当前时点可得信息。
        4. **划分样本**：训练集/验证集/测试集，避免过拟合。
        5. **加入摩擦成本**：佣金、滑点、冲击成本、资金费率。
        6. **评估绩效**：收益、风险、回撤、胜率、盈亏比、稳定性。
        7. **样本外检验**：用未见过的数据再次验证。
        """)

    with st.expander("⚠️ 常见回测陷阱"):
        st.markdown("""
        | 陷阱 | 说明 | 避免方法 |
        |------|------|----------|
        | **过拟合 (Overfitting)** | 参数对历史数据过度优化，未来失效 | 简化参数、交叉验证、样本外测试 |
        | **前视偏差 (Look-ahead Bias)** | 使用了未来才知道的信息 | 严格按时间顺序获取数据 |
        | **幸存者偏差 (Survivorship Bias)** | 只保留现存股票，忽略已退市股 | 使用包含退市股的历史数据 |
        | **数据窥探偏差 (Data Snooping)** | 多次试验后偶然找到“好”策略 | 控制显著性、增加样本量 |
        | **参数高原/孤岛** | 绩效对参数高度敏感 | 参数稳健性分析 |
        """)

    with st.expander("🛠️ 风险管理体系"):
        st.markdown("""
        - **仓位控制**：单笔/单日最大亏损限制，避免单笔黑天鹅致命。
        - **止损规则**：固定比例、ATR、技术位、时间止损。
        - **分散化**：跨品种、跨行业、跨策略、跨周期降低集中度风险。
        - **压力测试**：模拟极端行情下组合表现。
        - **最大回撤控制**：回撤超过阈值时减仓或暂停交易。
        - **流动性风险**：确保策略容量与市场容量匹配，避免冲击成本过大。
        - **模型风险**：模型假设失效时要有备用方案。
        """)

    with st.expander("📋 绩效评估与归因"):
        st.markdown("""
        - **收益归因**：收益来自选股、择时、行业配置、风格因子还是运气？
        - **Brinson 归因**：将组合超额收益分解为配置效应与选股效应。
        - **风险归因**：识别主要风险来源（Beta、行业、因子、个券）。
        - **滚动绩效**：分年度、分季度、分市场环境考察策略稳定性。
        - **最大回撤恢复时间**：衡量策略从低谷回到新高的能力。
        """)

    # ==================== 八、行业术语 ====================
    st.markdown("---")
    st.header("🏭 八、行业术语")

    with st.expander("💬 常见缩写速查"):
        for term, desc in TERM_LIBRARY["常用缩写"].items():
            st.markdown(f"**{term}**：{desc}")

    with st.expander("🎤 量化圈黑话与术语"):
        for term, desc in TERM_LIBRARY["行业黑话"].items():
            st.markdown(f"**{term}**：{desc}")

    with st.expander("🏦 机构与基础设施"):
        st.markdown("""
        - **量化私募**：以数学模型和计算机程序为核心进行投资决策的私募机构。
        - **对冲基金 (Hedge Fund)**：追求绝对收益，常使用多空、杠杆、衍生品等工具。
        - **公募量化基金**：面向大众投资者，受持仓比例、申赎等约束较多。
        - **券商自营/资管**：证券公司自有资金或代客理财进行量化投资。
        - **托管/估值/外包**：基金资产的保管、净值计算、运营支持服务。
        - **FPGA / 低延迟网络**：高频交易中用于降低系统延迟的硬件与网络技术。
        - **暗池 (Dark Pool)**：不公开显示订单簿的大宗交易场所。
        """)

    # ==================== 九、金融基础 ====================
    st.markdown("---")
    st.header("💰 九、金融基础")

    with st.expander("🌍 宏观经济指标"):
        st.markdown("""
        | 指标 | 含义 | 对资产影响 |
        |------|------|------------|
        | **GDP** | 国内生产总值 | 经济基本面核心指标 |
        | **CPI / PPI** | 消费/生产者价格指数 | 通胀水平，影响货币政策 |
        | **PMI** | 采购经理人指数 | >50 扩张，<50 收缩 |
        | **利率** | 资金价格 | 影响折现率、估值、债券价格 |
        | **汇率** | 本币对外币价值 | 影响出口、外资流动 |
        | **M2** | 广义货币供应量 | 反映市场流动性 |
        | **失业率** | 劳动力市场状况 | 影响消费与政策 |
        """)

    with st.expander("🏢 公司财务指标"):
        st.markdown("""
        | 指标 | 公式 | 含义 |
        |------|------|------|
        | **PE（市盈率）** | 股价 / 每股收益 | 估值水平 |
        | **PB（市净率）** | 股价 / 每股净资产 | 净资产估值 |
        | **ROE** | 净利润 / 净资产 | 股东权益回报率 |
        | **ROA** | 净利润 / 总资产 | 资产利用效率 |
        | **毛利率** | (营收-成本)/营收 | 产品盈利能力 |
        | **净利率** | 净利润 / 营收 | 最终盈利水平 |
        | **资产负债率** | 总负债 / 总资产 | 财务杠杆与风险 |
        | **自由现金流 (FCF)** | 经营现金流-资本支出 | 企业可自由支配现金 |
        """)

    with st.expander("📚 金融市场结构"):
        st.markdown("""
        - **交易所**：提供标准化证券交易场所（上交所、深交所、北交所）。
        - **场外市场 (OTC)**：非集中交易，如银行间债券市场、新三板。
        - **做市商制度**：做市商提供双边报价，提升流动性。
        - **撮合成交**：买卖双方订单按价格优先、时间优先原则匹配。
        - **清算交收**：交易完成后的资金和证券交割，A股通常为T+1交收。
        """)

    with st.expander("🧠 经典经济理论"):
        st.markdown("""
        - **有效市场假说 (EMH)**：弱式、半强式、强式有效市场，价格反映信息程度不同。
        - **行为金融学**：研究投资者心理偏差（过度自信、损失厌恶、羊群效应）对市场的影响。
        - **均值回归**：资产价格或收益长期围绕均衡水平波动。
        - **动量效应**：过去表现好的资产未来短期仍可能表现好。
        - **风险溢价**：承担额外风险所要求的额外收益。
        """)

    # ==================== 十、统计与概率 ====================
    st.markdown("---")
    st.header("📐 十、统计与概率")

    with st.expander("📊 描述性统计"):
        st.markdown("""
        - **均值 (Mean)**：数据平均水平，但易受极端值影响。
        - **中位数 (Median)**：排序后中间值，更稳健。
        - **标准差 (Std)**：衡量波动程度，是风险度量的基础。
        - **偏度 (Skewness)**：分布不对称程度，负偏代表左尾厚，正偏代表右尾厚。
        - **峰度 (Kurtosis)**：分布尾部厚度，高峰度意味着极端值概率更高。
        - **百分位数 / 分位数**：用于了解数据在某一区间的位置。
        """)

    with st.expander("🎲 概率分布"):
        st.markdown("""
        - **正态分布**：许多金融模型假设收益服从正态分布，但现实中金融收益常具有厚尾特征。
        - **对数正态分布**：价格通常假设服从对数正态分布，因此价格不能为负。
        - **泊松分布**：用于建模稀有事件（如跳跃）发生次数。
        - **t 分布**：小样本或厚尾数据更合适的分布假设。
        - **稳定分布 /  levy 分布**：用于刻画极端风险。
        """)

    with st.expander("🧪 统计检验与假设"):
        st.markdown("""
        - **t 检验**：检验均值是否显著不等于某个值或两组均值是否有差异。
        - **卡方检验**：检验分类变量独立性或拟合优度。
        - **K-S 检验**：检验样本是否来自某个特定分布。
        - **ADF 检验**：检验时间序列是否平稳，是协整分析的前提。
        - **Granger 因果检验**：判断一个时间序列是否对另一个有预测能力。
        - **多重比较问题**：同时进行大量检验时，假阳性率会上升，需用 Bonferroni、FDR 等方法校正。
        """)

    with st.expander("📉 时间序列基础"):
        st.markdown("""
        - **自相关 (ACF)**：序列与自身滞后值的相关性。
        - **偏自相关 (PACF)**：剔除中间滞后影响后的相关性。
        - **平稳性**：均值、方差不随时间变化，是经典建模的前提。
        - **ARIMA 模型**：自回归+差分+移动平均模型，用于短期预测。
        - **协整 (Cointegration)**：两个非平稳序列的线性组合平稳，常用于配对交易。
        - **随机过程**：几何布朗运动、Ornstein-Uhlenbeck 过程等描述价格动态。
        """)


# ==================== 辅助绘图函数 ====================

def _draw_candlestick_demo():
    """画一根简单的K线示意图"""
    fig = go.Figure(data=[go.Candlestick(
        x=['示例K线'],
        open=[10.0], high=[10.8], low=[9.5], close=[10.5],
        increasing_line_color='#e74c3c',
        decreasing_line_color='#27ae60',
    )])
    fig.update_layout(
        title="阳线示例",
        height=250,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title="价格",
    )
    st.plotly_chart(fig, use_container_width=True)


def _draw_adjust_demo():
    """画复权对比示意图"""
    dates = pd.date_range("2024-01-01", periods=60)
    price_raw = 10 + np.cumsum(np.random.randn(60) * 0.2)  # 模拟含除权缺口
    # 在30日人为制造一个除权缺口
    price_raw[30:] = price_raw[30:] * 0.85
    price_adj = price_raw.copy()
    # 前复权：从后往前调整
    factor = price_raw[30] / (price_raw[30] / 0.85)
    price_adj[:30] = price_adj[:30] * 0.85

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=price_raw, mode='lines', name='未复权（有缺口）', line=dict(color='#d62728')))
    fig.add_trace(go.Scatter(x=dates, y=price_adj, mode='lines', name='前复权（连续）', line=dict(color='#2ca02c')))
    fig.update_layout(
        title="复权前后对比",
        height=250,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title="价格",
    )
    st.plotly_chart(fig, use_container_width=True)


def _draw_ma_cross_demo():
    """画均线金叉死叉示意图"""
    np.random.seed(42)
    n = 120
    dates = pd.date_range("2024-01-01", periods=n)
    price = 10 + np.cumsum(np.random.randn(n) * 0.2) + np.linspace(0, 5, n)
    ma20 = pd.Series(price).rolling(20).mean()
    ma60 = pd.Series(price).rolling(60).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=price, mode='lines', name='收盘价', line=dict(color='#333', width=1.2)))
    fig.add_trace(go.Scatter(x=dates, y=ma20, mode='lines', name='MA20', line=dict(color='#1f77b4')))
    fig.add_trace(go.Scatter(x=dates, y=ma60, mode='lines', name='MA60', line=dict(color='#ff7f0e')))

    fig.add_annotation(x=dates[40], y=ma20.iloc[40], text="金叉", showarrow=True, arrowhead=1, font=dict(color="green"))
    fig.add_annotation(x=dates[90], y=ma20.iloc[90], text="死叉", showarrow=True, arrowhead=1, font=dict(color="red"))

    fig.update_layout(
        title="双均线金叉/死叉示意",
        height=250,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title="价格",
    )
    st.plotly_chart(fig, use_container_width=True)


def _draw_choppy_market_demo():
    """画震荡市假信号示意"""
    np.random.seed(42)
    n = 80
    dates = pd.date_range("2024-01-01", periods=n)
    price = 10 + np.cumsum(np.random.randn(n) * 0.15)
    price = 10 + (price - np.mean(price)) * 0.3
    ma20 = pd.Series(price).rolling(20).mean()
    ma60 = pd.Series(price).rolling(60).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=price, mode='lines', name='收盘价', line=dict(color='#333', width=1.5)))
    fig.add_trace(go.Scatter(x=dates, y=ma20, mode='lines', name='MA20', line=dict(color='#1f77b4')))
    fig.add_trace(go.Scatter(x=dates, y=ma60, mode='lines', name='MA60', line=dict(color='#ff7f0e')))

    cross_dates = [dates[25], dates[45], dates[65]]
    for d in cross_dates:
        fig.add_annotation(x=d, y=price[list(dates).index(d)] + 0.4,
                           text="❌ 假金叉", showarrow=True, arrowhead=1,
                           font=dict(color="red", size=11))

    fig.update_layout(
        title="震荡市中的假信号",
        height=250,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title="价格",
    )
    st.plotly_chart(fig, use_container_width=True)
