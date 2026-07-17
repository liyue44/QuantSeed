"""
项目报告模块
- 密码验证（默认 135246）
- 嵌入 project-report.html 内容
"""

import streamlit as st
import streamlit.components.v1 as components
import os

# ==================== 页面配置 ====================
st.set_page_config(page_title="项目报告", page_icon="📋", layout="wide")

# ==================== Session State ====================
if "report_unlocked" not in st.session_state:
    st.session_state.report_unlocked = False

# ==================== CSS ====================
st.markdown("""
<style>
    .lock-box {
        max-width: 380px;
        margin: 3rem auto;
        padding: 2rem;
        background: rgba(255,255,255,0.04);
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
    }
    .lock-icon {
        font-size: 3rem;
        display: block;
        margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 密码验证 ====================
if not st.session_state.report_unlocked:
    st.markdown("""
    <div class="lock-box">
        <span class="lock-icon">🔐</span>
        <h2 style="margin:0 0 0.5rem 0; color:#e0e0e0;">项目分析报告</h2>
        <p style="color:#90a4ae; font-size:0.9rem;">请输入密码查看</p>
    </div>
    """, unsafe_allow_html=True)

    report_pwd = st.text_input("密码", type="password", key="report_pwd",
                               placeholder="请输入密码", autocomplete="new-password")

    col_enter, _ = st.columns([1, 3])
    with col_enter:
        if st.button("📋 查看报告", use_container_width=True):
            if report_pwd == "135246":
                st.session_state.report_unlocked = True
                st.rerun()
            else:
                st.error("密码错误")
    st.stop()

# ==================== 报告内容 ====================
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;margin-bottom:1rem;">
    <h2 style="margin:0;color:#e0e0e0;">📋 项目分析报告</h2>
</div>
""", unsafe_allow_html=True)

# 读取 HTML 文件
html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "project-report.html")
if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=800, scrolling=True)
else:
    st.error(f"找不到报告文件: {html_path}")

# 退出按钮
st.markdown("---")
col_exit, _ = st.columns([1, 5])
with col_exit:
    if st.button("🚪 退出报告", use_container_width=True):
        st.session_state.report_unlocked = False
        st.rerun()
