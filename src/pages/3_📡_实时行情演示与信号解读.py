"""
实时行情演示与信号解读 - 行情面板 + K线解读 + 信号工单（移动端适配）
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from live_signal_viewer import render_live_signal_viewer

st.set_page_config(page_title="实时行情演示", layout="wide")

# ==================== 移动端响应式 CSS ====================
st.markdown("""
<style>
    @media (max-width: 768px) {
        .stApp { padding: 0.5rem !important; }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1rem !important; }
        .stButton button { font-size: 0.85rem !important; padding: 0.5rem 0.8rem !important; }
    }
    @media (max-width: 480px) {
        h1 { font-size: 1.2rem !important; }
        h2 { font-size: 1.05rem !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("📡 实时行情演示与信号解读")
st.markdown("### 最新市场数据 + K线解读 + 明日关注信号")
st.markdown("---")

render_live_signal_viewer()
