"""
QuantSeed 学习中心 - learning_center.py
======================================
学习中心主入口，通过 Streamlit 多页面机制整合三个教学子页面：
1. 量化交易知识库 (knowledge_base.py)
2. 核心算法可视化解析 (algorithm_visualizer.py)
3. 实时行情演示与信号解读 (live_signal_viewer.py)

运行方式：
    streamlit run src/learning_center.py
    或从 app.py 侧边栏跳转
"""

import streamlit as st
import os
import sys

# 将src目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PAGE_TITLE, PAGE_LAYOUT, SIDEBAR_STATE

# 页面配置
st.set_page_config(
    page_title="QuantSeed 学习中心",
    layout=PAGE_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)

# 导入子页面模块
from knowledge_base import render_knowledge_base
from algorithm_visualizer import render_algorithm_visualizer
from live_signal_viewer import render_live_signal_viewer

# ==================== 页面标题 ====================
st.title("📚 QuantSeed 学习中心")
st.markdown("### 从零开始理解量化交易：知识、算法与实战")
st.markdown("---")

# ==================== 子页面选择 ====================
tab1, tab2, tab3 = st.tabs([
    "📖 量化交易知识库",
    "🔬 核心算法可视化解析",
    "📡 实时行情演示与信号解读",
])

with tab1:
    render_knowledge_base()

with tab2:
    render_algorithm_visualizer()

with tab3:
    render_live_signal_viewer()

# ==================== 页脚 ====================
st.markdown("---")
st.caption(
    "QuantSeed v1.0 学习中心 | "
    "第二阶段将增加更多策略教学和实盘模拟功能"
)
