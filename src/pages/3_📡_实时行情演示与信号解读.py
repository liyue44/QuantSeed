"""
实时行情演示与信号解读 - 行情面板 + K线解读 + 信号工单
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from live_signal_viewer import render_live_signal_viewer

st.set_page_config(page_title="实时行情演示", layout="wide")

st.title("📡 实时行情演示与信号解读")
st.markdown("### 最新市场数据 + K线解读 + 明日关注信号")
st.markdown("---")

render_live_signal_viewer()
