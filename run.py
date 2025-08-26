#!/usr/bin/env python3
"""
Flask应用启动脚本 - 无数据库版本
"""

from src.app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)