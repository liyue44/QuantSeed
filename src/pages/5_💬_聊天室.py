"""
聊天室模块
- 门锁密码验证（默认 135246）
- 每个浏览器窗口独立设置用户名（用 streamlit session_id 区分）
- 本机消息右侧，他人消息左侧（类似微信）
- 每 5 秒自动刷新
- 管理员面板（密码 root）
"""

import streamlit as st
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chat_db

# ==================== 页面配置 ====================
st.set_page_config(page_title="聊天室", page_icon="💬", layout="centered")

# ==================== 获取/生成唯一 session_id ====================
def get_session_id() -> str:
    """获取当前浏览器窗口的唯一ID"""
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx = get_script_run_ctx()
    if ctx:
        return ctx.session_id
    # fallback
    if "_chat_sid" not in st.session_state:
        st.session_state._chat_sid = str(uuid.uuid4())
    return st.session_state._chat_sid

my_sid = get_session_id()

# ==================== Session State ====================
if "chat_unlocked" not in st.session_state:
    st.session_state.chat_unlocked = False
if "chat_show_admin" not in st.session_state:
    st.session_state.chat_show_admin = False
if "chat_admin_verified" not in st.session_state:
    st.session_state.chat_admin_verified = False

# 每个 session_id 独立的用户名 key
_uname_key = f"_chat_uname_{my_sid}"
if _uname_key not in st.session_state:
    st.session_state[_uname_key] = ""

my_username = st.session_state[_uname_key]

# ==================== CSS ====================
st.markdown("""
<style>
    /* === 聊天容器 === */
    .chat-wrapper {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        background: rgba(255,255,255,0.02);
        padding: 0.8rem;
        max-height: 58vh;
        overflow-y: auto;
        margin-bottom: 0.8rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    /* === 消息气泡（他人 / 左侧） === */
    .chat-bubble {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        max-width: 78%;
    }
    .chat-bubble .bubble-box {
        background: rgba(79, 195, 247, 0.1);
        border: 1px solid rgba(79, 195, 247, 0.15);
        border-radius: 4px 14px 14px 14px;
        padding: 0.55rem 0.85rem;
        color: #e0e0e0;
        word-break: break-word;
        line-height: 1.5;
        font-size: 0.92rem;
    }
    .chat-bubble .bubble-meta {
        font-size: 0.7rem;
        color: #607d8b;
        margin-bottom: 0.15rem;
        padding-left: 0.3rem;
    }
    .chat-bubble .bubble-meta .sender {
        color: #4fc3f7;
        font-weight: 600;
    }

    /* === 自己的消息（右侧） === */
    .chat-bubble.self {
        align-self: flex-end;
        align-items: flex-end;
    }
    .chat-bubble.self .bubble-box {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.25), rgba(118, 75, 162, 0.2));
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 14px 4px 14px 14px;
    }
    .chat-bubble.self .bubble-meta {
        padding-left: 0;
        padding-right: 0.3rem;
    }
    .chat-bubble.self .bubble-meta .sender {
        color: #b39ddb;
    }

    /* === 系统消息 === */
    .chat-system {
        text-align: center;
        font-size: 0.75rem;
        color: #546e7a;
        padding: 0.3rem;
    }

    /* === 门锁盒子 === */
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

    /* === 管理员面板 === */
    .admin-panel {
        background: rgba(255,152,0,0.06);
        border: 1px solid rgba(255,152,0,0.25);
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
    }

    /* === 输入区 === */
    .input-row {
        display: flex;
        gap: 0.5rem;
        align-items: flex-end;
    }

    /* === 移动端 === */
    @media (max-width: 768px) {
        .lock-box { margin: 1.5rem auto; padding: 1.5rem; }
        .chat-wrapper { max-height: 50vh; }
        .chat-bubble { max-width: 90%; }
    }
</style>
""", unsafe_allow_html=True)


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
                st.rerun()
            else:
                st.error("密码错误")

    # 管理员入口
    st.markdown("<br>", unsafe_allow_html=True)
    col_admin_btn, _ = st.columns([1, 3])
    with col_admin_btn:
        if st.button("🛠️", key="tiny_admin_btn", help="管理员入口"):
            st.session_state.chat_show_admin = True
            st.rerun()

    # 管理员面板（未进入聊天室时也可访问）
    if st.session_state.chat_show_admin:
        st.markdown("---")
        st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
        if not st.session_state.chat_admin_verified:
            admin_pwd = st.text_input("管理员密码", type="password", key="admin_pwd_outside",
                                      placeholder="输入管理员密码", autocomplete="new-password")
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
                msgs = chat_db.get_messages(limit=200)
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
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


