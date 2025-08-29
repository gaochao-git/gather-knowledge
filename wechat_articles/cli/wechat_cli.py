#!/usr/bin/env python3
"""
微信公众号采集系统 CLI 工具
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wechat_articles.collector.article_collector import WechatArticleCollector
from wechat_articles.monitor.account_monitor import account_monitor
from wechat_articles.wechat_config import WECHAT_TOKEN, WECHAT_COOKIES, WECHAT_FAKEID

class WechatCollectorCLI:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        # 使用配置的token、cookies和fakeid初始化采集器（批量采集）
        self.local_collector = WechatArticleCollector(token=WECHAT_TOKEN, cookies=WECHAT_COOKIES, fakeid=WECHAT_FAKEID, storage_type='batch')
        
        # 显示配置状态
        if WECHAT_TOKEN:
            print("✅ 已配置微信公众平台token，将优先使用API方式采集")
            if WECHAT_FAKEID:
                print("✅ 已配置FAKEID，将直接使用指定公众号")
        else:
            print("⚠️  未配置微信公众平台token，将使用搜索方式采集")
    
    def collect_account(self, account_name, max_articles=20, use_api=False, export_formats=None):
        """采集指定公众号文章"""
        print(f"开始采集公众号: {account_name}")
        
        if export_formats:
            print(f"导出格式: {', '.join(export_formats)}")
        
        if use_api:
            # 使用API采集
            if export_formats:
                # 使用采集+导出API
                response = requests.post(f'{self.base_url}/api/collectors/wechat/collect-export', json={
                    'account_name': account_name,
                    'max_articles': max_articles,
                    'export_formats': export_formats,
                    'async': True
                })
            else:
                # 使用普通采集API
                response = requests.post(f'{self.base_url}/api/collectors/wechat/collect', json={
                    'account_name': account_name,
                    'max_articles': max_articles,
                    'async': True
                })
            
            if response.status_code == 200:
                data = response.json()['data']
                collector_key = data['collector_key']
                print(f"采集任务已启动，任务ID: {collector_key}")
                
                # 等待采集完成
                while True:
                    status_response = requests.get(f'{self.base_url}/api/collectors/status/{collector_key}')
                    if status_response.status_code == 200:
                        status_data = status_response.json()['data']
                        print(f"当前状态: {status_data['status']}")
                        
                        if status_data['status'] == 'completed':
                            result = status_data.get('result', {})
                            if export_formats:
                                print(f"采集导出完成!")
                                print(f"文章数量: {result.get('articles_count', 0)}")
                                export_stats = result.get('export_stats', {})
                                if export_stats:
                                    print("导出统计:")
                                    for fmt, count in export_stats.items():
                                        print(f"  {fmt.upper()}: {count} 个文件")
                                print(f"导出目录: {result.get('export_directory', 'N/A')}")
                            else:
                                print(f"采集完成! 共采集 {result.get('articles_count', 0)} 篇文章")
                            break
                        elif status_data['status'] == 'failed':
                            print(f"采集失败: {status_data.get('error', '未知错误')}")
                            break
                    
                    time.sleep(5)
            else:
                print(f"启动采集失败: {response.text}")
        
        else:
            # 直接本地采集
            if export_formats:
                # 采集并导出
                result = self.local_collector.collect_and_export_articles(account_name, max_articles, export_formats)
                
                if result.get('success'):
                    print(f"采集导出完成!")
                    print(f"文章数量: {result.get('articles_count', 0)}")
                    export_stats = result.get('export_stats', {})
                    if export_stats:
                        print("导出统计:")
                        for fmt, count in export_stats.items():
                            print(f"  {fmt.upper()}: {count} 个文件")
                    print(f"导出目录: {result.get('export_directory', 'N/A')}")
                else:
                    print(f"采集导出失败: {result.get('message', '未知错误')}")
            else:
                # 普通采集
                articles = self.local_collector.collect_articles(account_name, max_articles)
                stats = self.local_collector.get_collection_stats()
                
                print(f"采集完成!")
                print(f"成功采集: {stats['success_count']} 篇")
                print(f"失败数量: {stats['error_count']} 篇")
                print(f"成功率: {stats['success_rate']:.1f}%")
                print(f"用时: {stats['duration_seconds']:.1f} 秒")
                
                if articles:
                    print(f"\n前5篇文章预览:")
                    for i, article in enumerate(articles[:5], 1):
                        print(f"  {i}. {article['title'][:50]}...")
    
    def list_accounts(self, use_api=False):
        """列出所有账号及统计信息"""
        if use_api:
            response = requests.get(f'{self.base_url}/api/files/accounts')
            
            if response.status_code == 200:
                accounts = response.json()['data']['accounts']
                print("\n账号列表:")
                print("-" * 80)
                print(f"{'账号名称':<20} {'文章数':<10} {'大小(MB)':<10} {'最后更新'}")
                print("-" * 80)
                
                for account in accounts:
                    print(f"{account['account_name']:<20} "
                          f"{account['article_count']:<10} "
                          f"{account['local_size_mb']:<10.1f} "
                          f"{account.get('last_article_time', 'N/A')[:10]}")
            else:
                print(f"获取账号列表失败: {response.text}")
        
        else:
            # 直接读取本地文件
            batch_dir = Path('wechat_articles/storage/batch_data')
            monitor_dir = Path('wechat_articles/storage/monitor_data')
            
            print("\n本地账号列表:")
            print("-" * 80)
            print(f"{'类型':<10} {'账号名称':<20} {'文章数':<10} {'大小(MB)':<10}")
            print("-" * 80)
            
            # 批量采集的账号
            if batch_dir.exists():
                for account_dir in batch_dir.iterdir():
                    if account_dir.is_dir():
                        file_count = len(list(account_dir.glob('*.*')))  # 所有格式的文件
                        total_size = sum(f.stat().st_size for f in account_dir.rglob('*') if f.is_file())
                        size_mb = total_size / (1024 * 1024)
                        
                        print(f"{'批量':<10} {account_dir.name:<20} {file_count:<10} {size_mb:<10.1f}")
            
            # 监控采集的账号
            if monitor_dir.exists():
                for account_dir in monitor_dir.iterdir():
                    if account_dir.is_dir():
                        file_count = len(list(account_dir.glob('*.*')))  # 所有格式的文件
                        total_size = sum(f.stat().st_size for f in account_dir.rglob('*') if f.is_file())
                        size_mb = total_size / (1024 * 1024)
                        
                        print(f"{'监控':<10} {account_dir.name:<20} {file_count:<10} {size_mb:<10.1f}")
            
            if not batch_dir.exists() and not monitor_dir.exists():
                print("暂无采集数据")
    
    def show_article_content(self, account_name, filename, use_api=False):
        """显示文章内容"""
        if use_api:
            response = requests.get(f'{self.base_url}/api/files/accounts/{account_name}/articles/{filename}/content')
            
            if response.status_code == 200:
                data = response.json()['data']
                metadata = data['metadata']
                print(f"\n标题: {metadata.get('title', 'N/A')}")
                print(f"作者: {metadata.get('author', 'N/A')}")
                print(f"发布时间: {metadata.get('publish_time', 'N/A')}")
                print(f"采集时间: {metadata.get('collected_at', 'N/A')}")
                print(f"URL: {metadata.get('url', 'N/A')}")
                print("-" * 60)
                
                # 显示部分内容
                soup = BeautifulSoup(data['content'], 'html.parser')
                text_content = soup.get_text()[:500]
                print(f"内容预览:\n{text_content}...")
            else:
                print(f"获取文章内容失败: {response.text}")
        
        else:
            # 直接读取本地文件
            json_file = Path('articles') / account_name / f"{filename}.json"
            html_file = Path('articles') / account_name / f"{filename}.html"
            
            if not json_file.exists():
                print("文章不存在")
                return
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                print(f"\n标题: {metadata.get('title', 'N/A')}")
                print(f"作者: {metadata.get('author', 'N/A')}")
                print(f"发布时间: {metadata.get('publish_time', 'N/A')}")
                print(f"采集时间: {metadata.get('collected_at', 'N/A')}")
                print(f"URL: {metadata.get('url', 'N/A')}")
                
                if html_file.exists():
                    with open(html_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    soup = BeautifulSoup(content, 'html.parser')
                    text_content = soup.get_text()[:500]
                    print("-" * 60)
                    print(f"内容预览:\n{text_content}...")
                
            except Exception as e:
                print(f"读取文章失败: {e}")
    
    def time_range_collect(self, account_name, start_date, end_date, formats=['pdf', 'docx']):
        """时间段采集 - 支持用户指定格式和时间范围过滤 '中核集团 20250501 20250601'"""
        print(f"开始时间段采集: {account_name} ({start_date} - {end_date})")
        print(f"导出格式: {', '.join(formats)}")
        
        # 使用指定格式和时间范围进行采集和导出
        print("步骤1: 采集并导出文章...")
        result = self.local_collector.collect_and_export_articles(
            account_name, 
            export_formats=formats,
            start_date=start_date,
            end_date=end_date
        )
        
        if not result['success']:
            print(f"采集失败: {result['message']}")
            return
        
        print(f"采集完成: 成功获取 {result['articles_count']} 篇文章")
        
        # 显示导出统计
        export_stats = result.get('export_stats', {})
        if export_stats:
            print("导出统计:")
            for fmt, count in export_stats.items():
                if count > 0:
                    print(f"  {fmt.upper()}: {count} 个文件")
        print(f"导出目录: {result.get('export_directory', 'N/A')}")
        
        print(f"\n✅ 时间段采集完成!")
        print(f"   账号: {account_name}")
        print(f"   时间范围: {start_date} - {end_date}")
        print(f"   文章数量: {result['articles_count']}")
        print(f"   格式: {', '.join(formats)}")
        
        # 显示采集统计
        stats = self.local_collector.get_collection_stats()
        if stats:
            print(f"   成功率: {stats.get('success_rate', 0):.1f}%")
            print(f"   用时: {stats.get('duration_seconds', 0):.1f} 秒")
    
    def add_monitor(self, account_name, check_interval=30, max_articles=10, export_formats=['pdf', 'docx'], use_api=False):
        """添加账号监控"""
        print(f"添加账号监控: {account_name}")
        print(f"检查间隔: {check_interval} 分钟")
        print(f"导出格式: {', '.join(export_formats)}")
        
        config = {
            'check_interval_minutes': check_interval,
            'max_articles_per_check': max_articles,
            'export_formats': export_formats,
            'enabled': True
        }
        
        if use_api:
            response = requests.post(f'{self.base_url}/api/collectors/monitor/accounts', json={
                'account_name': account_name,
                **config
            })
            
            if response.status_code == 200:
                print(f"✅ 成功添加监控: {account_name}")
            else:
                print(f"❌ 添加监控失败: {response.text}")
        else:
            success = account_monitor.add_account_monitor(account_name, config)
            if success:
                print(f"✅ 成功添加监控: {account_name}")
                print("💡 监控服务已在后台运行")
            else:
                print(f"❌ 添加监控失败")
    
    def list_monitors(self, use_api=False):
        """列出所有监控"""
        if use_api:
            response = requests.get(f'{self.base_url}/api/collectors/monitor/status')
            
            if response.status_code == 200:
                data = response.json()['data']
                print("\n📊 监控状态:")
                print(f"运行状态: {'运行中' if data['running'] else '已停止'}")
                print(f"总监控数: {data['total_accounts']}")
                print(f"启用数量: {data['enabled_accounts']}")
                
                accounts = data.get('accounts', {})
                if accounts:
                    print("\n📋 监控列表:")
                    print("-" * 80)
                    print(f"{'账号名':<15} {'状态':<6} {'间隔(分)':<8} {'总采集':<6} {'最后检查':<12} {'错误次数':<6}")
                    print("-" * 80)
                    
                    for name, config in accounts.items():
                        status = '启用' if config.get('enabled') else '禁用'
                        interval = config.get('check_interval_minutes', 0)
                        total = config.get('total_collected', 0)
                        last_check = config.get('last_check_time', '')[:16] if config.get('last_check_time') else 'N/A'
                        errors = config.get('error_count', 0)
                        
                        print(f"{name:<15} {status:<6} {interval:<8} {total:<6} {last_check:<12} {errors:<6}")
            else:
                print(f"获取监控状态失败: {response.text}")
        else:
            status = account_monitor.get_monitor_status()
            
            if status:
                print("\n📊 本地监控状态:")
                print(f"运行状态: {'运行中' if status['running'] else '已停止'}")
                print(f"总监控数: {status['total_accounts']}")
                print(f"启用数量: {status['enabled_accounts']}")
                
                accounts = status.get('accounts', {})
                if accounts:
                    print("\n📋 监控列表:")
                    print("-" * 80)
                    print(f"{'账号名':<15} {'状态':<6} {'间隔(分)':<8} {'总采集':<6} {'最后检查':<12} {'错误次数':<6}")
                    print("-" * 80)
                    
                    for name, config in accounts.items():
                        status = '启用' if config.get('enabled') else '禁用'
                        interval = config.get('check_interval_minutes', 0)
                        total = config.get('total_collected', 0)
                        last_check = config.get('last_check_time', '')[:16] if config.get('last_check_time') else 'N/A'
                        errors = config.get('error_count', 0)
                        
                        print(f"{name:<15} {status:<6} {interval:<8} {total:<6} {last_check:<12} {errors:<6}")
            else:
                print("获取监控状态失败")
    
    def remove_monitor(self, account_name, use_api=False):
        """移除账号监控"""
        if use_api:
            response = requests.delete(f'{self.base_url}/api/collectors/monitor/accounts/{account_name}')
            
            if response.status_code == 200:
                print(f"✅ 成功移除监控: {account_name}")
            else:
                print(f"❌ 移除监控失败: {response.text}")
        else:
            success = account_monitor.remove_account_monitor(account_name)
            if success:
                print(f"✅ 成功移除监控: {account_name}")
            else:
                print(f"❌ 账号监控不存在: {account_name}")
    
    def toggle_monitor(self, account_name, enabled=True, use_api=False):
        """启用/禁用账号监控"""
        action = '启用' if enabled else '禁用'
        
        if use_api:
            response = requests.put(f'{self.base_url}/api/collectors/monitor/accounts/{account_name}/toggle', 
                                   json={'enabled': enabled})
            
            if response.status_code == 200:
                print(f"✅ 成功{action}监控: {account_name}")
            else:
                print(f"❌ {action}监控失败: {response.text}")
        else:
            success = account_monitor.enable_account_monitor(account_name, enabled)
            if success:
                print(f"✅ 成功{action}监控: {account_name}")
            else:
                print(f"❌ 账号监控不存在: {account_name}")
    
    def force_check(self, account_name, use_api=False):
        """强制检查账号更新"""
        print(f"强制检查账号: {account_name}")
        
        if use_api:
            response = requests.post(f'{self.base_url}/api/collectors/monitor/accounts/{account_name}/check')
            
            if response.status_code == 200:
                print(f"✅ 强制检查完成: {account_name}")
            else:
                print(f"❌ 强制检查失败: {response.text}")
        else:
            success = account_monitor.force_check_account(account_name)
            if success:
                print(f"✅ 强制检查完成: {account_name}")
            else:
                print(f"❌ 账号未被监控或检查失败: {account_name}")
    
    def _safe_filename(self, text):
        """生成安全文件名"""
        import re
        return re.sub(r'[^\w\s-]', '', text.strip()).replace(' ', '_')