"""
聊天室数据库操作
- 消息表：用户名、内容、时间
- IP-用户名映射表：记录每个IP最近使用的用户名
"""

import sqlite3
import os
import threading
import urllib.request
from datetime import datetime
from typing import Optional

# Server酱 配置（支持多个 SendKey，每个绑定不同微信）
SERVERCHAN_KEYS = [
    "SCT380382TbqIkbYMgw8jBSOGI11qVrlSG",
    "SCT383900Tum2I3oxcTN586XMDa2HqOP2K",
]

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "chatroom.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化聊天室数据库表"""
    conn = _get_conn()
    cur = conn.cursor()
    # 消息表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    # IP-用户名映射表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ip_usernames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


def _send_wx_notification(username: str, content: str):
    """通过 Server酱 发送微信通知到所有配置的微信（异步，不阻塞）"""
    title = f"💬 [{username}] 发来新消息"
    short_content = content[:100] + ("..." if len(content) > 100 else "")
    desp = f"## {username} 说：\n\n> {short_content}"
    for key in SERVERCHAN_KEYS:
        try:
            url = f"https://sctapi.ftqq.com/{key}.send"
            data = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # 单个 Key 失败不影响其他 Key 和主流程


def add_message(username: str, content: str) -> dict:
    """添加一条聊天消息"""
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO chat_messages (username, content, created_at) VALUES (?, ?, ?)",
        (username.strip(), content.strip(), now)
    )
    conn.commit()
    msg_id = cur.lastrowid
    conn.close()
    # 异步发送微信通知
    threading.Thread(target=_send_wx_notification, args=(username.strip(), content.strip()), daemon=True).start()
    return {"id": msg_id, "username": username.strip(), "content": content.strip(), "created_at": now}


def get_messages(limit: int = 100, offset: int = 0) -> list:
    """获取最近的聊天消息"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM chat_messages ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_message_count() -> int:
    """获取消息总数"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM chat_messages")
    count = cur.fetchone()[0]
    conn.close()
    return count


def delete_message(msg_id: int):
    """删除一条消息"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()


def delete_all_messages():
    """清空所有消息"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_messages")
    conn.commit()
    conn.close()


def save_ip_username(ip_address: str, username: str):
    """记录IP地址对应的用户名"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ip_usernames (ip_address, username, updated_at)
        VALUES (?, ?, datetime('now','localtime'))
        ON CONFLICT(ip_address) DO UPDATE SET
            username = excluded.username,
            updated_at = datetime('now','localtime')
    """, (ip_address, username.strip()))
    conn.commit()
    conn.close()


def get_username_by_ip(ip_address: str) -> Optional[str]:
    """根据IP地址获取最近使用的用户名"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username FROM ip_usernames WHERE ip_address = ?", (ip_address,))
    row = cur.fetchone()
    conn.close()
    return row["username"] if row else None


def get_all_users() -> list:
    """获取所有IP-用户名映射"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ip_usernames ORDER BY updated_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# 初始化表
init_db()
