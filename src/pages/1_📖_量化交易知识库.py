"""
量化交易知识库 - 交互式词典（移动端适配）
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from knowledge_base import render_knowledge_base

st.set_page_config(page_title="量化交易知识库", layout="wide")

# ==================== 移动端响应式 CSS ====================
st.markdown("""
<style>
    @media (max-width: 768px) {
        .stApp { padding: 0.5rem !important; }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1rem !important; }
        .stButton button { font-size: 0.85rem !important; padding: 0.5rem 0.8rem !important; }
        .knowledge-card { padding: 1rem !important; }
    }
    @media (max-width: 480px) {
        h1 { font-size: 1.2rem !important; }
        h2 { font-size: 1.05rem !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("📖 量化交易知识库")
st.markdown("### 像一本交互式词典，随时查阅核心概念")
st.markdown("---")

render_knowledge_base()
