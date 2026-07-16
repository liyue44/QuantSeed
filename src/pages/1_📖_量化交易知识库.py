"""
量化交易知识库 - 交互式词典（移动端适配）
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from knowledge_base import render_knowledge_base

st.set_page_config(page_title="量化交易知识库", layout="wide")

# 密码保护
if not st.session_state.get("quantseed_verified"):
    st.warning("请从首页进入量化模块")
    if st.button("← 返回首页", use_container_width=True):
        st.switch_page("app.py")
    st.stop()

# ==================== CSS：返回顶部 + 移动端适配 ====================
st.markdown("""
<style>
    /* 返回顶部按钮 */
    #back-to-top {
        display: none;
        position: fixed;
        bottom: 40px;
        right: 30px;
        z-index: 9999;
        width: 44px;
        height: 44px;
        background: #667eea;
        color: white;
        border: none;
        border-radius: 50%;
        font-size: 22px;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
        line-height: 44px;
        text-align: center;
    }
    #back-to-top:hover {
        background: #5a6fd6;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
    }
    #back-to-top.show {
        display: block;
    }

    /* 标题栏容器 */
    .title-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .title-bar .title-text {
        flex: 1;
        min-width: 0;
    }
    .home-btn {
        flex-shrink: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        padding: 6px 16px;
        border-radius: 20px;
        text-decoration: none !important;
        font-size: 0.88rem;
        font-weight: 500;
        white-space: nowrap;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .home-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        color: white !important;
    }

    @media (max-width: 768px) {
        .stApp { padding: 0.5rem !important; }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1rem !important; }
        .stButton button { font-size: 0.85rem !important; padding: 0.5rem 0.8rem !important; }
        .knowledge-card { padding: 1rem !important; }
        #back-to-top {
            bottom: 20px;
            right: 16px;
            width: 38px;
            height: 38px;
            line-height: 38px;
            font-size: 18px;
        }
        .home-btn { font-size: 0.8rem; padding: 4px 12px; }
    }
    @media (max-width: 480px) {
        h1 { font-size: 1.2rem !important; }
        h2 { font-size: 1.05rem !important; }
    }
</style>

<!-- 返回顶部按钮 -->
<button id="back-to-top" title="返回顶部" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>

<script>
    const btn = document.getElementById('back-to-top');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 600) {
            btn.classList.add('show');
        } else {
            btn.classList.remove('show');
        }
    });
</script>
""", unsafe_allow_html=True)

# ==================== 标题栏（含返回首页按钮） ====================
st.markdown("""
<div class="title-bar">
    <div class="title-text">
        <h1 style="margin:0; padding:0; border:none;">📖 量化交易知识库</h1>
    </div>
    <a class="home-btn" href="/" target="_self">🏠 返回首页</a>
</div>
""", unsafe_allow_html=True)

st.markdown("### 像一本交互式词典，随时查阅核心概念")
st.markdown("---")

render_knowledge_base()
