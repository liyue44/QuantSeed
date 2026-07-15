"""
QuantSeed 聊天室
==============
输入用户名和密码即可进入聊天室。
管理员账户: root / root
"""

import streamlit as st
import requests
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="聊天室 - QuantSeed",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==================== CSS ====================
st.markdown("""
<style>
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
    }
    .chat-message {
        padding: 10px 16px;
        border-radius: 12px;
        margin: 6px 0;
        animation: fadeIn 0.3s ease;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .chat-message-self {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 40px;
    }
    .chat-message-other {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.12);
        margin-right: 40px;
    }
    .chat-message-admin {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        margin-right: 40px;
        border-left: 3px solid #ff4081;
    }
    .chat-username {
        font-weight: bold;
        font-size: 0.85rem;
        margin-bottom: 2px;
    }
    .chat-time {
        font-size: 0.7rem;
        opacity: 0.7;
        float: right;
    }
    .chat-content {
        font-size: 1rem;
        line-height: 1.5;
    }
    .chat-input-area {
        position: sticky;
        bottom: 0;
        background: #0e1117;
        padding: 1rem 0;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    .login-box {
        max-width: 420px;
        margin: 4rem auto;
        padding: 2.5rem;
        background: rgba(255,255,255,0.04);
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
    }
    .delete-btn {
        font-size: 0.65rem;
        opacity: 0.4;
        cursor: pointer;
        float: right;
        margin-left: 8px;
    }
    .delete-btn:hover {
        opacity: 1;
        color: #ff5252;
    }
</style>
""", unsafe_allow_html=True)

# ==================== Session State ====================
if "chat_logged_in" not in st.session_state:
    st.session_state.chat_logged_in = False
if "chat_username" not in st.session_state:
    st.session_state.chat_username = ""
if "chat_is_admin" not in st.session_state:
    st.session_state.chat_is_admin = False
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_last_id" not in st.session_state:
    st.session_state.chat_last_id = 0
if "chat_auto_refresh" not in st.session_state:
    st.session_state.chat_auto_refresh = True


# ==================== API 调用 ====================
def api_login(username, password):
    try:
        r = requests.post(f"{API_BASE}/api/auth/login", json={
            "username": username, "password": password
        }, timeout=5)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_register(username, password):
    try:
        r = requests.post(f"{API_BASE}/api/auth/register", json={
            "username": username, "password": password
        }, timeout=5)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get_messages(limit=50):
    try:
        r = requests.get(f"{API_BASE}/api/chat/messages", params={"limit": limit}, timeout=5)
        return r.json()
    except Exception:
        return {"messages": []}


def api_send_message(username, content):
    try:
        r = requests.post(f"{API_BASE}/api/chat/send", json={
            "username": username, "content": content
        }, timeout=5)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_delete_message(message_id, username):
    try:
        r = requests.delete(
            f"{API_BASE}/api/chat/messages/{message_id}",
            params={"username": username},
            timeout=5,
        )
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_clear_chat(username):
    try:
        r = requests.delete(f"{API_BASE}/api/chat/messages", params={"username": username}, timeout=5)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 登录界面 ====================
if not st.session_state.chat_logged_in:
    st.title("💬 QuantSeed 聊天室")

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("### 👋 欢迎来到聊天室")
    st.markdown("输入用户名和密码即可加入")

    tab_login, tab_reg = st.tabs(["🔑 登录 / 自动注册", "📝 新用户注册"])

    with tab_login:
        login_user = st.text_input("用户名", key="login_user", placeholder="输入用户名（新用户将自动注册）")
        login_pass = st.text_input("密码", type="password", key="login_pass", placeholder="输入密码")
        if st.button("🚀 进入聊天室", width="stretch", type="primary"):
            if not login_user.strip():
                st.error("请输入用户名")
            elif not login_pass.strip():
                st.error("请输入密码")
            else:
                result = api_login(login_user.strip(), login_pass.strip())
                if result.get("success"):
                    st.session_state.chat_logged_in = True
                    st.session_state.chat_username = result["username"]
                    st.session_state.chat_is_admin = result.get("is_admin", False)
                    st.rerun()
                else:
                    st.error(result.get("detail", result.get("error", "登录失败")))

    with tab_reg:
        reg_user = st.text_input("用户名", key="reg_user", placeholder="设置用户名")
        reg_pass = st.text_input("密码", type="password", key="reg_pass", placeholder="设置密码")
        if st.button("📝 注册并进入", width="stretch"):
            if not reg_user.strip():
                st.error("请输入用户名")
            elif not reg_pass.strip():
                st.error("请输入密码")
            else:
                result = api_register(reg_user.strip(), reg_pass.strip())
                if result.get("success"):
                    login_result = api_login(reg_user.strip(), reg_pass.strip())
                    if login_result.get("success"):
                        st.session_state.chat_logged_in = True
                        st.session_state.chat_username = login_result["username"]
                        st.session_state.chat_is_admin = login_result.get("is_admin", False)
                        st.rerun()
                else:
                    st.error(result.get("detail", "注册失败，用户名可能已存在"))

    st.markdown("> 💡 **提示**：新用户名首次输入密码即自动注册。管理员账户：`root` / `root`")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ==================== 聊天界面 ====================
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# 顶栏
col_title, col_info, col_refresh, col_leave = st.columns([3, 2, 1, 1])
with col_title:
    st.title("💬 QuantSeed 聊天室")
