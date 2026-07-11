@echo off
:: ============================================================
:: QuantSeed 本地开发一键启动脚本（Windows）
:: ============================================================
:: 启动后端 API 和前端 Streamlit 两个服务

echo ========================================
echo   QuantSeed 开发环境启动
echo ========================================
echo.

cd /d %~dp0

:: 启动后端 API（新窗口）
echo [1/2] 启动后端 API (端口 8000)...
start "QuantSeed-API" cmd /c "cd /d %~dp0src && py -3.12 -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端 Streamlit（新窗口）
echo [2/2] 启动前端 Streamlit (端口 8501)...
start "QuantSeed-Streamlit" cmd /c "cd /d %~dp0src && py -3.12 -m streamlit run app.py --server.port 8501"

echo.
echo ========================================
echo   启动完成！
echo   后端 API:  http://localhost:8000/docs
echo   前端页面:  http://localhost:8501
echo ========================================
echo.
echo 按任意键关闭此窗口...
pause >nul