# ==================== 用户名设置（每个浏览器窗口独立） ====================
if not my_username:
    st.markdown("""
    <div class="lock-box">
        <span class="lock-icon">👤</span>
        <h3 style="color:#e0e0e0;">设置你的昵称</h3>
        <p style="color:#90a4ae; font-size:0.85rem;">每个人都需要输入自己的昵称</p>
    </div>
    """, unsafe_allow_html=True)

    name_input = st.text_input("请输入用户名", key="username_input", placeholder="起个名字吧~",
                               max_chars=20)
    if st.button("✅ 进入聊天", use_container_width=True, disabled=not name_input.strip()):
        st.session_state[_uname_key] = name_input.strip()
        st.rerun()
    st.stop()


# ==================== 聊天主界面 ====================
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem;">
    <h2 style="margin:0;color:#e0e0e0;">💬 聊天室</h2>
    <span style="color:#90a4ae;font-size:0.85rem;">
        🟢 {my_username}
    </span>
</div>
""", unsafe_allow_html=True)

# 消息展示区
st.markdown('<div class="chat-wrapper" id="chat-box">', unsafe_allow_html=True)
messages = chat_db.get_messages(limit=200)
if not messages:
    st.markdown('<p style="color:#546e7a;text-align:center;padding:2rem;">还没有消息，来说点什么吧~</p>',
                unsafe_allow_html=True)
else:
    for msg in messages:
        is_self = (msg["username"] == my_username)
        cls = "chat-bubble self" if is_self else "chat-bubble"
        st.markdown(f"""
        <div class="{cls}">
            <div class="bubble-meta">
                <span class="sender">{msg['username']}</span>
                &nbsp;·&nbsp;{msg['created_at']}
            </div>
            <div class="bubble-box">{msg['content']}</div>
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
            chat_db.add_message(my_username, new_msg.strip())
            st.session_state["_chat_last_count"] = chat_db.get_message_count()
            st.rerun()

# Enter 发送 + 自动滚动到底部 + 每 1 秒自动刷新（不在输入时不打断）
st.markdown("""
<script>
    var _chatInputFocused = false;

    // === 追踪输入框焦点 ===
    (function() {
        var input = window.parent.document.querySelector('[data-testid="stTextArea"] textarea');
        if (input) {
            input.addEventListener('focus', function() { _chatInputFocused = true; });
            input.addEventListener('blur', function() { _chatInputFocused = false; });
        }
    })();

    // === Enter 发送 ===
    (function() {
        var input = window.parent.document.querySelector('[data-testid="stTextArea"] textarea');
        if (input && !input._enterBound) {
            input._enterBound = true;
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    _chatInputFocused = false;
                    var btns = window.parent.document.querySelectorAll('button');
                    for (var i = 0; i < btns.length; i++) {
                        if (btns[i].textContent.includes('发送')) {
                            btns[i].click();
                            break;
                        }
                    }
                }
            });
        }
    })();

    // === 滚动到底部 ===
    setTimeout(function() {
        var box = document.getElementById('chat-box');
        if (box) { box.scrollTop = box.scrollHeight; }
    }, 300);

    // === 每 1 秒自动刷新（仅在未输入时刷新，不打断用户） ===
    setInterval(function() {
        if (_chatInputFocused) return;  // 正在输入时不刷新
        var btns = window.parent.document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.includes('刷新')) {
                btns[i].click();
                break;
            }
        }
    }, 1000);
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
        st.session_state[_uname_key] = ""
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
            msgs = chat_db.get_messages(limit=500)
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

    st.markdown('</div>', unsafe_allow_html=True)
