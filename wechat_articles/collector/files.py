from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import json
from wechat_articles.core.logger import get_logger

logger = get_logger(__name__)
bp = Blueprint('files', __name__)

ARTICLES_DIR = Path('articles')

@bp.route('/accounts', methods=['GET'])
def get_accounts():
    """获取所有账号列表（从文件系统读取）"""
    try:
        accounts = []
        
        if ARTICLES_DIR.exists():
            for account_dir in ARTICLES_DIR.iterdir():
                if account_dir.is_dir():
                    account_info = _get_account_info(account_dir)
                    accounts.append(account_info)
        
        return jsonify({
            'success': True,
            'data': {
                'accounts': accounts,
                'total_accounts': len(accounts)
            }
        })
        
    except Exception as e:
        logger.error(f'获取账号列表失败: {e}')
        return jsonify({
            'success': False,
            'message': '获取账号列表失败'
        }), 500

@bp.route('/accounts/<account_name>/articles', methods=['GET'])
def get_account_articles(account_name):
    """获取指定账号的文章列表"""
    try:
        account_dir = ARTICLES_DIR / account_name
        if not account_dir.exists():
            return jsonify({
                'success': False,
                'message': '账号不存在'
            }), 404
        
        articles = []
        
        # 查找所有JSON文件
        for json_file in account_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    article_data = json.load(f)
                    
                    # 检查是否有对应的HTML文件
                    html_file = json_file.with_suffix('.html')
                    article_data['has_content'] = html_file.exists()
                    article_data['filename'] = json_file.stem
                    
                    articles.append(article_data)
                    
            except Exception as e:
                logger.warning(f"读取文章文件失败 {json_file}: {e}")
                continue
        
        # 按发布时间排序
        articles.sort(key=lambda x: x.get('publish_time', ''), reverse=True)
        
        # 分页
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_articles = articles[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'data': {
                'articles': paginated_articles,
                'total': len(articles),
                'page': page,
                'per_page': per_page,
                'pages': (len(articles) + per_page - 1) // per_page,
                'account_name': account_name
            }
        })
        
    except Exception as e:
        logger.error(f'获取账号文章失败: {e}')
        return jsonify({
            'success': False,
            'message': '获取账号文章失败'
        }), 500

@bp.route('/accounts/<account_name>/articles/<filename>/content', methods=['GET'])
def get_article_content(account_name, filename):
    """获取文章HTML内容"""
    try:
        html_file = ARTICLES_DIR / account_name / f"{filename}.html"
        json_file = ARTICLES_DIR / account_name / f"{filename}.json"
        
        if not html_file.exists():
            return jsonify({
                'success': False,
                'message': '文章内容文件不存在'
            }), 404
        
        # 读取HTML内容
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 读取元数据
        metadata = {}
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': {
                'account_name': account_name,
                'filename': filename,
                'content': content,
                'metadata': metadata
            }
        })
        
    except Exception as e:
        logger.error(f'获取文章内容失败: {e}')
        return jsonify({
            'success': False,
            'message': '获取文章内容失败'
        }), 500

@bp.route('/accounts/<account_name>/articles/<filename>/download', methods=['GET'])
def download_article(account_name, filename):
    """下载文章文件"""
    try:
        file_type = request.args.get('type', 'html')
        
        if file_type == 'html':
            file_path = ARTICLES_DIR / account_name / f"{filename}.html"
            mimetype = 'text/html'
        elif file_type == 'json':
            file_path = ARTICLES_DIR / account_name / f"{filename}.json"
            mimetype = 'application/json'
        else:
            return jsonify({
                'success': False,
                'message': '不支持的文件类型'
            }), 400
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"{account_name}_{filename}.{file_type}",
            mimetype=mimetype
        )
        
    except Exception as e:
        logger.error(f'下载文章文件失败: {e}')
        return jsonify({
            'success': False,
            'message': '下载文件失败'
        }), 500

@bp.route('/accounts/<account_name>/articles/<filename>', methods=['DELETE'])
def delete_article(account_name, filename):
    """删除文章文件"""
    try:
        html_file = ARTICLES_DIR / account_name / f"{filename}.html"
        json_file = ARTICLES_DIR / account_name / f"{filename}.json"
        
        deleted_files = []
        
        if html_file.exists():
            html_file.unlink()
            deleted_files.append('html')
        
        if json_file.exists():
            json_file.unlink()
            deleted_files.append('json')
        
        if not deleted_files:
            return jsonify({
                'success': False,
                'message': '文章文件不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'message': f'文章已删除 ({", ".join(deleted_files)})',
            'data': {
                'deleted_files': deleted_files
            }
        })
        
    except Exception as e:
        logger.error(f'删除文章失败: {e}')
        return jsonify({
            'success': False,
            'message': '删除文章失败'
        }), 500

@bp.route('/storage/stats', methods=['GET'])
def get_storage_stats():
    """获取存储统计信息"""
    try:
        stats = {
            'total_accounts': 0,
            'total_articles': 0,
            'total_size_mb': 0
        }
        
        if ARTICLES_DIR.exists():
            for account_dir in ARTICLES_DIR.iterdir():
                if account_dir.is_dir():
                    stats['total_accounts'] += 1
                    
                    for file_path in account_dir.iterdir():
                        if file_path.is_file():
                            if file_path.suffix == '.json':
                                stats['total_articles'] += 1
                            stats['total_size_mb'] += file_path.stat().st_size / (1024 * 1024)
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f'获取存储统计失败: {e}')
        return jsonify({
            'success': False,
            'message': '获取存储统计失败'
        }), 500

def _get_account_info(account_dir):
    """获取账号信息"""
    account_name = account_dir.name
    article_count = len(list(account_dir.glob('*.json')))
    
    # 计算目录大小
    total_size = sum(f.stat().st_size for f in account_dir.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    
    # 获取最后更新时间
    last_modified = None
    json_files = list(account_dir.glob('*.json'))
    if json_files:
        latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_modified = data.get('collected_at', '')
        except:
            pass
    
    return {
        'account_name': account_name,
        'article_count': article_count,
        'local_article_count': article_count,
        'local_size_mb': round(size_mb, 2),
        'last_article_time': last_modified
    }