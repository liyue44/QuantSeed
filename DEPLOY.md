# QuantSeed 阿里云部署完整指南

---

## 一、整体架构

```
┌──────────────────────────────────────────────────┐
│                   阿里云 ECS                       │
│                                                   │
│  ┌──────────────┐    ┌──────────────────────┐     │
│  │  Nginx       │───→│  Streamlit :8501     │     │
│  │  (反向代理)   │    │  (前端 Web 界面)      │     │
│  │  :80/:443    │    └───────┬──────────────┘     │
│  └──────────────┘            │ HTTP               │
│                              ↓                    │
│  ┌───────────────────────────────────────────┐   │
│  │            Docker 容器编排                  │   │
│  │  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │ FastAPI :8000 │  │ PostgreSQL :5432 │   │   │
│  │  │ (后端 API)    │  │ (数据库)          │   │   │
│  │  └──────────────┘  └──────────────────┘   │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  ┌───────────────────────────────────────────┐   │
│  │  数据卷 (Docker Volumes)                   │   │
│  │  - quantseed_data: CSV 日线数据            │   │
│  │  - quantseed_logs: 日志                   │   │
│  │  - postgres_data: PostgreSQL 数据          │   │
│  └───────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

---

## 二、阿里云 ECS 服务器配置建议

### 最低配置（学习/个人用）
| 项目 | 配置 |
|------|------|
| 实例规格 | 2 vCPU / 4 GB 内存 |
| 系统盘 | 40 GB 高效云盘 |
| 操作系统 | Ubuntu 22.04 LTS (推荐) 或 CentOS 8+ |
| 带宽 | 按量计费 5 Mbps |
| 安全组 | 开放 80, 443, 22 端口 |

### 安全组规则
| 端口 | 来源 | 用途 |
|------|------|------|
| 22 | 你的IP | SSH 远程连接 |
| 80 | 0.0.0.0/0 | HTTP 访问 |
| 443 | 0.0.0.0/0 | HTTPS 访问 |
| 8000 | 127.0.0.1 | API（仅内部） |
| 8501 | 127.0.0.1 | Streamlit（仅内部） |
| 5432 | 127.0.0.1 | PostgreSQL（仅内部） |

> ⚠️ **安全提示**：8000、8501、5432 只对内网开放，不要暴露到公网！

---

## 三、服务器环境安装（一次性）

SSH 连接到 ECS 后，按顺序执行：

### 3.1 安装 Docker
```bash
# Ubuntu
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
# 退出重新登录使权限生效

# 安装 docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证
docker --version
docker-compose --version
```

### 3.2 安装 Git
```bash
sudo apt update && sudo apt install -y git
```

### 3.3 创建项目目录
```bash
mkdir -p /opt/quantseed
cd /opt/quantseed
```

---

## 四、部署项目

### 4.1 从 Git 拉取代码
```bash
cd /opt/quantseed
git clone https://github.com/你的用户名/QuantSeed.git .
# 或从本地直接 scp 上传
```

### 4.2 配置环境变量
```bash
# 复制并修改环境变量
cp .env.example .env
nano .env   # 修改为生产环境配置
```

生产环境 `.env` 内容：
```ini
DB_TYPE=postgresql
PG_HOST=postgres
PG_PORT=5432
PG_USER=quantseed
PG_PASSWORD=你的安全密码
PG_DATABASE=quantseed
API_BASE_URL=http://api:8000
LOG_LEVEL=INFO
```

### 4.3 启动服务
```bash
# 开发模式（仅后端 + Streamlit，SQLite）
docker-compose up -d

# 生产模式（含 PostgreSQL）
docker-compose --profile production up -d

# 查看日志
docker-compose logs -f
```

### 4.4 验证服务
```bash
# 后端 API
curl http://localhost:8000/api/health

# 前端
curl http://localhost:8501
```

---

## 五、Nginx 反向代理配置

### 5.1 安装 Nginx
```bash
sudo apt install -y nginx
```

### 5.2 创建配置
```bash
sudo nano /etc/nginx/sites-available/quantseed
```

```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    client_max_body_size 50M;

    # 主应用（Streamlit 前端）
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Streamlit WebSocket
    location /_stcore/stream {
        proxy_pass http://127.0.0.1:8501/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # API 后端（可选，直接代理）
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 5.3 启用并重启
```bash
sudo ln -s /etc/nginx/sites-available/quantseed /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 六、数据初始化

### 首次启动后下载历史数据
```bash
# 进入 API 容器执行数据下载
docker exec -it quantseed-api python -c "
from api_server import app
from database import init_db
init_db()
print('数据库初始化完成')
"

# 下载全部股票历史数据（约10分钟）
curl -X POST http://localhost:8000/api/data/download
```

---

## 七、设置开机自启

docker-compose 已配置 `restart: unless-stopped`，但建议：

```bash
# 创建 systemd 服务
sudo nano /etc/systemd/system/quantseed.service
```

```ini
[Unit]
Description=QuantSeed Docker Compose Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/quantseed
ExecStart=/usr/local/bin/docker-compose --profile production up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable quantseed
```

---

## 八、更新部署流程

以后每次修改代码后：

```bash
# 本地推送到 Git
git add .
git commit -m "更新说明"
git push origin main

# 服务器拉取并重启
ssh your-server
cd /opt/quantseed
git pull
docker-compose --profile production down
docker-compose --profile production up -d --build
```

---

## 九、费用预估（阿里云）

| 项目 | 月费（约） |
|------|-----------|
| ECS 2核4G | ~¥120 |
| 系统盘 40GB | ~¥14 |
| 带宽 5Mbps（按量） | ~¥120 |
| **合计** | **~¥254/月** |

> 💡 使用抢占式实例或新人优惠可降至 ~¥60/月

---

## 十、数据库方案说明

### 开发环境（本地）：SQLite
- 零配置，文件即数据库
- 数据存储在 `data/quantseed.db`
- 适合单用户、个人使用

### 生产环境（阿里云）：PostgreSQL
- 通过 docker-compose 一键启动
- 支持并发读写、数据备份
- 为第二阶段多用户、实盘交易做准备

### 数据库表结构
| 表名 | 用途 | 数据量 |
|------|------|--------|
| `stock_info` | 股票基本信息 | 35行 |
| `daily_data` | 日线行情 | ~70,000行 |
| `signal_records` | 交易信号 | 动态增长 |
| `backtest_results` | 回测结果 | 按需增长 |
| `system_config` | 系统配置 | ~10行 |
