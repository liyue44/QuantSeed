"""
核心算法可视化解析 - 双均线策略分步教学
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from algorithm_visualizer import render_algorithm_visualizer

st.set_page_config(page_title="算法可视化解析", layout="wide")

st.title("🔬 核心算法可视化解析")
st.markdown("### 彻底弄懂双均线策略的每一步")
st.markdown("---")

render_algorithm_visualizer()
