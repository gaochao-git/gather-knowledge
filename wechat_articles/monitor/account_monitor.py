import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import json
from wechat_articles.collector.article_collector import WechatArticleCollector
from wechat_articles.core.logger import get_logger

logger = get_logger(__name__)

class AccountMonitor:
    """账号监控器 - 定期检查账号新文章"""
    
    def __init__(self):
        self.monitored_accounts = {}  # {account_name: monitor_config}
        self.monitor_thread = None
        self.running = False
        self.monitor_data_file = Path('data/monitor_config.json')
        self.monitor_data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载监控配置
        self._load_monitor_config()
    
    def add_account_monitor(self, account_name, config):
        """
        添加账号监控
        
        Args:
            account_name: 公众号名称
            config: 监控配置
                - check_interval_minutes: 检查间隔（分钟）
                - max_articles_per_check: 每次检查最大采集数
                - export_formats: 导出格式列表
                - enabled: 是否启用
        """
        try:
            monitor_config = {
                'account_name': account_name,
                'check_interval_minutes': config.get('check_interval_minutes', 30),
                'max_articles_per_check': config.get('max_articles_per_check', 10),
                'export_formats': config.get('export_formats', ['pdf', 'docx']),
                'enabled': config.get('enabled', True),
                'created_at': datetime.now().isoformat(),
                'last_check_time': None,
                'total_collected': 0,
                'error_count': 0,
                'last_error': None
            }
            
            self.monitored_accounts[account_name] = monitor_config
            self._save_monitor_config()
            
            # 启动监控线程
            if not self.running:
                self.start_monitoring()
            
            logger.info(f"添加账号监控: {account_name}, 间隔: {monitor_config['check_interval_minutes']}分钟")
            return True
            
        except Exception as e:
            logger.error(f"添加账号监控失败: {e}")
            return False
    
    def remove_account_monitor(self, account_name):
        """移除账号监控"""
        try:
            if account_name in self.monitored_accounts:
                del self.monitored_accounts[account_name]
                self._save_monitor_config()
                logger.info(f"移除账号监控: {account_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"移除账号监控失败: {e}")
            return False
    
    def enable_account_monitor(self, account_name, enabled=True):
        """启用/禁用账号监控"""
        try:
            if account_name in self.monitored_accounts:
                self.monitored_accounts[account_name]['enabled'] = enabled
                self._save_monitor_config()
                action = "启用" if enabled else "禁用"
                logger.info(f"{action}账号监控: {account_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"切换账号监控状态失败: {e}")
            return False
    
    def start_monitoring(self):
        """启动监控服务"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("账号监控服务已启动")
    
    def stop_monitoring(self):
        """停止监控服务"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("账号监控服务已停止")
    
    def _monitor_loop(self):
        """监控主循环"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for account_name, config in list(self.monitored_accounts.items()):
                    if not config.get('enabled', True):
                        continue
                    
                    # 检查是否到达检查时间
                    last_check = config.get('last_check_time')
                    interval_minutes = config.get('check_interval_minutes', 30)
                    
                    if last_check:
                        last_check_time = datetime.fromisoformat(last_check)
                        if current_time - last_check_time < timedelta(minutes=interval_minutes):
                            continue
                    
                    # 执行检查
                    logger.info(f"开始检查账号: {account_name}")
                    self._check_account_updates(account_name, config)
                
                # 休眠1分钟后继续检查
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(60)
    
    def _check_account_updates(self, account_name, config):
        """检查账号更新"""
        try:
            collector = WechatArticleCollector()
            max_articles = config.get('max_articles_per_check', 10)
            export_formats = config.get('export_formats', ['pdf', 'docx'])
            
            # 采集并导出文章
            result = collector.collect_and_export_articles(
                account_name, max_articles, export_formats
            )
            
            # 更新监控状态
            config['last_check_time'] = datetime.now().isoformat()
            
            if result.get('success'):
                articles_count = result.get('articles_count', 0)
                config['total_collected'] += articles_count
                config['last_error'] = None
                
                if articles_count > 0:
                    logger.info(f"账号 {account_name} 新采集 {articles_count} 篇文章")
                    
                    # 发送通知（可选）
                    self._send_notification(account_name, articles_count, result)
                else:
                    logger.debug(f"账号 {account_name} 无新文章")
            else:
                config['error_count'] += 1
                config['last_error'] = result.get('message', '采集失败')
                logger.warning(f"账号 {account_name} 检查失败: {config['last_error']}")
            
            self._save_monitor_config()
            
        except Exception as e:
            config['error_count'] += 1
            config['last_error'] = str(e)
            config['last_check_time'] = datetime.now().isoformat()
            self._save_monitor_config()
            logger.error(f"检查账号 {account_name} 失败: {e}")
    
    def _send_notification(self, account_name, articles_count, result):
        """发送通知（可扩展）"""
        try:
            # 这里可以添加邮件、微信、钉钉等通知方式
            export_stats = result.get('export_stats', {})
            export_dir = result.get('export_directory', '')
            
            notification_msg = f"""
📢 微信公众号监控通知

账号: {account_name}
新文章: {articles_count} 篇
导出情况: {export_stats}
存储位置: {export_dir}
检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # 暂时只记录到日志，后续可添加其他通知方式
            logger.info(f"监控通知: {notification_msg}")
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
    
    def force_check_account(self, account_name):
        """强制检查指定账号"""
        try:
            if account_name not in self.monitored_accounts:
                return False
            
            config = self.monitored_accounts[account_name]
            self._check_account_updates(account_name, config)
            return True
            
        except Exception as e:
            logger.error(f"强制检查账号失败: {e}")
            return False
    
    def get_monitor_status(self, account_name=None):
        """获取监控状态"""
        try:
            if account_name:
                if account_name in self.monitored_accounts:
                    return self.monitored_accounts[account_name]
                return None
            else:
                return {
                    'running': self.running,
                    'total_accounts': len(self.monitored_accounts),
                    'enabled_accounts': sum(1 for c in self.monitored_accounts.values() if c.get('enabled', True)),
                    'accounts': self.monitored_accounts
                }
        except Exception as e:
            logger.error(f"获取监控状态失败: {e}")
            return None
    
    def _load_monitor_config(self):
        """加载监控配置"""
        try:
            if self.monitor_data_file.exists():
                with open(self.monitor_data_file, 'r', encoding='utf-8') as f:
                    self.monitored_accounts = json.load(f)
                logger.info(f"加载监控配置: {len(self.monitored_accounts)} 个账号")
        except Exception as e:
            logger.warning(f"加载监控配置失败: {e}")
            self.monitored_accounts = {}
    
    def _save_monitor_config(self):
        """保存监控配置"""
        try:
            with open(self.monitor_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.monitored_accounts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存监控配置失败: {e}")
    
    def cleanup_old_monitors(self, days=30):
        """清理旧的监控配置"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            accounts_to_remove = []
            
            for account_name, config in self.monitored_accounts.items():
                created_at = config.get('created_at')
                if created_at:
                    created_time = datetime.fromisoformat(created_at)
                    if created_time < cutoff_time and not config.get('enabled', True):
                        accounts_to_remove.append(account_name)
            
            for account_name in accounts_to_remove:
                del self.monitored_accounts[account_name]
            
            if accounts_to_remove:
                self._save_monitor_config()
                logger.info(f"清理了 {len(accounts_to_remove)} 个旧的监控配置")
            
            return len(accounts_to_remove)
            
        except Exception as e:
            logger.error(f"清理监控配置失败: {e}")
            return 0

# 全局监控器实例
account_monitor = AccountMonitor()