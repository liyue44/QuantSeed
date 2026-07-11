"""
量化交易知识库 - 交互式词典
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from knowledge_base import render_knowledge_base

st.set_page_config(page_title="量化交易知识库", layout="wide")

st.title("📖 量化交易知识库")
st.markdown("### 像一本交互式词典，随时查阅核心概念")
st.markdown("---")

render_knowledge_base()
