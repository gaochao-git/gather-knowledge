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
    def __init__(self):
        # 使用配置的token、cookies和fakeid初始化采集器（批量采集）
        self.collector = WechatArticleCollector(token=WECHAT_TOKEN, cookies=WECHAT_COOKIES, fakeid=WECHAT_FAKEID, storage_type='batch')
        
        # 显示配置状态
        if WECHAT_TOKEN:
            print("✅ 已配置微信公众平台token")
            if WECHAT_FAKEID:
                print("✅ 已配置FAKEID，将直接使用指定公众号")
        else:
            print("⚠️  未配置微信公众平台token")
    
    def collect_account(self, account_name, export_formats=None):
        """采集指定公众号文章"""
        if not export_formats:
            export_formats = ['pdf', 'docx']
            
        print(f"开始采集公众号: {account_name}")
        print(f"导出格式: {', '.join(export_formats)}")
        
        # 直接本地采集并导出
        result = self.collector.collect_and_export_articles(account_name, export_formats)
        
        if result.get('success'):
            print(f"✅ 采集导出完成!")
            print(f"文章数量: {result.get('articles_count', 0)} 篇")
            export_stats = result.get('export_stats', {})
            if export_stats:
                print("导出统计:")
                for fmt, count in export_stats.items():
                    if count > 0:
                        print(f"  {fmt.upper()}: {count} 个文件")
            print(f"导出目录: {result.get('export_directory', 'N/A')}")
            
            # 显示失败信息
            if result.get('failed_file'):
                print(f"❌ 失败链接文件: {result['failed_file']}")
                print(f"💡 使用 'retry-failed' 命令重新采集失败的文章")
        else:
            print(f"❌ 采集导出失败: {result.get('message', '未知错误')}")
    
    def list_accounts(self):
        """列出所有账号及统计信息"""
        batch_dir = Path('wechat_articles/storage/batch_data')
        monitor_dir = Path('wechat_articles/storage/monitor_data')
        
        print("\n📂 本地账号列表:")
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
    
    def show_article_content(self, account_name, filename):
        """显示文章内容"""
        # 直接读取本地文件
        json_file = Path('wechat_articles/storage/batch_data') / account_name / f"{filename}.json"
        
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
            print("-" * 60)
            
            # 显示部分内容
            if 'content' in metadata:
                soup = BeautifulSoup(metadata['content'], 'html.parser')
                text_content = soup.get_text()[:500]
                print(f"内容预览:\n{text_content}...")
            
        except Exception as e:
            print(f"读取文章失败: {e}")
    
    def time_range_collect(self, account_name, start_date, end_date, formats=['pdf', 'docx']):
        """时间段采集 - 支持用户指定格式和时间范围过滤 '中核集团 20250501 20250601'"""
        print(f"开始时间段采集: {account_name} ({start_date} - {end_date})")
        print(f"导出格式: {', '.join(formats)}")
        
        # 使用指定格式和时间范围进行采集和导出
        print("步骤1: 采集并导出文章...")
        result = self.collector.collect_and_export_articles(
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
        stats = self.collector.get_collection_stats()
        if stats:
            print(f"   成功率: {stats.get('success_rate', 0):.1f}%")
            print(f"   用时: {stats.get('duration_seconds', 0):.1f} 秒")
            
            # 显示失败链接文件信息
            if stats.get('failed_articles_count', 0) > 0:
                print(f"   失败文章: {stats['failed_articles_count']} 篇")
                if result.get('failed_file'):
                    print(f"   失败链接文件: {result['failed_file']}")
                    print(f"   💡 可以使用 'retry-failed' 命令重新采集失败的文章")
    
    def retry_failed_collection(self, failed_file_path, formats=['pdf', 'docx']):
        """从失败链接文件重新采集文章"""
        print(f"开始重新采集失败文章: {failed_file_path}")
        print(f"导出格式: {', '.join(formats)}")
        
        # 检查失败链接文件是否存在
        if not Path(failed_file_path).exists():
            print(f"❌ 失败链接文件不存在: {failed_file_path}")
            return
        
        try:
            # 从失败链接文件重新采集
            result = self.collector.collect_from_failed_links(failed_file_path, formats)
            
            if result['success']:
                print(f"✅ 重新采集完成!")
                print(f"   文章数量: {result['articles_count']} 篇")
                print(f"   成功采集: {result['success_count']} 篇")
                print(f"   仍然失败: {result['failed_count']} 篇")
                
                if result.get('new_failed_file'):
                    print(f"   新失败链接文件: {result['new_failed_file']}")
                    print(f"   💡 可以再次使用此文件进行重试")
                else:
                    print(f"   🎉 所有文章都重新采集成功!")
            else:
                print(f"❌ 重新采集失败: {result['message']}")
                
        except Exception as e:
            print(f"❌ 重新采集异常: {e}")
    
    def list_failed_files(self):
        """列出所有失败链接文件"""
        batch_dir = Path('wechat_articles/storage/batch_data')
        
        if not batch_dir.exists():
            print("📁 存储目录不存在")
            return
            
        failed_files = []
        
        # 查找所有失败链接文件
        for failed_file in batch_dir.rglob('*_failed_articles_*.json'):
            try:
                with open(failed_file, 'r', encoding='utf-8') as f:
                    failed_data = json.load(f)
                
                failed_files.append({
                    'path': str(failed_file),
                    'filename': failed_file.name,
                    'account': failed_data.get('account_name', '未知'),
                    'failed_count': failed_data.get('failed_count', 0),
                    'collection_time': failed_data.get('collection_time', ''),
                    'size': failed_file.stat().st_size
                })
            except Exception as e:
                print(f"⚠️  读取失败文件 {failed_file} 出错: {e}")
                continue
        
        if not failed_files:
            print("📋 没有找到失败链接文件")
            return
            
        print(f"\n📋 失败链接文件列表 ({len(failed_files)} 个):")
        print("-" * 100)
        print(f"{'文件名':<35} {'账号':<15} {'失败数':<8} {'创建时间':<20} {'大小':<10}")
        print("-" * 100)
        
        for file_info in sorted(failed_files, key=lambda x: x['collection_time'], reverse=True):
            collection_time = file_info['collection_time'][:19] if file_info['collection_time'] else 'N/A'
            size_kb = file_info['size'] / 1024
            
            print(f"{file_info['filename']:<35} "
                  f"{file_info['account']:<15} "
                  f"{file_info['failed_count']:<8} "
                  f"{collection_time:<20} "
                  f"{size_kb:.1f}KB")
        
        print(f"\n💡 使用 'retry-failed <文件路径>' 命令重新采集失败的文章")
    
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