with col_info:
    admin_badge = " 👑 管理员" if st.session_state.chat_is_admin else ""
    st.markdown(f"**当前用户**: {st.session_state.chat_username}{admin_badge}")
    st.session_state.chat_auto_refresh = st.checkbox("自动刷新", value=st.session_state.chat_auto_refresh)
with col_refresh:
    if st.button("🔄 刷新", width="stretch"):
        st.rerun()
with col_leave:
    if st.button("🚪 退出", width="stretch"):
        st.session_state.chat_logged_in = False
        st.session_state.chat_username = ""
        st.session_state.chat_is_admin = False
        st.rerun()

# 管理员工具
if st.session_state.chat_is_admin:
    with st.expander("🛠️ 管理员工具"):
        if st.button("🗑️ 清空所有聊天记录", type="secondary"):
            result = api_clear_chat(st.session_state.chat_username)
            if result.get("success"):
                st.success("聊天记录已清空")
                st.rerun()
            else:
                st.error("清空失败")

st.markdown("---")

# ==================== 消息显示区 ====================
messages_container = st.container()

with messages_container:
    data = api_get_messages(limit=100)
    messages = data.get("messages", [])

    if not messages:
        st.info("📭 暂无消息，快来发送第一条消息吧！")
    else:
        for msg in messages:
            is_self = msg["username"] == st.session_state.chat_username
            is_admin_msg = msg["username"] in ["root", "admin"]

            if is_self:
                css_class = "chat-message-self"
            elif is_admin_msg:
                css_class = "chat-message-admin"
            else:
                css_class = "chat-message-other"

            delete_btn = ""
            if st.session_state.chat_is_admin or is_self:
                delete_btn = (
                    f'<span class="delete-btn" '
                    f'onclick="document.getElementById(\'delete_msg_{msg["id"]}\').click()" '
                    f'title="删除">✕</span>'
                )

            st.markdown(f"""
            <div class="chat-message {css_class}">
                <div class="chat-username">
                    {'👑 ' if is_admin_msg else ''}{msg["username"]}
                    <span class="chat-time">{msg["created_full"]}</span>
                </div>
                <div class="chat-content">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)

# ==================== 消息输入区 ====================
st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)
col_input, col_send = st.columns([5, 1])
with col_input:
    new_message = st.text_area(
        "输入消息",
        key="chat_input",
        placeholder="输入你的消息... (Ctrl+Enter 发送)",
        label_visibility="collapsed",
        height=68,
    )
with col_send:
    st.markdown("<br>", unsafe_allow_html=True)
    send_btn = st.button("📨 发送", width="stretch", type="primary")
    # 监听 Ctrl+Enter
    st.markdown("""
    <script>
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            document.querySelector('button[kind="primary"]').click();
        }
    });
    </script>
    """, unsafe_allow_html=True)

if send_btn and new_message.strip():
    result = api_send_message(st.session_state.chat_username, new_message.strip())
    if result.get("success"):
        st.session_state.chat_input_clear = True
        st.rerun()
    else:
        st.error("发送失败，请重试")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==================== 自动刷新 ====================
if st.session_state.chat_auto_refresh:
    time.sleep(2)
    st.rerun()
