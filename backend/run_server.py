import subprocess
import threading
from app import app
import os
import sys


def start_frontend():
    """启动前端服务器"""
    try:
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web_frontend')
        print(f"启动前端服务器... 端口 8082")
        subprocess.run([sys.executable, '-m', 'http.server', '8082', '--bind', '127.0.0.1'],
                      cwd=frontend_path, check=True)
    except subprocess.CalledProcessError as e:
        print(f"前端服务器启动失败: {e}")
    except KeyboardInterrupt:
        print("前端服务器已停止")


def start_backend():
    """启动后端服务器"""
    try:
        print(f"启动后端服务器... 端口 5000")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("后端服务器已停止")


if __name__ == '__main__':
    # 启动前端服务器线程
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    frontend_thread.start()
    
    # 启动后端服务器（主线程）
    start_backend()
