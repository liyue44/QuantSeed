#!/bin/bash
# ============================================================
# QuantSeed 本地开发一键启动脚本（Linux/Mac）
# ============================================================

cd "$(dirname "$0")"

echo "========================================"
echo "  QuantSeed 开发环境启动"
echo "========================================"
echo ""

# 安装依赖（如果需要）
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 初始化数据库
echo "[1/3] 初始化数据库..."
cd src
python3 -c "from database import init_db; init_db(); print('数据库初始化完成')"

# 启动后端 API（后台）
echo "[2/3] 启动后端 API (端口 8000)..."
python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# 等待后端启动
sleep 3

# 启动前端 Streamlit（后台）
echo "[3/3] 启动前端 Streamlit (端口 8501)..."
python3 -m streamlit run app.py --server.port 8501 &
ST_PID=$!

echo ""
echo "========================================"
echo "  启动完成！"
echo "  后端 API:  http://localhost:8000/docs"
echo "  前端页面:  http://localhost:8501"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待并捕获退出信号
trap "echo '正在停止服务...'; kill $API_PID $ST_PID; exit 0" INT TERM
wait
