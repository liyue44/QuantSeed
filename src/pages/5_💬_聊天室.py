"""
聊天室模块
- 门锁密码验证（默认 135246）
- 用户名输入（IP 自动记忆）
- 实时聊天
- 管理员面板（密码 root）
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chat_db

# ==================== 页面配置 ====================
st.set_page_config(page_title="聊天室", page_icon="💬", layout="centered")

# ==================== Session State 初始化 ====================
if "chat_unlocked" not in st.session_state:
    st.session_state.chat_unlocked = False
if "chat_username" not in st.session_state:
    st.session_state.chat_username = ""
if "chat_show_admin" not in st.session_state:
    st.session_state.chat_show_admin = False
if "chat_admin_verified" not in st.session_state:
    st.session_state.chat_admin_verified = False

# ==================== CSS ====================
st.markdown("""
<style>
    .chat-container {
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1rem;
        max-height: 60vh;
        overflow-y: auto;
        background: rgba(255,255,255,0.03);
        margin-bottom: 1rem;
    }
    .chat-msg {
        padding: 0.5rem 0.8rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        background: rgba(79, 195, 247, 0.08);
        border-left: 3px solid #4fc3f7;
    }
    .chat-msg .meta {
        font-size: 0.75rem;
        color: #78909c;
        margin-bottom: 0.15rem;
    }
    .chat-msg .meta .user {
        color: #4fc3f7;
        font-weight: 600;
    }
    .chat-msg .text {
        color: #e0e0e0;
        word-break: break-word;
    }
    .chat-msg.self {
        background: rgba(102, 126, 234, 0.12);
        border-left-color: #667eea;
    }
    .lock-box {
        max-width: 360px;
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
    .admin-panel {
        background: rgba(255,152,0,0.08);
        border: 1px solid rgba(255,152,0,0.3);
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
    }
    .online-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #4caf50;
        border-radius: 50%;
        margin-right: 4px;
    }
    @media (max-width: 768px) {
        .lock-box { margin: 1.5rem auto; padding: 1.5rem; }
        .chat-container { max-height: 50vh; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 获取客户端 IP ====================
def get_client_ip():
    """尝试多种方式获取客户端真实IP"""
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx = get_script_run_ctx()
    if ctx and hasattr(ctx, "session") and ctx.session:
        # 通过 streamlit 内部 session 获取
        pass
    # fallback: 通过 query params 或 header
    try:
        ip = st.query_params.get("client_ip", None)
        if ip:
            return ip
    except Exception:
        pass
    # 最终用 request 尝试
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers:
            ip = headers.get("X-Forwarded-For") or headers.get("X-Real-IP")
            if ip:
                return ip.split(",")[0].strip()
    except Exception:
        pass
    return "未知IP"

client_ip = get_client_ip()

# ==================== 门锁验证 ====================
if not st.session_state.chat_unlocked:
    st.markdown("""
    <div class="lock-box">
        <span class="lock-icon">🔐</span>
        <h2 style="margin:0 0 0.5rem 0; color:#e0e0e0;">聊天室</h2>
        <p style="color:#90a4ae; font-size:0.9rem;">请输入门锁密码进入</p>
    </div>
    """, unsafe_allow_html=True)

    lock_pwd = st.text_input("门锁密码", type="password", key="lock_pwd",
                             placeholder="请输入门锁密码", autocomplete="new-password")

    col_enter, _ = st.columns([1, 3])
    with col_enter:
        if st.button("🚪 进入聊天室", use_container_width=True):
            if lock_pwd == "135246":
                st.session_state.chat_unlocked = True
                # 检查IP是否有历史用户名
                saved_name = chat_db.get_username_by_ip(client_ip)
                if saved_name:
                    st.session_state.chat_username = saved_name
                st.rerun()
            else:
                st.error("密码错误")

    # 管理员入口（小字，不易察觉）
    st.markdown("<br>", unsafe_allow_html=True)
    col_admin_btn, _ = st.columns([1, 3])
    with col_admin_btn:
        if st.button("🛠️", key="tiny_admin_btn", help="管理员入口"):
            st.session_state.chat_show_admin = True
            st.rerun()

    # 管理员面板（未进入聊天室时也可以访问）
    if st.session_state.chat_show_admin:
        st.markdown("---")
        st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
        if not st.session_state.chat_admin_verified:
            admin_pwd = st.text_input("管理员密码", type="password", key="admin_pwd_outside",
                                      placeholder="输入管理员密码")
            if st.button("🔑 验证管理员", key="verify_admin_outside"):
                if admin_pwd == "root":
                    st.session_state.chat_admin_verified = True
                    st.rerun()
                else:
                    st.error("管理员密码错误")
        else:
            st.success("✅ 管理员已验证")
            st.subheader("💬 消息管理")
            msg_count = chat_db.get_message_count()
            st.info(f"共 {msg_count} 条消息")

            if msg_count > 0:
                msgs = chat_db.get_messages(limit=100)
                for m in reversed(msgs):
                    with st.container():
                        c1, c2, c3 = st.columns([2, 5, 1])
                        with c1:
                            st.markdown(f"**{m['username']}**")
                        with c2:
                            st.markdown(f"{m['content'][:50]}{'...' if len(m['content'])>50 else ''}")
                        with c3:
                            if st.button("🗑️", key=f"del_out_{m['id']}"):
                                chat_db.delete_message(m['id'])
                                st.rerun()
                        st.caption(f"🕐 {m['created_at']}")
                        st.markdown("---")

            col_del_all, col_clear = st.columns(2)
            with col_del_all:
                if st.button("🗑️ 清空全部消息", type="secondary", use_container_width=True):
                    chat_db.delete_all_messages()
                    st.rerun()
            with col_clear:
                if st.button("🚪 退出管理", use_container_width=True):
                    st.session_state.chat_admin_verified = False
                    st.session_state.chat_show_admin = False
                    st.rerun()

            # 用户记录
            st.subheader("👥 IP-用户记录")
            users = chat_db.get_all_users()
            if users:
                for u in users:
                    st.markdown(f"`{u['ip_address']}` → **{u['username']}** · {u['updated_at']}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# ==================== 用户名设置 ====================
if not st.session_state.chat_username:
    st.markdown("""
    <div class="lock-box">
        <span class="lock-icon">👤</span>
        <h3 style="color:#e0e0e0;">设置你的昵称</h3>
    </div>
    """, unsafe_allow_html=True)

    name_input = st.text_input("请输入用户名", key="username_input", placeholder="起个名字吧~",
                               max_chars=20)
    if st.button("✅ 进入聊天", use_container_width=True, disabled=not name_input.strip()):
        st.session_state.chat_username = name_input.strip()
        chat_db.save_ip_username(client_ip, name_input.strip())
        st.rerun()
    st.stop()

# ==================== 聊天主界面 ====================
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem;">
    <h2 style="margin:0;color:#e0e0e0;">💬 聊天室</h2>
    <span style="color:#90a4ae;font-size:0.85rem;">
        <span class="online-dot"></span>{st.session_state.chat_username}
    </span>
</div>
""", unsafe_allow_html=True)

# 消息展示区
st.markdown('<div class="chat-container" id="chat-box">', unsafe_allow_html=True)
messages = chat_db.get_messages(limit=100)
if not messages:
    st.markdown('<p style="color:#546e7a;text-align:center;padding:2rem;">还没有消息，来说点什么吧~</p>',
                unsafe_allow_html=True)
else:
    for msg in messages:
        is_self = (msg["username"] == st.session_state.chat_username)
        cls = "chat-msg self" if is_self else "chat-msg"
        st.markdown(f"""
        <div class="{cls}">
            <div class="meta">
                <span class="user">{msg['username']}</span>
                <span> · {msg['created_at']}</span>
            </div>
            <div class="text">{msg['content']}</div>
        </div>
        """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 消息输入区
col_input, col_send = st.columns([5, 1])
with col_input:
    new_msg = st.text_area("输入消息", key="chat_input", placeholder="输入消息... (Enter 发送)",
                           label_visibility="collapsed", height=68)
with col_send:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📨 发送", use_container_width=True):
        if new_msg.strip():
            chat_db.add_message(st.session_state.chat_username, new_msg.strip())
            st.rerun()

# Enter 键自动发送
st.markdown("""
<script>
    var input = window.parent.document.querySelector('[data-testid="stTextArea"] textarea');
    if (input) {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                var sendBtn = window.parent.document.querySelector('button[kind="primary"]');
                if (sendBtn) sendBtn.click();
            }
        });
    }
