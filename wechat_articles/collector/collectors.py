from flask import Blueprint, request, jsonify
from src.collectors.wechat.article_collector import WechatArticleCollector
from src.collectors.account_monitor import account_monitor
from wechat_articles.core.logger import get_logger
import threading
import time
from datetime import datetime

logger = get_logger(__name__)
bp = Blueprint('collectors', __name__)

# 全局采集器实例管理
active_collectors = {}

@bp.route('/wechat/collect', methods=['POST'])
def collect_wechat_articles():
    """采集微信公众号文章"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        account_name = data.get('account_name', '').strip()
        if not account_name:
            return jsonify({
                'success': False,
                'message': '公众号名称不能为空'
            }), 400
        
        max_articles = data.get('max_articles', 20)
        is_async = data.get('async', False)
        
        if is_async:
            # 异步采集
            collector_key = f"collector_{int(time.time())}_{id(data)}"
            
            def run_collection():
                collector = WechatArticleCollector()
                active_collectors[collector_key] = {
                    'status': 'running',
                    'collector': collector,
                    'start_time': datetime.now(),
                    'account_name': account_name,
                    'max_articles': max_articles
                }
                
                try:
                    articles = collector.collect_articles(account_name, max_articles)
                    active_collectors[collector_key]['status'] = 'completed'
                    active_collectors[collector_key]['result'] = {
                        'articles_count': len(articles),
                        'articles': [
                            {
                                'title': a['title'],
                                'author': a.get('author', ''),
                                'publish_time': a.get('publish_time', ''),
                                'url': a['url']
                            } for a in articles[:5]  # 只返回前5篇预览
                        ],
                        'stats': collector.get_collection_stats()
                    }
                except Exception as e:
                    active_collectors[collector_key]['status'] = 'failed'
                    active_collectors[collector_key]['error'] = str(e)
                    logger.error(f"异步采集失败: {e}")
            
            thread = threading.Thread(target=run_collection, daemon=True)
            thread.start()
            
            return jsonify({
                'success': True,
                'message': '异步采集任务已启动',
                'data': {
                    'collector_key': collector_key,
                    'account_name': account_name,
                    'max_articles': max_articles
                }
            })
        
        else:
            # 同步采集
            collector = WechatArticleCollector()
            articles = collector.collect_articles(account_name, max_articles)
            
            return jsonify({
                'success': True,
                'message': f'采集完成，共采集 {len(articles)} 篇文章',
                'data': {
                    'articles_count': len(articles),
                    'articles': [
                        {
                            'title': a['title'],
                            'author': a.get('author', ''),
                            'publish_time': a.get('publish_time', ''),
                            'url': a['url']
                        } for a in articles[:10]  # 返回前10篇预览
                    ],
                    'stats': collector.get_collection_stats()
                }
            })
        
    except Exception as e:
        logger.error(f'采集文章失败: {e}')
        return jsonify({
            'success': False,
            'message': '采集文章失败',
            'error': str(e)
        }), 500

@bp.route('/status/<collector_key>', methods=['GET'])
def get_collector_status(collector_key):
    """获取采集器状态"""
    try:
        if collector_key not in active_collectors:
            return jsonify({
                'success': False,
                'message': '采集器不存在'
            }), 404
        
        collector_info = active_collectors[collector_key]
        
        result = {
            'success': True,
            'data': {
                'collector_key': collector_key,
                'status': collector_info['status'],
                'account_name': collector_info['account_name'],
                'max_articles': collector_info['max_articles'],
                'start_time': collector_info['start_time'].isoformat()
            }
        }
        
        if 'result' in collector_info:
            result['data']['result'] = collector_info['result']
        
        if 'error' in collector_info:
            result['data']['error'] = collector_info['error']
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取采集器状态失败: {e}')
        return jsonify({
            'success': False,
            'message': '获取状态失败'
        }), 500

@bp.route('/wechat/collect-export', methods=['POST'])
def collect_and_export_wechat_articles():
    """采集微信公众号文章并导出为PDF/Word"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        account_name = data.get('account_name', '').strip()
        if not account_name:
            return jsonify({
                'success': False,
                'message': '公众号名称不能为空'
            }), 400
        
        max_articles = data.get('max_articles', 20)
        export_formats = data.get('export_formats', ['pdf', 'docx'])
        is_async = data.get('async', False)
        
        if is_async:
            # 异步采集导出
            collector_key = f"export_{int(time.time())}_{id(data)}"
            
            def run_collection_export():
                collector = WechatArticleCollector()
                active_collectors[collector_key] = {
                    'status': 'running',
                    'collector': collector,
                    'start_time': datetime.now(),
                    'account_name': account_name,
                    'max_articles': max_articles,
                    'export_formats': export_formats
                }
                
                try:
                    result = collector.collect_and_export_articles(
                        account_name, max_articles, export_formats
                    )
                    active_collectors[collector_key]['status'] = 'completed'
                    active_collectors[collector_key]['result'] = result
                except Exception as e:
                    active_collectors[collector_key]['status'] = 'failed'
                    active_collectors[collector_key]['error'] = str(e)
                    logger.error(f"异步采集导出失败: {e}")
            
            thread = threading.Thread(target=run_collection_export, daemon=True)
            thread.start()
            
            return jsonify({
                'success': True,
                'message': '异步采集导出任务已启动',
                'data': {
                    'collector_key': collector_key,
                    'account_name': account_name,
                    'max_articles': max_articles,
                    'export_formats': export_formats
                }
            })
        
        else:
            # 同步采集导出
            collector = WechatArticleCollector()
            result = collector.collect_and_export_articles(
                account_name, max_articles, export_formats
            )
            
            return jsonify({
                'success': True,
                'message': result.get('message', '采集导出完成'),
                'data': result
            })
        
    except Exception as e:
        logger.error(f'采集导出文章失败: {e}')
        return jsonify({
            'success': False,
            'message': '采集导出文章失败',
            'error': str(e)
        }), 500

