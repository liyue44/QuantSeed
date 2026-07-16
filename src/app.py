"""
QuantSeed 主页 - 移动端适配量化平台
==================================
提供量化仪表盘和知识库入口，针对手机浏览器优化。
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PAGE_TITLE, PAGE_LAYOUT, SIDEBAR_STATE, ensure_dirs

ensure_dirs()

st.set_page_config(
    page_title="QuantSeed 量化种子",
    layout=PAGE_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)

# ==================== 防密码自动填充 + 隐藏未认证导航 ====================
st.markdown("""
<style>
    input[type="password"] {
        -webkit-text-security: disc !important;
    }
    .hide-quant-pages [data-testid="stSidebarNav"] a:not([href*="app"]):not([href*="5_"]):not([href*="%F0%9F%92%AC"]) {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("quantseed_verified", False):
    st.markdown("""
    <script>
        document.body.classList.add('hide-quant-pages');
        document.addEventListener('DOMContentLoaded', function() {
            document.body.classList.add('hide-quant-pages');
            var links = document.querySelectorAll('[data-testid="stSidebarNav"] a');
            links.forEach(function(a) {
                var href = a.getAttribute('href') || '';
                // 隐藏量化子页面（1-4），保留聊天室（5）
                var isChat = href.includes('5_') || href.includes('%F0%9F%92%AC');
                if (!href.includes('app') && !isChat) {
                    a.style.display = 'none';
                }
            });
        });
    </script>
    """, unsafe_allow_html=True)

# ==================== 响应式 CSS ====================
st.markdown("""
<style>
    /* === 全局响应式基础 === */
    @media (max-width: 768px) {
        .stApp {
            padding: 0.5rem !important;
        }
        h1 {
            font-size: 1.5rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        .stButton button {
            font-size: 0.9rem !important;
            padding: 0.6rem 1rem !important;
        }
    }

    /* === 主页头部 === */
    .hero-section {
        text-align: center;
        padding: 1.5rem 1rem;
        background: linear-gradient(135deg, #0d1b2a 0%, #1b2838 50%, #0f3460 100%);
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(79, 195, 247, 0.15);
    }
    .hero-section h1 {
        background: linear-gradient(135deg, #4fc3f7, #81d4fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
    }
    .hero-subtitle {
        color: #90a4ae;
        font-size: 0.95rem;
    }

    /* === 功能卡片网格 === */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    @media (max-width: 640px) {
        .feature-grid {
            grid-template-columns: 1fr;
            gap: 0.8rem;
        }
    }

    .feature-card {
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
        border-radius: 14px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: all 0.3s ease;
        text-align: center;
        cursor: default;
    }
    .feature-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        border-color: rgba(79, 195, 247, 0.4);
    }
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 0.8rem;
        display: block;
    }
    .feature-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #e0e0e0;
        margin-bottom: 0.4rem;
    }
    .feature-desc {
        font-size: 0.85rem;
        color: #90a4ae;
        line-height: 1.5;
    }
    .feature-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 10px;
        font-size: 0.75rem;
        margin-top: 0.6rem;
    }
    .badge-free {
        background: rgba(76, 175, 80, 0.2);
        color: #66bb6a;
    }
    .badge-locked {
        background: rgba(255, 152, 0, 0.2);
        color: #ffa726;
    }

    /* === 密码弹窗 === */
    .password-box {
        max-width: 360px;
        margin: 1rem auto;
        padding: 1.5rem;
        background: rgba(255,255,255,0.04);
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    @media (max-width: 480px) {
        .password-box {
            max-width: 100%;
            padding: 1rem;
        }
    }

    /* === 统计条 === */
    .stats-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: center;
        margin-bottom: 1rem;
    }
    .stat-item {
        background: rgba(255,255,255,0.04);
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        text-align: center;
        min-width: 100px;
    }
    .stat-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #4fc3f7;
    }
    .stat-label {
        font-size: 0.75rem;
        color: #90a4ae;
    }

    /* === 页脚 === */
    .footer {
        text-align: center;
        padding: 1rem;
        color: #546e7a;
        font-size: 0.8rem;
    }

    /* === 移动端侧边栏优化 === */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            width: 100% !important;
            max-width: 100% !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 头部 ====================
st.markdown("""
<div class="hero-section">
    <h1>🌱 QuantSeed 量化种子</h1>
    <p class="hero-subtitle">双均线策略回测 · 信号监控 · 知识学习 · 算法可视化</p>
</div>
""", unsafe_allow_html=True)

# ==================== 快速统计 ====================
try:
    from data_manager import DataManager
    dm = DataManager()
    available_count = len(dm.get_available_stocks())
    total_count = len(dm.stock_pool)
except Exception:
    available_count = 0
    total_count = 35

st.markdown(f"""
<div class="stats-bar">
    <div class="stat-item">
        <div class="stat-value">{total_count}</div>
        <div class="stat-label">股票池</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">{available_count}</div>
        <div class="stat-label">已下载数据</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">MA20×MA60</div>
        <div class="stat-label">核心策略</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">100万</div>
        <div class="stat-label">初始资金</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== 功能入口卡片 ====================
st.markdown("### 📱 功能模块")

# 初始化 session state
if "quantseed_verified" not in st.session_state:
    st.session_state.quantseed_verified = False
if "show_quant_password" not in st.session_state:
    st.session_state.show_quant_password = False

# ========== 量化模块（需密码） ==========
st.markdown("""
<div class="feature-card">
    <span class="feature-icon">📊</span>
    <div class="feature-title">量化</div>
    <div class="feature-desc">仪表盘 · 知识库 · 算法可视化 · 行情<br>双均线回测 · 信号监控 · 量化学习</div>
    <span class="feature-badge badge-locked">🔒 需要密码</span>
</div>
""", unsafe_allow_html=True)

# ========== 聊天室入口（独立密码，始终可见） ==========
st.markdown("""
<div class="feature-card">
    <span class="feature-icon">💬</span>
    <div class="feature-title">聊天室</div>
    <div class="feature-desc">实时聊天 · 交流讨论<br>门锁密码保护 · IP 自动记忆</div>
    <span class="feature-badge badge-locked">🔒 门锁密码</span>
</div>
""", unsafe_allow_html=True)
if st.button("💬 进入聊天室", key="btn_chat", use_container_width=True):
    st.switch_page("pages/5_💬_聊天室.py")

if not st.session_state.quantseed_verified:
    if st.button("🔐 进入量化", key="btn_quant", use_container_width=True):
        st.session_state.show_quant_password = True

    if st.session_state.show_quant_password:
        st.markdown('<div class="password-box">', unsafe_allow_html=True)
        st.markdown("#### 🔐 密码验证")
        pwd = st.text_input("请输入密码", type="password", key="quant_pwd_input",
                           placeholder="输入 quantseed", autocomplete="new-password")
        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button("✅ 确认", use_container_width=True):
                if pwd == "quantseed":
                    st.session_state.quantseed_verified = True
                    st.session_state.show_quant_password = False
                    st.success("验证成功！")
                    st.rerun()
                else:
                    st.error("密码错误")
        with col_cancel:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.show_quant_password = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.success("✅ 已通过验证，请选择子模块：")
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        # 量化仪表盘
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">📊</span>
            <div class="feature-title">量化仪表盘</div>
            <div class="feature-desc">双均线回测 · 交易明细<br>信号监控 · 数据概览</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📊 进入仪表盘", key="btn_dashboard", use_container_width=True):
            st.switch_page("pages/4_📊_量化仪表盘.py")

        # 算法可视化
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">🔬</span>
            <div class="feature-title">算法可视化</div>
            <div class="feature-desc">双均线策略分步教学<br>看懂每一根K线</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔬 进入可视化", key="btn_av", use_container_width=True):
            st.switch_page("pages/2_🔬_核心算法可视化解析.py")

    with col2:
        # 知识库
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">📖</span>
            <div class="feature-title">量化知识库</div>
            <div class="feature-desc">交互式词典 · 核心概念<br>随时查阅量化术语</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📖 进入知识库", key="btn_kb", use_container_width=True):
            st.switch_page("pages/1_📖_量化交易知识库.py")

        # 行情演示
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">📡</span>
            <div class="feature-title">行情演示</div>
            <div class="feature-desc">实时行情面板 · K线解读<br>信号工单与趋势分析</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📡 进入行情", key="btn_ls", use_container_width=True):
            st.switch_page("pages/3_📡_实时行情演示与信号解读.py")

# ==================== 页脚 ====================
st.markdown("---")
st.markdown("""
<div class="footer">
    QuantSeed v2.0 · 双均线量化策略回测与学习平台 · 适配手机浏览器
</div>
""", unsafe_allow_html=True)
