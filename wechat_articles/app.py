from flask import Flask
from flask_cors import CORS
from wechat_articles.core.logger import get_logger

logger = get_logger(__name__)

def create_app():
    """创建Flask应用 - 无数据库版本"""
    app = Flask(__name__)
    
    # 基本配置
    app.config['SECRET_KEY'] = 'wechat-collector-no-db'
    
    # 启用CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # 注册路由
    from src.api.routes.collectors import bp as collectors_bp
    from src.api.routes.files import bp as files_bp
    
    app.register_blueprint(collectors_bp, url_prefix='/api/collectors')
    app.register_blueprint(files_bp, url_prefix='/api/files')
    
    @app.route('/health')
    def health_check():
        """健康检查"""
        return {'status': 'ok', 'version': 'no-db-version'}
    
    @app.route('/')
    def index():
        """主页"""
        return {
            'message': '微信公众号采集系统 - 无数据库版本',
            'endpoints': {
                'health': '/health',
                'collectors': '/api/collectors',
                'files': '/api/files'
            }
        }
    
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info("启动微信采集系统 - 无数据库版本")
    app.run(host='0.0.0.0', port=5000, debug=True)