@bp.route('/monitor/accounts', methods=['POST'])
def add_account_monitor():
    """添加账号监控"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        account_name = data.get('account_name', '').strip()
        if not account_name:
            return jsonify({
                'success': False,
                'message': '账号名称不能为空'
            }), 400
        
        config = {
            'check_interval_minutes': data.get('check_interval_minutes', 30),
            'max_articles_per_check': data.get('max_articles_per_check', 10),
            'export_formats': data.get('export_formats', ['pdf', 'docx']),
            'enabled': data.get('enabled', True)
        }
        
        success = account_monitor.add_account_monitor(account_name, config)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'已添加账号监控: {account_name}',
                'data': {
                    'account_name': account_name,
                    'config': config
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '添加账号监控失败'
            }), 500
        
    except Exception as e:
        logger.error(f'添加账号监控失败: {e}')
        return jsonify({
            'success': False,
            'message': '添加账号监控失败'
        }), 500

@bp.route('/monitor/accounts/<account_name>', methods=['DELETE'])
def remove_account_monitor(account_name):
    """移除账号监控"""
    try:
        success = account_monitor.remove_account_monitor(account_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'已移除账号监控: {account_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': '账号监控不存在'
            }), 404
        
    except Exception as e:
        logger.error(f'移除账号监控失败: {e}')
        return jsonify({
            'success': False,
            'message': '移除账号监控失败'
        }), 500

@bp.route('/monitor/accounts/<account_name>/toggle', methods=['PUT'])
def toggle_account_monitor(account_name):
    """启用/禁用账号监控"""
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', True)
        
        success = account_monitor.enable_account_monitor(account_name, enabled)
        
        if success:
            action = '启用' if enabled else '禁用'
            return jsonify({
                'success': True,
                'message': f'已{action}账号监控: {account_name}',
                'data': {
                    'account_name': account_name,
                    'enabled': enabled
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '账号监控不存在'
            }), 404
        
    except Exception as e:
        logger.error(f'切换账号监控状态失败: {e}')
        return jsonify({
            'success': False,
            'message': '操作失败'
        }), 500

@bp.route('/monitor/status', methods=['GET'])
def get_monitor_status():
    """获取监控状态"""
    try:
        account_name = request.args.get('account_name')
        status = account_monitor.get_monitor_status(account_name)
        
        if account_name and status is None:
            return jsonify({
                'success': False,
                'message': '账号监控不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f'获取监控状态失败: {e}')
        return jsonify({
            'success': False,
            'message': '获取监控状态失败'
        }), 500

@bp.route('/monitor/accounts/<account_name>/check', methods=['POST'])
def force_check_account(account_name):
    """强制检查账号更新"""
    try:
        success = account_monitor.force_check_account(account_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'已强制检查账号: {account_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': '账号未被监控或检查失败'
            }), 400
        
    except Exception as e:
        logger.error(f'强制检查账号失败: {e}')
        return jsonify({
            'success': False,
            'message': '强制检查失败'
        }), 500

@bp.route('/list', methods=['GET'])
def list_active_collectors():
    """列出所有活跃的采集器"""
    try:
        collectors_list = []
        current_time = datetime.now()
        
        # 清理超过1小时的旧采集器
        keys_to_remove = []
        for key, info in active_collectors.items():
            duration = (current_time - info['start_time']).total_seconds()
            if duration > 3600:  # 1小时
                keys_to_remove.append(key)
            else:
                collectors_list.append({
                    'collector_key': key,
                    'status': info['status'],
                    'account_name': info['account_name'],
                    'start_time': info['start_time'].isoformat(),
                    'duration_seconds': int(duration)
                })
        
        # 删除过期的采集器
        for key in keys_to_remove:
            del active_collectors[key]
        
        return jsonify({
            'success': True,
            'data': {
                'active_collectors': collectors_list,
                'total_count': len(collectors_list)
            }
        })
        
    except Exception as e:
        logger.error(f'获取采集器列表失败: {e}')
        return jsonify({
            'success': False,
            'message': '获取列表失败'
        }), 500