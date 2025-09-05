#!/usr/bin/env python3
"""
数据采集系统 CLI 工具 - 统一入口
"""

import argparse
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def main():
    parser = argparse.ArgumentParser(description='数据采集系统 CLI - 统一入口')
    subparsers = parser.add_subparsers(dest='module', help='可用模块')
    
    # 微信采集模块
    wechat_parser = subparsers.add_parser('wechat', help='微信公众号采集模块')
    wechat_subparsers = wechat_parser.add_subparsers(dest='wechat_command', help='微信采集命令')
    
    # 微信采集命令
    wechat_collect_parser = wechat_subparsers.add_parser('collect', help='采集指定公众号文章')
    wechat_collect_parser.add_argument('account_name', help='公众号名称')
    wechat_collect_parser.add_argument('--max-articles', type=int, default=20, help='最大采集文章数')
    wechat_collect_parser.add_argument('--export-formats', help='导出格式，逗号分隔 (pdf,docx,html)', default='')
    wechat_collect_parser.add_argument('--use-api', action='store_true', help='使用API模式（需要启动服务）')
    
    # 微信时间段采集命令
    wechat_time_range_parser = wechat_subparsers.add_parser('time-range-collect', help='时间段采集')
    wechat_time_range_parser.add_argument('account_name', help='公众号名称')
    wechat_time_range_parser.add_argument('start_date', help='开始日期 (格式: 20250501)')
    wechat_time_range_parser.add_argument('end_date', help='结束日期 (格式: 20250601)')
    wechat_time_range_parser.add_argument('--formats', default='pdf', help='导出格式，逗号分隔 (pdf,docx,html)')
    
    # 微信列表命令
    wechat_list_parser = wechat_subparsers.add_parser('list', help='列出所有账号')
    wechat_list_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 微信查看文章命令
    wechat_show_parser = wechat_subparsers.add_parser('show', help='显示文章内容')
    wechat_show_parser.add_argument('account_name', help='公众号名称')
    wechat_show_parser.add_argument('filename', help='文件名（不含扩展名）')
    wechat_show_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 微信监控命令
    wechat_monitor_parser = wechat_subparsers.add_parser('monitor', help='账号监控管理')
    wechat_monitor_subparsers = wechat_monitor_parser.add_subparsers(dest='monitor_action', help='监控操作')
    
    # 添加监控
    wechat_add_monitor_parser = wechat_monitor_subparsers.add_parser('add', help='添加账号监控')
    wechat_add_monitor_parser.add_argument('account_name', help='公众号名称')
    wechat_add_monitor_parser.add_argument('--interval', type=int, default=30, help='检查间隔（分钟）')
    wechat_add_monitor_parser.add_argument('--max-articles', type=int, default=10, help='每次最大采集数')
    wechat_add_monitor_parser.add_argument('--formats', default='pdf,docx', help='导出格式，逗号分隔')
    wechat_add_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 列出监控
    wechat_list_monitor_parser = wechat_monitor_subparsers.add_parser('list', help='列出所有监控')
    wechat_list_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 移除监控
    wechat_remove_monitor_parser = wechat_monitor_subparsers.add_parser('remove', help='移除账号监控')
    wechat_remove_monitor_parser.add_argument('account_name', help='公众号名称')
    wechat_remove_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 启用/禁用监控
    wechat_toggle_monitor_parser = wechat_monitor_subparsers.add_parser('toggle', help='启用/禁用账号监控')
    wechat_toggle_monitor_parser.add_argument('account_name', help='公众号名称')
    wechat_toggle_monitor_parser.add_argument('--disable', action='store_true', help='禁用监控')
    wechat_toggle_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 强制检查
    wechat_check_monitor_parser = wechat_monitor_subparsers.add_parser('check', help='强制检查账号更新')
    wechat_check_monitor_parser.add_argument('account_name', help='公众号名称')
    wechat_check_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 重新采集失败链接命令
    wechat_retry_parser = wechat_subparsers.add_parser('retry-failed', help='从失败链接文件重新采集文章')
    wechat_retry_parser.add_argument('failed_file_path', help='失败链接文件路径')
    wechat_retry_parser.add_argument('--formats', default='pdf,docx', help='导出格式，逗号分隔')
    
    # 列出失败链接文件命令
    wechat_list_failed_parser = wechat_subparsers.add_parser('list-failed', help='列出所有失败链接文件')
    
    args = parser.parse_args()
    
    if not args.module:
        parser.print_help()
        print("\n可用模块:")
        print("  wechat    微信公众号采集模块")
        return
    
    if args.module == 'wechat':
        # 导入并调用微信CLI
        from wechat_articles.cli.wechat_cli import WechatCollectorCLI
        import requests
        
        if not args.wechat_command:
            wechat_parser.print_help()
            return
        
        cli = WechatCollectorCLI()
        
        try:
            if args.wechat_command == 'collect':
                export_formats = None
                if args.export_formats:
                    export_formats = [f.strip() for f in args.export_formats.split(',')]
                cli.collect_account(args.account_name, args.max_articles, args.use_api, export_formats)
            elif args.wechat_command == 'time-range-collect':
                formats = [f.strip() for f in args.formats.split(',')]
                cli.time_range_collect(args.account_name, args.start_date, args.end_date, formats)
            elif args.wechat_command == 'list':
                cli.list_accounts(args.use_api)
            elif args.wechat_command == 'show':
                cli.show_article_content(args.account_name, args.filename, args.use_api)
            elif args.wechat_command == 'monitor':
                if args.monitor_action == 'add':
                    formats = [f.strip() for f in args.formats.split(',')]
                    cli.add_monitor(args.account_name, args.interval, args.max_articles, formats, args.use_api)
                elif args.monitor_action == 'list':
                    cli.list_monitors(args.use_api)
                elif args.monitor_action == 'remove':
                    cli.remove_monitor(args.account_name, args.use_api)
                elif args.monitor_action == 'toggle':
                    enabled = not args.disable
                    cli.toggle_monitor(args.account_name, enabled, args.use_api)
                elif args.monitor_action == 'check':
                    cli.force_check(args.account_name, args.use_api)
                else:
                    print("请指定监控操作: add, list, remove, toggle, check")
            elif args.wechat_command == 'retry-failed':
                formats = [f.strip() for f in args.formats.split(',')]
                cli.retry_failed_collection(args.failed_file_path, formats)
            elif args.wechat_command == 'list-failed':
                cli.list_failed_files()
        
        except KeyboardInterrupt:
            print("\n操作已取消")
        except requests.exceptions.ConnectionError:
            if hasattr(args, 'use_api') and args.use_api:
                print("错误: 无法连接到服务器，请确保服务已启动 (python run.py)")
            else:
                print("网络连接错误")
        except Exception as e:
            print(f"执行出错: {e}")

if __name__ == '__main__':
    main()