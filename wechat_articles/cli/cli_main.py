#!/usr/bin/env python3
"""
微信公众号采集系统 CLI 主程序
"""

import argparse
import requests
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wechat_articles.cli.wechat_cli import WechatCollectorCLI

def main():
    parser = argparse.ArgumentParser(description='微信公众号采集系统 CLI')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 采集命令
    collect_parser = subparsers.add_parser('collect', help='采集指定公众号文章')
    collect_parser.add_argument('account_name', help='公众号名称')
    collect_parser.add_argument('--max-articles', type=int, default=20, help='最大采集文章数')
    collect_parser.add_argument('--export-formats', help='导出格式，逗号分隔 (pdf,docx,html)', default='pdf,docx')
    collect_parser.add_argument('--use-api', action='store_true', help='使用API模式（需要启动服务）')
    
    # 时间段采集命令
    time_range_parser = subparsers.add_parser('time-range-collect', help='时间段采集 - 格式: 账号名 开始日期 结束日期')
    time_range_parser.add_argument('account_name', help='公众号名称')
    time_range_parser.add_argument('start_date', help='开始日期 (格式: 20250501)')
    time_range_parser.add_argument('end_date', help='结束日期 (格式: 20250601)')
    time_range_parser.add_argument('--formats', default='pdf,docx', help='导出格式，逗号分隔 (pdf,docx,html)')
    
    # 列表命令
    list_parser = subparsers.add_parser('list', help='列出所有账号')
    list_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 查看文章命令
    show_parser = subparsers.add_parser('show', help='显示文章内容')
    show_parser.add_argument('account_name', help='公众号名称')
    show_parser.add_argument('filename', help='文件名（不含扩展名）')
    show_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 监控命令
    monitor_parser = subparsers.add_parser('monitor', help='账号监控管理')
    monitor_subparsers = monitor_parser.add_subparsers(dest='monitor_action', help='监控操作')
    
    # 添加监控
    add_monitor_parser = monitor_subparsers.add_parser('add', help='添加账号监控')
    add_monitor_parser.add_argument('account_name', help='公众号名称')
    add_monitor_parser.add_argument('--interval', type=int, default=30, help='检查间隔（分钟）')
    add_monitor_parser.add_argument('--max-articles', type=int, default=10, help='每次最大采集数')
    add_monitor_parser.add_argument('--formats', default='pdf,docx', help='导出格式，逗号分隔')
    add_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 列出监控
    list_monitor_parser = monitor_subparsers.add_parser('list', help='列出所有监控')
    list_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 移除监控
    remove_monitor_parser = monitor_subparsers.add_parser('remove', help='移除账号监控')
    remove_monitor_parser.add_argument('account_name', help='公众号名称')
    remove_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 启用/禁用监控
    toggle_monitor_parser = monitor_subparsers.add_parser('toggle', help='启用/禁用账号监控')
    toggle_monitor_parser.add_argument('account_name', help='公众号名称')
    toggle_monitor_parser.add_argument('--disable', action='store_true', help='禁用监控')
    toggle_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    # 强制检查
    check_monitor_parser = monitor_subparsers.add_parser('check', help='强制检查账号更新')
    check_monitor_parser.add_argument('account_name', help='公众号名称')
    check_monitor_parser.add_argument('--use-api', action='store_true', help='使用API模式')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = WechatCollectorCLI()
    
    try:
        if args.command == 'collect':
            export_formats = None
            if args.export_formats:
                export_formats = [f.strip() for f in args.export_formats.split(',')]
            cli.collect_account(args.account_name, args.max_articles, args.use_api, export_formats)
        elif args.command == 'time-range-collect':
            formats = [f.strip() for f in args.formats.split(',')]
            cli.time_range_collect(args.account_name, args.start_date, args.end_date, formats)
        elif args.command == 'list':
            cli.list_accounts(args.use_api)
        elif args.command == 'show':
            cli.show_article_content(args.account_name, args.filename, args.use_api)
        elif args.command == 'monitor':
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