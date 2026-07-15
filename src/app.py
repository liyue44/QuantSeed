"""
QuantSeed 主页 - 模块入口
=======================
提供聊天室和量化仪表盘两个模块入口。
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PAGE_TITLE, PAGE_LAYOUT, SIDEBAR_STATE, ensure_dirs

ensure_dirs()

st.set_page_config(
    page_title="QuantSeed 综合平台",
    layout=PAGE_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)

# ==================== 自定义 CSS ====================
st.markdown("""
<style>
    .module-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 2px solid transparent;
        margin: 1rem 0;
    }
    .module-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        border-color: #4fc3f7;
    }
    .module-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .module-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #e0e0e0;
        margin-bottom: 0.5rem;
    }
    .module-desc {
        font-size: 0.9rem;
        color: #aaa;
    }
    .password-box {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin-top: 0.5rem;
    }
    .status-online {
        background: rgba(76, 175, 80, 0.2);
        color: #4caf50;
    }
    .status-locked {
        background: rgba(255, 152, 0, 0.2);
        color: #ff9800;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 主页标题 ====================
st.title("🌱 QuantSeed 量化种子")
st.markdown("### 综合量化学习与交流平台")
st.markdown("---")

# ==================== 两个模块入口 ====================
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="module-card">
        <div class="module-icon">💬</div>
        <div class="module-title">聊天室</div>
        <div class="module-desc">输入用户名密码即可加入聊天<br>与大家实时交流讨论</div>
        <div class="status-badge status-online">👤 自由加入</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 进入聊天室", key="btn_chat", width="stretch", type="primary"):
        st.switch_page("pages/chat.py")

with col2:
    st.markdown("""
    <div class="module-card">
        <div class="module-icon">📊</div>
        <div class="module-title">量化仪表盘</div>
        <div class="module-desc">双均线回测 · 信号监控<br>知识库 · 算法可视化</div>
        <div class="status-badge status-locked">🔒 需要密码</div>
    </div>
    """, unsafe_allow_html=True)

    # 量化模块密码弹窗
    if "quantseed_verified" not in st.session_state:
        st.session_state.quantseed_verified = False

    if st.button("🔐 进入量化仪表盘", key="btn_quant", width="stretch"):
        st.session_state.show_quant_password = True

    if st.session_state.get("show_quant_password"):
        with st.container():
            st.markdown('<div class="password-box">', unsafe_allow_html=True)
            st.markdown("#### 🔐 量化模块密码验证")
            pwd = st.text_input("请输入密码", type="password", key="quant_pwd_input")
            col_ok, col_cancel = st.columns(2)
            with col_ok:
                if st.button("✅ 确认", width="stretch"):
                    if pwd == "quantseed":
                        st.session_state.quantseed_verified = True
                        st.session_state.show_quant_password = False
                        st.success("验证成功！正在跳转...")
                        st.switch_page("pages/4_📊_量化仪表盘.py")
                    else:
                        st.error("密码错误")
            with col_cancel:
                if st.button("❌ 取消", width="stretch"):
                    st.session_state.show_quant_password = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==================== 页脚 ====================
st.markdown("---")
st.caption("QuantSeed v2.0 | 综合量化学习与交流平台")