</script>
""", unsafe_allow_html=True)

# 底部操作栏
st.markdown("---")
col_refresh, col_logout, col_admin = st.columns(3)
with col_refresh:
    if st.button("🔄 刷新消息", use_container_width=True):
        st.rerun()
with col_logout:
    if st.button("🚪 退出聊天室", use_container_width=True):
        st.session_state.chat_unlocked = False
        st.session_state.chat_username = ""
        st.session_state.chat_admin_verified = False
        st.session_state.chat_show_admin = False
        st.rerun()
with col_admin:
    if st.button("🛠️ 管理", use_container_width=True):
        st.session_state.chat_show_admin = True
        st.rerun()

# ==================== 管理员面板 ====================
if st.session_state.chat_show_admin:
    st.markdown("---")
    st.markdown('<div class="admin-panel">', unsafe_allow_html=True)

    if not st.session_state.chat_admin_verified:
        st.subheader("🛡️ 管理员验证")
        admin_pwd = st.text_input("管理员密码", type="password", key="admin_pwd_inside",
                                  placeholder="输入管理员密码", autocomplete="new-password")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔑 验证", use_container_width=True):
                if admin_pwd == "root":
                    st.session_state.chat_admin_verified = True
                    st.rerun()
                else:
                    st.error("密码错误")
        with c2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.chat_show_admin = False
                st.rerun()
    else:
        st.success("✅ 管理员已登录")
        msg_count = chat_db.get_message_count()
        st.info(f"📊 共 **{msg_count}** 条消息")

        st.subheader("💬 消息列表")
        if msg_count > 0:
            msgs = chat_db.get_messages(limit=200)
            for m in reversed(msgs):
                with st.container():
                    c1, c2, c3 = st.columns([2, 5, 1])
                    with c1:
                        st.markdown(f"**{m['username']}**")
                    with c2:
                        st.markdown(f"{m['content'][:60]}{'...' if len(m['content'])>60 else ''}")
                    with c3:
                        if st.button("🗑️", key=f"del_in_{m['id']}"):
                            chat_db.delete_message(m['id'])
                            st.rerun()
                    st.caption(f"🕐 {m['created_at']}")
                    st.markdown("---")

        col_del_all, col_hide = st.columns(2)
        with col_del_all:
            if st.button("🗑️ 清空全部消息", type="secondary", use_container_width=True):
                chat_db.delete_all_messages()
                st.rerun()
        with col_hide:
            if st.button("🚪 关闭管理", use_container_width=True):
                st.session_state.chat_admin_verified = False
                st.session_state.chat_show_admin = False
                st.rerun()

        st.subheader("👥 IP-用户记录")
        users = chat_db.get_all_users()
        if users:
            for u in users:
                st.markdown(f"`{u['ip_address']}` → **{u['username']}** · {u['updated_at']}")

    st.markdown('</div>', unsafe_allow_html=True)

# 自动刷新（每 10 秒通过 JS 点击刷新按钮，不打断输入）
if st.session_state.chat_unlocked and st.session_state.chat_username:
    st.markdown("""
    <script>
        setTimeout(function() {
            var btns = window.parent.document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.includes('刷新')) {
                    btns[i].click();
                    break;
                }
            }
        }, 10000);
    </script>
    """, unsafe_allow_html=True)
