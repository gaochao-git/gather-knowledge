import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path
import json
import hashlib
import re
from wechat_articles.core.logger import get_logger

logger = get_logger(__name__)

class WechatArticleCollector:
    """微信公众号文章采集器 - 使用微信公众平台token和cookie方式"""
    
    def __init__(self, token=None, cookies=None, fakeid=None, storage_type='batch'):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://mp.weixin.qq.com/',
        })
        
        # 微信公众平台配置
        self.token = token
        self.fakeid = fakeid  # 公众号的fakeid，用于API调用
        if cookies:
            self._set_cookies(cookies)
            
        logger.info(f"初始化采集器 - Token: {'已配置' if token else '未配置'}, Fakeid: {'已配置' if fakeid else '未配置'}")
        
        # 微信公众平台API端点
        self.mp_base_url = 'https://mp.weixin.qq.com'
        self.mp_api_base = f'{self.mp_base_url}/cgi-bin'
        
        # 备用搜索配置（当没有token/cookie时使用）
        self.sogou_search_url = 'https://weixin.sogou.com/weixin'
        
        # 根据storage_type设置保存路径
        if storage_type == 'monitor':
            self.base_output_dir = Path('wechat_articles/storage/monitor_data')  # 监控采集保存到monitor_data
        else:
            self.base_output_dir = Path('wechat_articles/storage/batch_data')  # 批量采集保存到batch_data
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 采集统计
        self.stats = {
            'total_collected': 0,
            'success_count': 0,
            'error_count': 0,
            'start_time': None
        }
    
    def _set_cookies(self, cookies):
        """设置cookies，支持字符串和字典两种格式"""
        try:
            if isinstance(cookies, str):
                # 解析cookie字符串格式 "key1=value1; key2=value2"
                cookie_dict = {}
                for item in cookies.split(';'):
                    item = item.strip()
                    if '=' in item:
                        key, value = item.split('=', 1)
                        cookie_dict[key.strip()] = value.strip()
                self.session.cookies.update(cookie_dict)
            elif isinstance(cookies, dict):
                # 直接使用字典格式
                self.session.cookies.update(cookies)
        except Exception as e:
            logger.warning(f"设置cookies失败: {e}")
    
    def collect_and_export_articles(self, account_name, max_articles=20, export_formats=None):
        """
        采集文章并直接保存为指定格式
        
        Args:
            account_name: 公众号名称
            max_articles: 最大采集数量
            export_formats: 导出格式列表 ['json', 'html', 'txt', 'md']
            
        Returns:
            dict: 采集和导出结果
        """
        if export_formats is None:
            export_formats = ['pdf', 'docx']  # 默认导出PDF和Word格式
            
        logger.info(f"开始采集并导出: {account_name}, 格式: {export_formats}")
        
        # 采集文章并直接保存为多种格式
        articles = self._collect_articles_with_formats(account_name, max_articles, export_formats)
        
        if not articles:
            return {
                'success': False,
                'message': '未采集到任何文章',
                'articles_count': 0,
                'export_stats': {fmt: 0 for fmt in export_formats}
            }
        
        # 统计每种格式的文件数量
        account_dir = self.base_output_dir / self._safe_filename(account_name)
        export_stats = {}
        
        for fmt in export_formats:
            if fmt == 'json':
                export_stats['json'] = len(list(account_dir.glob('*.json')))
            elif fmt == 'html':
                export_stats['html'] = len(list(account_dir.glob('*.html')))
            elif fmt == 'txt':
                export_stats['txt'] = len(list(account_dir.glob('*.txt')))
            elif fmt == 'md':
                export_stats['md'] = len(list(account_dir.glob('*.md')))
            elif fmt == 'pdf':
                export_stats['pdf'] = len(list(account_dir.glob('*.pdf')))
            elif fmt == 'docx':
                export_stats['docx'] = len(list(account_dir.glob('*.docx')))
        
        return {
            'success': True,
            'message': f'采集并导出完成',
            'articles_count': len(articles),
            'export_stats': export_stats,
            'export_directory': str(account_dir)
        }
    
    def _collect_articles_with_formats(self, account_name, max_articles, export_formats):
        """采集文章并直接保存为多种格式"""
        logger.info(f"开始采集公众号: {account_name}, 最大数量: {max_articles}")
        self.stats['start_time'] = datetime.now()
        
        try:
            # 优先使用微信公众平台接口
            if self.token:
                articles = self._get_articles_by_mp_api(account_name, max_articles)
                if articles:
                    logger.info(f"通过微信公众平台API获取到 {len(articles)} 篇文章")
                    return self._process_articles_with_formats(articles, account_name, export_formats)
                else:
                    logger.warning("微信公众平台API获取失败，切换到搜索方式")
            
            # 备用：搜索方式获取文章
            return self._collect_articles_by_search_with_formats(account_name, max_articles, export_formats)
            
        except Exception as e:
            logger.error(f"采集过程出错: {e}")
            return []
    
    def _collect_articles_by_search_with_formats(self, account_name, max_articles, export_formats):
        """通过搜索方式采集文章并保存为多种格式"""
        logger.error(f"搜索方式已禁用，请配置微信公众平台token和fakeid后使用API方式: {account_name}")
        return []
    
    def _process_articles_with_formats(self, articles, account_name, export_formats):
        """处理文章列表，获取详情并保存为多种格式"""
        collected_articles = []
        account_dir = self.base_output_dir / self._safe_filename(account_name)
        account_dir.mkdir(parents=True, exist_ok=True)
        
        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"采集第 {i}/{len(articles)} 篇: {article['title'][:30]}...")
                
                # 获取文章详情
                article_detail = self._get_article_detail(article['url'])
                if article_detail:
                    # 合并文章信息
                    full_article = {**article, **article_detail}
                    full_article['account_name'] = account_name
                    full_article['collected_at'] = datetime.now().isoformat()
                    
                    # 保存为多种格式
                    self._save_article_in_formats(full_article, account_dir, export_formats)
                    collected_articles.append(full_article)
                    
                    self.stats['success_count'] += 1
                    logger.info(f"采集成功: {full_article['title'][:30]}")
                else:
                    logger.warning(f"获取文章详情失败: {article['title'][:30]}")
                    self.stats['error_count'] += 1
                
                # 控制采集速度，避免被限制
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"采集文章失败: {e}")
                self.stats['error_count'] += 1
                continue
        
        self.stats['total_collected'] = len(collected_articles)
        logger.info(f"采集完成: 成功 {self.stats['success_count']} 篇，失败 {self.stats['error_count']} 篇")
        
        return collected_articles
    
    def _save_article_in_formats(self, article, account_dir, export_formats):
        """将文章保存为多种格式"""
        try:
            # 生成文件名
            filename_base = self._generate_filename(article)
            
            # 根据指定格式保存文件
            for fmt in export_formats:
                if fmt == 'json':
                    self._save_as_json(article, account_dir, filename_base)
                elif fmt == 'html':
                    self._save_as_html(article, account_dir, filename_base)
                elif fmt == 'txt':
                    self._save_as_txt(article, account_dir, filename_base)
                elif fmt == 'md':
                    self._save_as_markdown(article, account_dir, filename_base)
                elif fmt == 'pdf':
                    self._save_as_pdf(article, account_dir, filename_base)
                elif fmt == 'docx':
                    self._save_as_docx(article, account_dir, filename_base)
            
            return True
            
        except Exception as e:
            logger.error(f"保存文章文件失败: {e}")
            return False
    
    def _save_as_json(self, article, account_dir, filename_base):
        """保存为JSON格式"""
        json_path = account_dir / f"{filename_base}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'title': article['title'],
                'author': article['author'],
                'publish_time': article['publish_time'],
                'url': article['url'],
                'account_name': article['account_name'],
                'collected_at': article['collected_at'],
                'content': article['content'],
                'summary': article.get('summary', ''),
                'read_count': article.get('read_count', 0),
                'like_count': article.get('like_count', 0),
                'comment_count': article.get('comment_count', 0)
            }, f, ensure_ascii=False, indent=2)
    
    def _save_as_html(self, article, account_dir, filename_base):
        """保存为HTML格式"""
        html_path = account_dir / f"{filename_base}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            # 创建完整的HTML文档
            html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article['title']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .header {{ border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .title {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
        .meta {{ color: #666; font-size: 14px; }}
        .content {{ max-width: 800px; margin: 0 auto; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">{article['title']}</div>
        <div class="meta">
            作者: {article['author']} | 发布时间: {article['publish_time']} | 来源: {article['account_name']}
        </div>
    </div>
    <div class="content">
        {article['content']}
    </div>
</body>
</html>"""
            f.write(html_content)
    
    def _save_as_txt(self, article, account_dir, filename_base):
        """保存为纯文本格式"""
        txt_path = account_dir / f"{filename_base}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            # 提取纯文本内容
            soup = BeautifulSoup(article['content'], 'html.parser')
            text_content = soup.get_text()
            
            # 格式化文本内容
            content = f"""标题: {article['title']}
作者: {article['author']}
发布时间: {article['publish_time']}
来源: {article['account_name']}
采集时间: {article['collected_at']}
原文链接: {article['url']}

{'=' * 50}

{text_content}
"""
            f.write(content)
    
    def _save_as_markdown(self, article, account_dir, filename_base):
        """保存为Markdown格式"""
        md_path = account_dir / f"{filename_base}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            # 简单的HTML到Markdown转换
            soup = BeautifulSoup(article['content'], 'html.parser')
            
            # 处理基本的HTML标签
            content = article['content']
            # 这里可以添加更复杂的HTML到Markdown转换逻辑
            # 目前先简单处理
            content = re.sub(r'<h([1-6])>(.*?)</h[1-6]>', r'\n# \2\n', content)
            content = re.sub(r'<p>(.*?)</p>', r'\1\n\n', content)
            content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', content)
            content = re.sub(r'<em>(.*?)</em>', r'*\1*', content)
            content = re.sub(r'<br\s*/?>', '\n', content)
            content = re.sub(r'<[^>]+>', '', content)  # 移除其他HTML标签
            
            markdown_content = f"""# {article['title']}

**作者**: {article['author']}  
**发布时间**: {article['publish_time']}  
**来源**: {article['account_name']}  
**采集时间**: {article['collected_at']}  
**原文链接**: {article['url']}

---

{content}
"""
            f.write(markdown_content)
    
    def _save_as_pdf(self, article, account_dir, filename_base):
        """保存为PDF格式 - 完整保持文章排版和图片"""
        pdf_path = account_dir / f"{filename_base}.pdf"
        
        # 首先尝试使用reportlab（更稳定）
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.units import inch
            from bs4 import BeautifulSoup
            import os
            
            # 注册中文字体 - 尝试系统字体
            try:
                # 在macOS上尝试使用系统中文字体
                font_paths = [
                    '/System/Library/Fonts/Helvetica.ttc',  # macOS系统字体
                    '/System/Library/Fonts/PingFang.ttc',   # macOS中文字体
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
                    'C:/Windows/Fonts/simsun.ttc',  # Windows
                    'C:/Windows/Fonts/msyh.ttc',    # Windows微软雅黑
                ]
                
                chinese_font_registered = False
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            chinese_font_registered = True
                            break
                        except:
                            continue
                
                if not chinese_font_registered:
                    # 如果没有找到系统字体，使用reportlab内置字体
                    logger.warning("未找到中文字体，使用默认字体")
                    
            except Exception as e:
                logger.warning(f"注册中文字体失败: {e}")
            
            # 创建PDF文档
            doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
            story = []
            
            # 设置样式 - 使用支持中文的字体
            styles = getSampleStyleSheet()
            
            # 根据是否成功注册中文字体选择字体
            font_name = 'ChineseFont' if chinese_font_registered else 'Helvetica'
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=20,
                wordWrap='LTR'
            )
            meta_style = ParagraphStyle(
                'CustomMeta',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=12,
                alignment=TA_CENTER,
                spaceAfter=20,
                wordWrap='LTR'
            )
            content_style = ParagraphStyle(
                'CustomContent',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=11,
                alignment=TA_LEFT,
                spaceAfter=10,
                wordWrap='LTR',
                leftIndent=20,
                rightIndent=20
            )
            
            # 添加标题 - 确保UTF-8编码
            title_text = article['title']
            story.append(Paragraph(title_text, title_style))
            
            # 添加元信息
            meta_text = f"作者: {article['author']} | 发布时间: {article['publish_time']} | 来源: {article['account_name']}"
            story.append(Paragraph(meta_text, meta_style))
            story.append(Spacer(1, 20))
            
            # 处理内容 - 保持完整HTML结构，包括图片
            soup = BeautifulSoup(article['content'], 'html.parser')
            
            # 按顺序处理所有元素，保持原始排版
            for element in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img', 'br']):
                try:
                    if element.name == 'img':
                        # 处理图片 - 嵌入到PDF中
                        img_src = element.get('src', '')
                        if img_src.startswith('images/'):
                            # 本地图片路径
                            img_path = self.base_output_dir / img_src
                            if img_path.exists():
                                try:
                                    # 添加图片到PDF，自动调整尺寸
                                    img = Image(str(img_path))
                                    
                                    # 获取页面可用宽度和高度（考虑边距）
                                    page_width, page_height = A4
                                    available_width = page_width - 2*inch  # 减去左右边距
                                    available_height = page_height - 2*inch  # 减去上下边距
                                    
                                    # 计算图片缩放比例
                                    width_scale = available_width / img.drawWidth if img.drawWidth > available_width else 1
                                    height_scale = available_height / img.drawHeight if img.drawHeight > available_height else 1
                                    
                                    # 使用较小的缩放比例，保持图片比例
                                    scale = min(width_scale, height_scale, 1)  # 不放大，只缩小
                                    
                                    # 应用缩放
                                    img.drawWidth = img.drawWidth * scale
                                    img.drawHeight = img.drawHeight * scale
                                    
                                    story.append(img)
                                    story.append(Spacer(1, 10))
                                except Exception as e:
                                    logger.warning(f"PDF图片嵌入失败 {img_path}: {e}")
                        continue
                        
                    elif element.name == 'br':
                        # 处理换行
                        story.append(Spacer(1, 6))
                        continue
                        
                    # 处理文本内容
                    text = element.get_text(separator=' ', strip=True)
                    if text:  # 只处理非空文本
                        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            # 处理标题
                            heading_style = ParagraphStyle(
                                'CustomHeading',
                                parent=content_style,
                                fontSize=14,
                                spaceAfter=15,
                                spaceBefore=15,
                                fontName=font_name
                            )
                            story.append(Paragraph(text, heading_style))
                        else:
                            # 处理普通段落
                            story.append(Paragraph(text, content_style))
                            story.append(Spacer(1, 6))
                            
                except Exception as e:
                    logger.warning(f"处理元素失败 {element.name}: {e}")
                    continue
            
            # 如果没有找到结构化内容，使用纯文本
            if len(story) <= 3:  # 只有标题、元信息和间距
                text_content = soup.get_text(separator='\n', strip=True)
                paragraphs = text_content.split('\n')
                for para in paragraphs:
                    para = para.strip()
                    if para:  # 只处理非空段落
                        story.append(Paragraph(para, content_style))
                        story.append(Spacer(1, 6))
            
            # 生成PDF
            doc.build(story)
            logger.info(f"PDF文件生成成功（含图片嵌入）: {pdf_path}")
            
        except ImportError as e:
            logger.warning(f"reportlab未安装: {e}")
            # 尝试使用weasyprint（需要系统依赖）
            try:
                from weasyprint import HTML, CSS
                
                # 创建HTML内容（用于PDF转换）- 使用UTF-8和中文字体
                html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ 
            size: A4; 
            margin: 2cm; 
        }}
        body {{ 
            font-family: 'PingFang SC', 'Microsoft YaHei', 'SimHei', 'Helvetica Neue', Arial, sans-serif; 
            line-height: 1.8; 
            color: #333;
            font-size: 12px;
        }}
        .header {{ 
            border-bottom: 2px solid #eee; 
            padding-bottom: 20px; 
            margin-bottom: 30px; 
            text-align: center;
        }}
        .title {{ 
            font-size: 20px; 
            font-weight: bold; 
            margin-bottom: 15px; 
            color: #2c3e50;
        }}
        .meta {{ 
            color: #666; 
            font-size: 11px; 
            margin-bottom: 10px;
        }}
        .content {{ 
            text-align: justify;
            word-wrap: break-word;
        }}
        .content p {{
            margin: 10px 0;
            text-indent: 2em;
        }}
        .content img {{ 
            max-width: 100%; 
            height: auto; 
            display: block;
            margin: 10px auto;
        }}
        .content h1, .content h2, .content h3, .content h4, .content h5, .content h6 {{
            color: #2c3e50;
            margin: 20px 0 10px 0;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">{article['title']}</div>
        <div class="meta">
            作者: {article['author']} | 发布时间: {article['publish_time']} | 来源: {article['account_name']}
        </div>
    </div>
    <div class="content">
        {article['content']}
    </div>
</body>
</html>"""
                
                # 转换为PDF
                HTML(string=html_content).write_pdf(pdf_path)
                logger.info(f"PDF文件生成成功（weasyprint）: {pdf_path}")
                
            except ImportError as e:
                logger.warning(f"weasyprint未安装: {e}")
                self._create_text_fallback_for_pdf(article, account_dir, filename_base)
            except Exception as e:
                logger.error(f"weasyprint PDF生成失败: {e}")
                self._create_text_fallback_for_pdf(article, account_dir, filename_base)
                
        except Exception as e:
            logger.error(f"reportlab PDF生成失败: {e}")
            self._create_text_fallback_for_pdf(article, account_dir, filename_base)
    
    def _create_text_fallback_for_pdf(self, article, account_dir, filename_base):
        """PDF生成失败时的文本备用方案"""
        try:
            from bs4 import BeautifulSoup
            txt_path = account_dir / f"{filename_base}.pdf.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"PDF生成失败，以下为文本内容：\n\n")
                f.write(f"标题: {article['title']}\n")
                f.write(f"作者: {article['author']}\n") 
                f.write(f"发布时间: {article['publish_time']}\n")
                f.write(f"来源: {article['account_name']}\n\n")
                soup = BeautifulSoup(article['content'], 'html.parser')
                f.write(soup.get_text())
            logger.warning(f"PDF生成失败，已创建文本备用文件: {txt_path}")
        except Exception as e:
            logger.error(f"创建PDF备用文本文件失败: {e}")
    
    def _save_as_docx(self, article, account_dir, filename_base):
        """保存为Word格式 - 完整保持文章排版和图片"""
        docx_path = account_dir / f"{filename_base}.docx"
        
        try:
            from docx import Document
            from docx.shared import Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from bs4 import BeautifulSoup
            
            # 创建Word文档
            doc = Document()
            
            # 添加标题
            title = doc.add_heading(article['title'], 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 添加元信息
            meta_para = doc.add_paragraph()
            meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            meta_para.add_run(f"作者: {article['author']} | 发布时间: {article['publish_time']} | 来源: {article['account_name']}")
            
            # 添加分隔线
            doc.add_paragraph('_' * 50).alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 处理内容 - 按顺序保持完整排版和图片
            soup = BeautifulSoup(article['content'], 'html.parser')
            
            # 按顺序处理所有元素，保持原始排版
            for element in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img', 'br']):
                try:
                    if element.name == 'img':
                        # 处理图片 - 嵌入到Word中
                        img_src = element.get('src', '')
                        if img_src.startswith('images/'):
                            # 本地图片路径
                            img_path = self.base_output_dir / img_src
                            if img_path.exists():
                                try:
                                    # 添加图片到Word文档，限制最大宽度
                                    paragraph = doc.add_paragraph()
                                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
                                    run.add_picture(str(img_path), width=Inches(5))  # 最大宽度5英寸
                                except Exception as e:
                                    logger.warning(f"Word图片嵌入失败 {img_path}: {e}")
                        continue
                        
                    elif element.name == 'br':
                        # 处理换行
                        doc.add_paragraph('')  # 添加空行
                        continue
                        
                    # 处理文本内容
                    text = element.get_text(separator=' ', strip=True)
                    if text:  # 只处理非空文本
                        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            # 处理标题
                            level = int(element.name[1])
                            doc.add_heading(text, level)
                        else:
                            # 处理普通段落
                            para = doc.add_paragraph(text)
                            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                            
                except Exception as e:
                    logger.warning(f"Word处理元素失败 {element.name}: {e}")
                    continue
            
            # 如果没有找到结构化内容，使用纯文本
            if len(doc.paragraphs) <= 3:  # 只有标题、元信息和分隔线
                text_content = soup.get_text(separator='\n', strip=True)
                paragraphs = text_content.split('\n')
                for para_text in paragraphs:
                    para_text = para_text.strip()
                    if para_text:  # 只处理非空段落
                        doc.add_paragraph(para_text)
            
            # 保存文档
            doc.save(docx_path)
            logger.info(f"Word文件生成成功（含图片嵌入）: {docx_path}")
            
        except ImportError as e:
            logger.warning(f"python-docx未安装: {e}")
            self._create_text_fallback_for_docx(article, account_dir, filename_base)
        except Exception as e:
            logger.error(f"Word文档生成失败: {e}")
            self._create_text_fallback_for_docx(article, account_dir, filename_base)
    
    def _create_text_fallback_for_docx(self, article, account_dir, filename_base):
        """Word生成失败时的文本备用方案"""
        try:
            from bs4 import BeautifulSoup
            txt_path = account_dir / f"{filename_base}.docx.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"Word文档生成失败，以下为文本内容：\n\n")
                f.write(f"标题: {article['title']}\n")
                f.write(f"作者: {article['author']}\n")
                f.write(f"发布时间: {article['publish_time']}\n")
                f.write(f"来源: {article['account_name']}\n\n")
                soup = BeautifulSoup(article['content'], 'html.parser')
                f.write(soup.get_text())
            logger.warning(f"Word文档生成失败，已创建文本备用文件: {txt_path}")
        except Exception as e:
            logger.error(f"创建Word备用文本文件失败: {e}")
    
    def collect_articles(self, account_name, max_articles=20):
        """
        采集指定公众号的文章
        
        Args:
            account_name: 公众号名称
            max_articles: 最大采集数量
            
        Returns:
            list: 采集到的文章列表
        """
        logger.info(f"开始采集公众号: {account_name}, 最大数量: {max_articles}")
        self.stats['start_time'] = datetime.now()
        
        try:
            # 优先使用微信公众平台接口
            if self.token:
                articles = self._get_articles_by_mp_api(account_name, max_articles)
                if articles:
                    logger.info(f"通过微信公众平台API获取到 {len(articles)} 篇文章")
                    return self._process_articles(articles, account_name)
                else:
                    logger.warning("微信公众平台API获取失败，切换到搜索方式")
            
            # 备用：搜索方式获取文章
            logger.error("搜索方式已禁用，请配置微信公众平台token和fakeid后使用API方式")
            return []
            
        except Exception as e:
            logger.error(f"采集过程出错: {e}")
            return []
    
    def _get_articles_by_mp_api(self, account_name, max_articles=20):
        """使用微信公众平台API获取文章列表"""
        try:
            if not self.token:
                logger.warning("微信公众平台API: 未配置token")
                return []
                
            logger.info(f"开始使用微信公众平台API采集，Token: {self.token}, Fakeid: {self.fakeid}")
            
            # 如果没有fakeid，无法使用API
            if not self.fakeid:
                logger.warning("未配置fakeid，无法使用微信公众平台API")
                return []
            
            # 获取文章列表接口
            url = f"{self.mp_api_base}/appmsg"
            
            # 构建请求参数 - 修正参数格式
            params = {
                'action': 'list_ex',
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': '1',
                'random': str(int(time.time() * 1000)),  # 使用毫秒时间戳
                'query': '',
                'begin': '0',  # 字符串格式
                'count': str(min(max_articles, 20)),  # 减少每次请求数量，使用字符串格式
                'type': '9',  # 修改为9（全部消息）
                'fakeid': self.fakeid,
            }
            
            logger.info(f"使用配置的fakeid: {self.fakeid}")
            
            # 设置必要的headers - 模拟真实浏览器请求
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
            self.session.headers.update(headers)
            
            logger.info(f"请求URL: {url}")
            logger.info(f"请求参数: {dict((k, v if k != 'token' else f'{v[:10]}...') for k, v in params.items())}")
            
            # 使用GET方式发送请求（符合微信公众平台的实际使用）
            response = self.session.get(url, params=params, timeout=15)
            
            logger.info(f"响应状态: {response.status_code}")
            logger.info(f"响应头: {dict(response.headers)}")
            
            response.raise_for_status()
            
            # 打印响应内容的前500字符用于调试
            response_text = response.text
            logger.info(f"响应内容前500字符: {response_text[:500]}")
            
            data = response.json()
            logger.info(f"解析的JSON数据: {data}")
            
            # 检查响应格式 - 兼容不同的返回格式
            if 'base_resp' in data:
                # 标准格式
                if data.get('base_resp', {}).get('ret') == 0:
                    app_msg_list = data.get('app_msg_list', [])
                    articles = []
                    
                    logger.info(f"获取到 {len(app_msg_list)} 篇文章")
                    
                    for item in app_msg_list:
                        articles.append({
                            'title': item.get('title', ''),
                            'url': item.get('link', ''),
                            'author': item.get('author', ''),
                            'publish_time': self._convert_timestamp(item.get('create_time', 0)),
                            'digest': item.get('digest', ''),
                            'cover': item.get('cover', ''),
                            'source': '微信公众平台API'
                        })
                    
                    return articles
                else:
                    error_msg = data.get('base_resp', {}).get('err_msg', '未知错误')
                    ret_code = data.get('base_resp', {}).get('ret', 'unknown')
                    logger.error(f"微信公众平台API返回错误: ret={ret_code}, err_msg={error_msg}")
                    return []
            else:
                # 直接格式 - 有些API直接返回app_msg_list
                if 'app_msg_list' in data:
                    app_msg_list = data.get('app_msg_list', [])
                    articles = []
                    
                    logger.info(f"获取到 {len(app_msg_list)} 篇文章")
                    
                    for item in app_msg_list:
                        articles.append({
                            'title': item.get('title', ''),
                            'url': item.get('link', ''),
                            'author': item.get('author', ''),
                            'publish_time': self._convert_timestamp(item.get('create_time', 0)),
                            'digest': item.get('digest', ''),
                            'cover': item.get('cover', ''),
                            'source': '微信公众平台API'
                        })
                    
                    return articles
                else:
                    logger.error(f"微信公众平台API返回未知格式: {data}")
                    return []
                
        except Exception as e:
            logger.error(f"使用微信公众平台API获取文章失败: {e}")
            logger.exception("详细错误信息:")
            return []
    
    def _get_fakeid_by_name(self, account_name):
        """通过公众号名称获取fakeid（如果可能的话）"""
        try:
            # 这里可以实现通过搜索接口获取fakeid的逻辑
            # 暂时返回空字符串，依赖搜索方式作为备用方案
            return ''
        except Exception as e:
            logger.warning(f"获取fakeid失败: {e}")
            return ''
    
    def _collect_articles_by_search(self, account_name, max_articles):
        """通过搜索方式采集文章（备用方案）"""
        try:
            # 1. 搜索公众号
            account_info = self._search_account(account_name)
            if not account_info:
                logger.error(f"未找到公众号: {account_name}")
                return []
            
            logger.info(f"找到公众号: {account_info['name']}")
            
            # 2. 获取文章列表
            articles = self._get_article_list(account_info, max_articles)
            logger.info(f"获取到 {len(articles)} 篇文章")
            
            return self._process_articles(articles, account_name)
            
        except Exception as e:
            logger.error(f"搜索方式采集失败: {e}")
            return []
    
    def _process_articles(self, articles, account_name):
        """处理文章列表，获取详情并保存"""
        collected_articles = []
        account_dir = self.base_output_dir / self._safe_filename(account_name)
        account_dir.mkdir(parents=True, exist_ok=True)
        
        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"采集第 {i}/{len(articles)} 篇: {article['title'][:30]}...")
                
                # 获取文章详情
                article_detail = self._get_article_detail(article['url'])
                if article_detail:
                    # 合并文章信息
                    full_article = {**article, **article_detail}
                    full_article['account_name'] = account_name
                    full_article['collected_at'] = datetime.now().isoformat()
                    
                    # 保存到文件
                    self._save_article_to_file(full_article, account_dir)
                    collected_articles.append(full_article)
                    
                    self.stats['success_count'] += 1
                    logger.info(f"采集成功: {full_article['title'][:30]}")
                else:
                    logger.warning(f"获取文章详情失败: {article['title'][:30]}")
                    self.stats['error_count'] += 1
                
                # 控制采集速度，避免被限制
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"采集文章失败: {e}")
                self.stats['error_count'] += 1
                continue
        
        self.stats['total_collected'] = len(collected_articles)
        logger.info(f"采集完成: 成功 {self.stats['success_count']} 篇，失败 {self.stats['error_count']} 篇")
        
        return collected_articles
    
    def _convert_timestamp(self, timestamp):
        """转换时间戳为日期字符串"""
        try:
            if timestamp:
                dt = datetime.fromtimestamp(int(timestamp))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            return datetime.now().strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def _search_account(self, account_name):
        """搜索公众号 - 改进的搜索策略"""
        try:
            # 更新搜狗微信搜索URL和参数
            search_params = {
                'type': '1',  # 搜索公众号
                'query': account_name,
                'ie': 'utf8',
                's_from': 'input',
                '_sug_': '0',
                '_sug_type_': ''
            }
            
            # 设置更完整的headers模拟真实浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # 临时更新headers
            original_headers = self.session.headers.copy()
            self.session.headers.update(headers)
            
            try:
                response = self.session.get(self.sogou_search_url, params=search_params, timeout=15)
                response.raise_for_status()
                
                logger.info(f"搜索请求状态: {response.status_code}")
                logger.info(f"搜索响应长度: {len(response.text)}")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 尝试多种页面结构解析
                account_info = None
                
                # 方法1: 查找results类
                results = soup.find_all('div', class_='results')
                logger.info(f"找到results数量: {len(results)}")
                
                for result in results:
                    name_elem = result.find('p', class_='tit') or result.find('h3') or result.find('h4')
                    if name_elem:
                        name = name_elem.get_text().strip()
                        logger.info(f"检查账号名: {name}")
                        
                        link_elem = name_elem.find('a')
                        if link_elem and (account_name.lower() in name.lower() or name.lower() in account_name.lower()):
                            href = link_elem.get('href')
                            # 确保链接格式正确
                            if href and not href.startswith('http'):
                                href = 'https://weixin.sogou.com' + href
                            
                            account_info = {
                                'name': name,
                                'url': href,
                                'description': result.find('p', class_='info').get_text().strip() if result.find('p', class_='info') else ''
                            }
                            break
                
                # 方法2: 如果方法1没找到，尝试其他选择器
                if not account_info:
                    logger.info("尝试其他页面结构...")
                    # 查找所有可能包含公众号信息的链接
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link.get('href')
                        if href and 'mp.weixin.qq.com' in href:
                            link_text = link.get_text().strip()
                            if account_name.lower() in link_text.lower() or link_text.lower() in account_name.lower():
                                account_info = {
                                    'name': link_text,
                                    'url': href,
                                    'description': ''
                                }
                                break
                
                if account_info:
                    logger.info(f"找到公众号: {account_info['name']} - {account_info['url']}")
                else:
                    logger.warning(f"未找到匹配的公众号: {account_name}")
                    # 打印页面内容的前1000字符用于调试
                    logger.debug(f"页面内容预览: {response.text[:1000]}")
                
                return account_info
                
            finally:
                # 恢复原始headers
                self.session.headers = original_headers
            
        except Exception as e:
            logger.error(f"搜索公众号失败: {e}")
            logger.exception("详细错误信息:")
            return None
    
    def _get_article_list(self, account_info, max_articles):
        """获取公众号文章列表"""
        try:
            response = self.session.get(account_info['url'], timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            
            # 查找文章链接
            article_links = soup.find_all('a', href=True)
            
            for link in article_links:
                href = link.get('href')
                if 'mp.weixin.qq.com/s' in href:
                    title_elem = link.find('h3') or link.find('h4') or link
                    title = title_elem.get_text().strip() if title_elem else '无标题'
                    
                    # 清理URL
                    if href.startswith('http'):
                        clean_url = href
                    else:
                        clean_url = urljoin(account_info['url'], href)
                    
                    articles.append({
                        'title': title,
                        'url': clean_url,
                        'source': '搜狗微信'
                    })
                    
                    if len(articles) >= max_articles:
                        break
            
            return articles
            
        except Exception as e:
            logger.error(f"获取文章列表失败: {e}")
            return []
    
    def _get_article_detail(self, url):
        """获取文章详细内容"""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取文章信息
            article_detail = {
                'url': url,
                'content': '',
                'author': '',
                'publish_time': '',
                'read_count': 0,
                'like_count': 0,
                'comment_count': 0
            }
            
            # 提取内容
            content_div = soup.find('div', {'id': 'js_content'})
            if content_div:
                # 下载并处理图片
                content_div = self._download_images(content_div)
                article_detail['content'] = str(content_div)
            else:
                # 备选方案
                content_div = soup.find('div', {'class': 'rich_media_content'})
                if content_div:
                    content_div = self._download_images(content_div)
                    article_detail['content'] = str(content_div)
            
            # 提取作者
            author_elem = soup.find('span', {'class': 'rich_media_meta_text'}) or \
                         soup.find('a', {'id': 'js_name'}) or \
                         soup.find('strong', {'class': 'profile_nickname'})
            if author_elem:
                article_detail['author'] = author_elem.get_text().strip()
            
            # 提取发布时间
            time_elem = soup.find('em', {'id': 'post-date'}) or \
                       soup.find('span', {'class': 'rich_media_meta_text'})
            if time_elem:
                time_text = time_elem.get_text().strip()
                # 解析时间格式
                try:
                    if '年' in time_text and '月' in time_text:
                        # 解析中文日期格式
                        import re
                        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', time_text)
                        if date_match:
                            year, month, day = date_match.groups()
                            article_detail['publish_time'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif '-' in time_text:
                        article_detail['publish_time'] = time_text.split()[0]  # 取日期部分
                except:
                    pass
            
            # 如果没有获取到发布时间，使用当前时间
            if not article_detail['publish_time']:
                article_detail['publish_time'] = datetime.now().strftime('%Y-%m-%d')
            
            return article_detail
            
        except Exception as e:
            logger.error(f"获取文章详情失败 {url}: {e}")
            return None
    
    def _download_images(self, content_div):
        """下载文章中的图片并替换链接"""
        try:
            # 找到所有图片标签
            img_tags = content_div.find_all('img')
            
            if not img_tags:
                return content_div
                
            # 创建图片存储目录
            images_dir = self.base_output_dir / 'images'
            images_dir.mkdir(parents=True, exist_ok=True)
            
            for img_tag in img_tags:
                try:
                    # 获取图片URL
                    img_src = img_tag.get('src') or img_tag.get('data-src')
                    if not img_src:
                        continue
                    
                    # 确保是完整的URL
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif not img_src.startswith('http'):
                        continue  # 跳过相对路径或无效URL
                    
                    # 生成本地文件名
                    img_filename = self._generate_image_filename(img_src)
                    img_path = images_dir / img_filename
                    
                    # 如果图片已存在，跳过下载
                    if img_path.exists():
                        logger.debug(f"图片已存在: {img_filename}")
                        # 更新图片标签的src为本地路径
                        img_tag['src'] = f"images/{img_filename}"
                        continue
                    
                    # 下载图片
                    logger.info(f"下载图片: {img_src}")
                    img_response = self.session.get(img_src, timeout=30, stream=True)
                    img_response.raise_for_status()
                    
                    # 检查内容类型
                    content_type = img_response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        logger.warning(f"不是有效的图片类型: {content_type}")
                        continue
                    
                    # 保存图片
                    with open(img_path, 'wb') as f:
                        for chunk in img_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f"图片下载成功: {img_filename}")
                    
                    # 更新图片标签的src为本地路径
                    img_tag['src'] = f"images/{img_filename}"
                    
                    # 控制下载速度
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"下载图片失败 {img_src}: {e}")
                    # 保持原始URL
                    continue
            
            return content_div
            
        except Exception as e:
            logger.error(f"处理图片失败: {e}")
            return content_div
    
    def _generate_image_filename(self, img_url):
        """生成图片文件名"""
        try:
            # 从URL中提取文件扩展名
            parsed_url = urlparse(img_url)
            path = parsed_url.path
            
            # 获取文件扩展名
            if '.' in path:
                ext = path.split('.')[-1].lower()
                # 确保是有效的图片扩展名
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
                    pass
                else:
                    ext = 'jpg'  # 默认扩展名
            else:
                ext = 'jpg'  # 默认扩展名
            
            # 生成唯一文件名
            img_hash = hashlib.md5(img_url.encode()).hexdigest()[:16]
            filename = f"img_{img_hash}.{ext}"
            
            return filename
            
        except Exception as e:
            logger.error(f"生成图片文件名失败: {e}")
            # 使用时间戳作为备用文件名
            timestamp = str(int(time.time()))
            return f"img_{timestamp}.jpg"
    
    def _save_article_to_file(self, article, account_dir):
        """保存文章到文件"""
        try:
            # 生成文件名
            filename_base = self._generate_filename(article)
            
            # 保存JSON元数据
            json_path = account_dir / f"{filename_base}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'title': article['title'],
                    'author': article['author'],
                    'publish_time': article['publish_time'],
                    'url': article['url'],
                    'account_name': article['account_name'],
                    'collected_at': article['collected_at'],
                    'summary': article.get('summary', ''),
                    'read_count': article.get('read_count', 0),
                    'like_count': article.get('like_count', 0),
                    'comment_count': article.get('comment_count', 0)
                }, f, ensure_ascii=False, indent=2)
            
            # 保存HTML内容
            html_path = account_dir / f"{filename_base}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(article['content'])
            
            return True
            
        except Exception as e:
            logger.error(f"保存文章文件失败: {e}")
            return False
    
    def _generate_filename(self, article):
        """生成文件名：日期_标题"""
        pub_time = article.get('publish_time', '')
        try:
            if pub_time:
                if '-' in pub_time:
                    date_str = pub_time.split()[0].replace('-', '')
                else:
                    date_str = datetime.now().strftime('%Y%m%d')
            else:
                date_str = datetime.now().strftime('%Y%m%d')
        except:
            date_str = datetime.now().strftime('%Y%m%d')
        
        # 清理标题
        title = article.get('title', '无标题')
        safe_title = self._safe_filename(title)[:30]
        
        # 生成唯一标识
        unique_id = hashlib.md5(article['url'].encode()).hexdigest()[:8]
        
        return f"{date_str}_{unique_id}_{safe_title}"
    
    def _safe_filename(self, text):
        """生成安全文件名"""
        import re
        return re.sub(r'[^\w\s-]', '', text.strip()).replace(' ', '_')
    
    def get_collection_stats(self):
        """获取采集统计"""
        end_time = datetime.now()
        duration = (end_time - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
        
        return {
            **self.stats,
            'end_time': end_time.isoformat() if self.stats['start_time'] else None,
            'duration_seconds': duration,
            'success_rate': self.stats['success_count'] / max(self.stats['total_collected'], 1) * 100
        }