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
        self.fakeid = fakeid
        if cookies:
            self._set_cookies(cookies)
            
        logger.info(f"初始化采集器 - Token: {'已配置' if token else '未配置'}, Fakeid: {'已配置' if fakeid else '未配置'}")
        
        # 微信公众平台API端点
        self.mp_base_url = 'https://mp.weixin.qq.com'
        self.mp_api_base = f'{self.mp_base_url}/cgi-bin'
        
        # 根据storage_type设置保存路径
        if storage_type == 'monitor':
            self.base_output_dir = Path('wechat_articles/storage/monitor_data')
        else:
            self.base_output_dir = Path('wechat_articles/storage/batch_data')
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 采集统计
        self.stats = {
            'total_collected': 0,
            'success_count': 0,
            'error_count': 0,
            'start_time': None
        }
    
    def _set_cookies(self, cookies):
        """设置cookies"""
        try:
            if isinstance(cookies, str):
                cookie_dict = {}
                for item in cookies.split(';'):
                    item = item.strip()
                    if '=' in item:
                        key, value = item.split('=', 1)
                        cookie_dict[key.strip()] = value.strip()
                self.session.cookies.update(cookie_dict)
            elif isinstance(cookies, dict):
                self.session.cookies.update(cookies)
        except Exception as e:
            logger.warning(f"设置cookies失败: {e}")
    
    def collect_and_export_articles(self, account_name, max_articles=20, export_formats=None):
        """采集文章并直接保存为指定格式"""
        if export_formats is None:
            export_formats = ['pdf', 'docx']
            
        logger.info(f"开始采集并导出: {account_name}, 格式: {export_formats}")
        
        articles = self._collect_articles_with_formats(account_name, max_articles, export_formats)
        
        if not articles:
            return {
                'success': False,
                'message': '未采集到任何文章',
                'articles_count': 0,
                'export_stats': {fmt: 0 for fmt in export_formats}
            }
        
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
            elif fmt == 'docx' or fmt == 'word':
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
            if self.token:
                articles = self._get_articles_by_mp_api(account_name, max_articles)
                if articles:
                    logger.info(f"通过微信公众平台API获取到 {len(articles)} 篇文章")
                    return self._process_articles_with_formats(articles, account_name, export_formats)
                else:
                    logger.warning("微信公众平台API获取失败")
            
            logger.error("请配置微信公众平台token和fakeid后使用API方式")
            return []
            
        except Exception as e:
            logger.error(f"采集过程出错: {e}")
            return []
    
    def _process_articles_with_formats(self, articles, account_name, export_formats):
        """处理文章列表，获取详情并保存为多种格式"""
        collected_articles = []
        account_dir = self.base_output_dir / self._safe_filename(account_name)
        account_dir.mkdir(parents=True, exist_ok=True)
        
        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"采集第 {i}/{len(articles)} 篇: {article['title'][:30]}...")
                
                article_detail = self._get_article_detail(article['url'])
                if article_detail:
                    full_article = {**article, **article_detail}
                    full_article['account_name'] = account_name
                    full_article['collected_at'] = datetime.now().isoformat()
                    
                    self._save_article_in_formats(full_article, account_dir, export_formats)
                    collected_articles.append(full_article)
                    
                    self.stats['success_count'] += 1
                    logger.info(f"采集成功: {full_article['title'][:30]}")
                else:
                    logger.warning(f"获取文章详情失败: {article['title'][:30]}")
                    self.stats['error_count'] += 1
                
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
            filename_base = self._generate_filename(article)
            logger.info(f"保存文章格式: {export_formats}, 文件名: {filename_base}")
            
            for fmt in export_formats:
                logger.info(f"处理格式: {fmt}")
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
                elif fmt == 'docx' or fmt == 'word':
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
        
        content = article['content']
        soup = BeautifulSoup(content, 'html.parser')
        
        # 更新图片路径
        img_tags = soup.find_all('img')
        for img_tag in img_tags:
            src = img_tag.get('src', '')
            if src.startswith('images/'):
                img_tag['src'] = f"../{src}"
        
        with open(html_path, 'w', encoding='utf-8') as f:
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
        .content img {{ max-width: 100%; height: auto; display: block; margin: 10px auto; }}
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
        {str(soup)}
    </div>
</body>
</html>"""
            f.write(html_content)
    
    def _save_as_txt(self, article, account_dir, filename_base):
        """保存为纯文本格式"""
        txt_path = account_dir / f"{filename_base}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            soup = BeautifulSoup(article['content'], 'html.parser')
            text_content = soup.get_text()
            
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
            soup = BeautifulSoup(article['content'], 'html.parser')
            
            content = article['content']
            content = re.sub(r'<h([1-6])>(.*?)</h[1-6]>', r'\n# \2\n', content)
            content = re.sub(r'<p>(.*?)</p>', r'\1\n\n', content)
            content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', content)
            content = re.sub(r'<em>(.*?)</em>', r'*\1*', content)
            content = re.sub(r'<br\s*/?>', '\n', content)
            content = re.sub(r'<[^>]+>', '', content)
            
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
            
            # 注册中文字体 - 完整的字体支持策略
            chinese_font_registered = False
            font_name = 'Helvetica'  # 默认字体
            
            try:
                # 尝试注册系统中文字体，按优先级排序
                font_paths = [
                    # macOS 字体
                    '/System/Library/Fonts/PingFang.ttc',
                    '/System/Library/Fonts/Supplemental/Songti.ttc',
                    '/System/Library/Fonts/Supplemental/Kaiti.ttc',
                    '/System/Library/Fonts/Helvetica.ttc',
                    
                    # Linux 字体
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                    '/usr/share/fonts/truetype/arphic/ukai.ttc',
                    '/usr/share/fonts/truetype/arphic/uming.ttc',
                    
                    # Windows 字体
                    'C:/Windows/Fonts/msyh.ttc',     # 微软雅黑
                    'C:/Windows/Fonts/simsun.ttc',   # 宋体
                    'C:/Windows/Fonts/simhei.ttf',   # 黑体
                    'C:/Windows/Fonts/simkai.ttf',   # 楷体
                ]
                
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            font_name = 'ChineseFont'
                            chinese_font_registered = True
                            logger.info(f"成功注册中文字体: {font_path}")
                            break
                        except Exception as e:
                            logger.debug(f"字体注册失败 {font_path}: {e}")
                            continue
                
                # 如果系统字体都失败，尝试使用reportlab内置的CID字体
                if not chinese_font_registered:
                    try:
                        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
                        # 尝试多种CID字体
                        cid_fonts = ['STSong-Light', 'STHeiti-Regular', 'STKaiti-Regular']
                        for cid_font in cid_fonts:
                            try:
                                pdfmetrics.registerFont(UnicodeCIDFont(cid_font))
                                font_name = cid_font
                                chinese_font_registered = True
                                logger.info(f"使用CID字体: {cid_font}")
                                break
                            except:
                                continue
                    except ImportError:
                        pass
                    
            except Exception as e:
                logger.warning(f"字体注册过程失败: {e}")
            
            # 如果没有成功注册中文字体，记录警告
            if not chinese_font_registered:
                logger.warning("未能注册中文字体，可能出现中文显示问题")
            
            # 创建PDF文档
            doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, 
                                  topMargin=1*inch, bottomMargin=1*inch,
                                  leftMargin=0.75*inch, rightMargin=0.75*inch)
            story = []
            
            # 设置样式 - 确保使用支持中文的字体
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=20,
                spaceBefore=10,
                wordWrap='LTR'
            )
            
            meta_style = ParagraphStyle(
                'CustomMeta',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=11,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor='#666666',
                wordWrap='LTR'
            )
            
            content_style = ParagraphStyle(
                'CustomContent',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=12,
                alignment=TA_LEFT,
                spaceAfter=8,
                spaceBefore=4,
                leftIndent=0,
                rightIndent=0,
                wordWrap='LTR',
                leading=18  # 行间距
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=16,
                alignment=TA_LEFT,
                spaceAfter=12,
                spaceBefore=20,
                wordWrap='LTR'
            )
            
            # 添加标题
            story.append(Paragraph(article['title'], title_style))
            
            # 添加元信息
            meta_text = f"作者: {article['author']} | 发布时间: {article['publish_time']} | 来源: {article['account_name']}"
            story.append(Paragraph(meta_text, meta_style))
            story.append(Spacer(1, 20))
            
            # 处理内容
            soup = BeautifulSoup(article['content'], 'html.parser')
            self._add_html_to_pdf_story(soup, story, content_style, heading_style)
            
            # 生成PDF
            doc.build(story)
            logger.info(f"PDF生成成功: {pdf_path}")
            
        except ImportError as e:
            logger.warning(f"reportlab未安装: {e}")
            self._create_text_fallback_for_pdf(article, account_dir, filename_base)
        except Exception as e:
            logger.error(f"PDF生成失败: {e}")
            logger.exception("详细错误信息:")
            self._create_text_fallback_for_pdf(article, account_dir, filename_base)
    
    def _add_html_to_pdf_story(self, soup, story, content_style, heading_style):
        """将HTML内容添加到PDF story中"""
        from reportlab.platypus import Paragraph, Spacer, Image
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        
        # 查找主内容区域
        content_div = soup.find('div', {'id': 'js_content'}) or soup.find('div', {'class': 'rich_media_content'}) or soup
        
        # 按顺序处理所有元素
        for element in content_div.find_all(['p', 'div', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            try:
                if element.name == 'img':
                    # 处理图片
                    img_src = element.get('src', '')
                    if img_src.startswith('images/'):
                        img_path = self.base_output_dir / img_src
                        if img_path.exists() and self._validate_image_file(img_path):
                            # 转换图片格式以确保PDF兼容性
                            compatible_img_path = self._convert_image_for_office(img_path)
                            if compatible_img_path:
                                try:
                                    img = Image(str(compatible_img_path))
                                    # 改进的图片缩放逻辑
                                    page_width, page_height = A4
                                    max_width = page_width - 4*inch  # 增加页边距
                                    max_height = page_height - 6*inch  # 增加上下边距
                                    
                                    # 计算缩放比例
                                    width_scale = max_width / img.drawWidth if img.drawWidth > max_width else 1
                                    height_scale = max_height / img.drawHeight if img.drawHeight > max_height else 1
                                    scale = min(width_scale, height_scale, 0.8)  # 最大缩放80%
                                    
                                    # 应用缩放，确保最小尺寸
                                    img.drawWidth = max(img.drawWidth * scale, inch)
                                    img.drawHeight = max(img.drawHeight * scale, 0.5*inch)
                                    
                                    # 确保尺寸不超过限制
                                    if img.drawWidth > max_width:
                                        scale_fix = max_width / img.drawWidth
                                        img.drawWidth = max_width
                                        img.drawHeight = img.drawHeight * scale_fix
                                    
                                    if img.drawHeight > max_height:
                                        scale_fix = max_height / img.drawHeight
                                        img.drawHeight = max_height
                                        img.drawWidth = img.drawWidth * scale_fix
                                    
                                    story.append(img)
                                    story.append(Spacer(1, 12))
                                    logger.info(f"PDF添加图片: {img_src} ({img.drawWidth:.1f}x{img.drawHeight:.1f})")
                                except Exception as e:
                                    logger.warning(f"PDF图片处理失败 {img_src}: {e}")
                                    # 添加占位文本
                                    story.append(Paragraph(f"[图片处理失败: {img_src}]", content_style))
                            else:
                                logger.warning(f"PDF图片转换失败: {img_src}")
                                story.append(Paragraph(f"[图片转换失败: {img_src}]", content_style))
                        else:
                            logger.warning(f"图片文件不存在或无效: {img_path}")
                            story.append(Paragraph(f"[图片文件缺失: {img_src}]", content_style))
                
                elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # 处理标题
                    text = element.get_text(strip=True)
                    if text:
                        story.append(Paragraph(text, heading_style))
                        story.append(Spacer(1, 12))
                
                else:
                    # 处理段落，检查是否包含图片
                    if element.find('img'):
                        # 包含图片的段落，需要分别处理文本和图片
                        for child in element.children:
                            if hasattr(child, 'name') and child.name == 'img':
                                img_src = child.get('src', '')
                                if img_src.startswith('images/'):
                                    img_path = self.base_output_dir / img_src
                                    if img_path.exists() and self._validate_image_file(img_path):
                                        # 转换图片格式以确保PDF兼容性
                                        compatible_img_path = self._convert_image_for_office(img_path)
                                        if compatible_img_path:
                                            try:
                                                img = Image(str(compatible_img_path))
                                                # 相同的缩放逻辑
                                                page_width, page_height = A4
                                                max_width = page_width - 4*inch
                                                max_height = page_height - 6*inch
                                                
                                                width_scale = max_width / img.drawWidth if img.drawWidth > max_width else 1
                                                height_scale = max_height / img.drawHeight if img.drawHeight > max_height else 1
                                                scale = min(width_scale, height_scale, 0.8)
                                                
                                                img.drawWidth = max(img.drawWidth * scale, inch)
                                                img.drawHeight = max(img.drawHeight * scale, 0.5*inch)
                                                
                                                if img.drawWidth > max_width:
                                                    scale_fix = max_width / img.drawWidth
                                                    img.drawWidth = max_width
                                                    img.drawHeight = img.drawHeight * scale_fix
                                                
                                                if img.drawHeight > max_height:
                                                    scale_fix = max_height / img.drawHeight
                                                    img.drawHeight = max_height
                                                    img.drawWidth = img.drawWidth * scale_fix
                                                
                                                story.append(img)
                                                story.append(Spacer(1, 12))
                                                logger.info(f"PDF添加段落图片: {img_src} ({img.drawWidth:.1f}x{img.drawHeight:.1f})")
                                            except Exception as e:
                                                logger.warning(f"PDF段落图片处理失败 {img_src}: {e}")
                                                story.append(Paragraph(f"[图片处理失败: {img_src}]", content_style))
                                        else:
                                            logger.warning(f"PDF段落图片转换失败: {img_src}")
                                            story.append(Paragraph(f"[图片转换失败: {img_src}]", content_style))
                            elif hasattr(child, 'get_text'):
                                text = child.get_text(strip=True)
                                if text:
                                    story.append(Paragraph(text, content_style))
                                    story.append(Spacer(1, 6))
                    else:
                        # 纯文本段落
                        text = element.get_text(strip=True)
                        if text:
                            story.append(Paragraph(text, content_style))
                            story.append(Spacer(1, 6))
                            
            except Exception as e:
                logger.warning(f"PDF元素处理失败: {e}")
                continue
    
    def _save_as_docx(self, article, account_dir, filename_base):
        """保存为Word格式 - 确保能够正常生成包含图片的Word文档"""
        docx_path = account_dir / f"{filename_base}.docx"
        logger.info(f"开始生成Word文档: {docx_path}")
        
        try:
            from docx import Document
            from docx.shared import Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.enum.style import WD_STYLE_TYPE
            from bs4 import BeautifulSoup
            
            # 创建Word文档
            doc = Document()
            
            # 设置文档样式
            try:
                # 创建自定义样式
                styles = doc.styles
                
                # 标题样式
                if 'CustomTitle' not in [style.name for style in styles]:
                    title_style = styles.add_style('CustomTitle', WD_STYLE_TYPE.PARAGRAPH)
                    title_style.font.size = Inches(0.2)  # 约16pt
                    title_style.font.bold = True
                    title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    title_style.paragraph_format.space_after = Inches(0.1)
                
                # 正文样式
                if 'CustomNormal' not in [style.name for style in styles]:
                    normal_style = styles.add_style('CustomNormal', WD_STYLE_TYPE.PARAGRAPH)
                    normal_style.font.size = Inches(0.1)  # 约12pt
                    normal_style.paragraph_format.line_spacing = 1.5
                    normal_style.paragraph_format.space_after = Inches(0.05)
                    
            except Exception as e:
                logger.debug(f"创建自定义样式失败: {e}")
            
            # 添加标题
            title_para = doc.add_heading(level=0)
            title_run = title_para.runs[0] if title_para.runs else title_para.add_run()
            title_run.text = article['title']
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 添加分隔线
            doc.add_paragraph()
            
            # 添加元信息
            meta_para = doc.add_paragraph()
            meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            meta_run = meta_para.add_run(f"作者: {article['author']} | 发布时间: {article['publish_time']} | 来源: {article['account_name']}")
            meta_run.font.size = Inches(0.08)  # 约10pt
            try:
                meta_run.font.color.rgb = RGBColor(102, 102, 102)  # 灰色
            except:
                pass
            
            # 添加分隔线
            separator_para = doc.add_paragraph('_' * 50)
            separator_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 添加空行
            doc.add_paragraph()
            
            # 处理内容 - 确保图片和文本都能正确处理
            soup = BeautifulSoup(article['content'], 'html.parser')
            processed_count = self._add_html_to_docx(soup, doc)
            
            # 如果没有处理任何内容，添加纯文本内容
            if processed_count == 0:
                logger.warning("Word文档没有处理任何HTML内容，添加纯文本")
                text_content = soup.get_text(strip=True)
                if text_content:
                    # 分段落添加
                    paragraphs = text_content.split('\n')
                    for para_text in paragraphs:
                        para_text = para_text.strip()
                        if para_text:
                            doc.add_paragraph(para_text)
                else:
                    doc.add_paragraph("文章内容为空或解析失败")
            
            # 保存文档
            logger.info(f"准备保存Word文档到: {docx_path}")
            doc.save(str(docx_path))
            
            # 验证文件是否成功创建
            if docx_path.exists():
                file_size = docx_path.stat().st_size
                logger.info(f"Word文档生成成功: {docx_path} (大小: {file_size} bytes)")
            else:
                logger.error(f"Word文档保存失败，文件未生成: {docx_path}")
            
        except ImportError as e:
            logger.warning(f"python-docx未安装: {e}")
            logger.info("尝试安装: pip install python-docx")
            self._create_text_fallback_for_docx(article, account_dir, filename_base)
        except Exception as e:
            logger.error(f"Word文档生成失败: {e}")
            logger.exception("详细错误信息:")
            self._create_text_fallback_for_docx(article, account_dir, filename_base)
    
    def _add_html_to_docx(self, soup, doc):
        """将HTML内容添加到Word文档中"""
        from docx.shared import Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        # 查找主内容区域
        content_div = soup.find('div', {'id': 'js_content'}) or soup.find('div', {'class': 'rich_media_content'}) or soup
        
        processed_count = 0
        
        # 按顺序处理所有元素
        for element in content_div.find_all(['p', 'div', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            try:
                if element.name == 'img':
                    # 处理图片
                    img_src = element.get('src', '')
                    logger.debug(f"处理图片: {img_src}")
                    if img_src.startswith('images/'):
                        # 修正图片路径计算
                        img_path = self.base_output_dir / img_src
                        logger.debug(f"图片路径: {img_path}")
                        if img_path.exists() and self._validate_image_file(img_path):
                            # 转换图片格式以确保兼容性
                            compatible_img_path = self._convert_image_for_office(img_path)
                            if compatible_img_path:
                                try:
                                    paragraph = doc.add_paragraph()
                                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
                                    
                                    # 获取图片尺寸并插入
                                    try:
                                        from PIL import Image as PILImage
                                        with PILImage.open(compatible_img_path) as pil_img:
                                            width, height = pil_img.size
                                            logger.debug(f"转换后图片尺寸: {width}x{height}")
                                            
                                            # 根据图片比例调整大小
                                            if width > height:
                                                max_width = Inches(6.5)  
                                            else:
                                                max_width = Inches(4.5)
                                            run.add_picture(str(compatible_img_path), width=max_width)
                                            logger.info(f"图片插入成功: {img_src}")
                                    except Exception as e:
                                        # 使用默认尺寸插入
                                        max_width = Inches(5)
                                        run.add_picture(str(compatible_img_path), width=max_width)
                                        logger.info(f"图片插入成功(默认尺寸): {img_src}")
                                    
                                    processed_count += 1
                                except Exception as e:
                                    logger.error(f"图片插入失败 {img_src}: {str(e)}")
                                    doc.add_paragraph(f"[图片插入失败: {img_src}]")
                                    processed_count += 1
                            else:
                                logger.warning(f"图片转换失败: {img_src}")
                                doc.add_paragraph(f"[图片转换失败: {img_src}]")
                                processed_count += 1
                        else:
                            logger.warning(f"图片文件不存在或无效: {img_path}")
                            doc.add_paragraph(f"[图片文件缺失: {img_src}]")
                            processed_count += 1
                
                elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # 处理标题
                    text = element.get_text(strip=True)
                    if text:
                        level = int(element.name[1])
                        # 限制标题级别，Word最多支持9级
                        level = min(level, 6)
                        doc.add_heading(text, level)
                        processed_count += 1
                
                else:
                    # 处理段落
                    if element.find('img'):
                        # 包含图片的段落 - 需要分别处理文本和图片
                        paragraph_text_parts = []
                        
                        for child in element.children:
                            if hasattr(child, 'name') and child.name == 'img':
                                # 先添加之前的文本（如果有）
                                if paragraph_text_parts:
                                    text_content = ''.join(paragraph_text_parts).strip()
                                    if text_content:
                                        self._add_formatted_paragraph(doc, text_content, element)
                                        processed_count += 1
                                    paragraph_text_parts = []
                                
                                # 处理图片
                                img_src = child.get('src', '')
                                logger.debug(f"处理段落图片: {img_src}")
                                if img_src.startswith('images/'):
                                    img_path = self.base_output_dir / img_src
                                    logger.debug(f"段落图片路径: {img_path}")
                                    if img_path.exists() and self._validate_image_file(img_path):
                                        # 转换图片格式以确保兼容性
                                        compatible_img_path = self._convert_image_for_office(img_path)
                                        if compatible_img_path:
                                            try:
                                                paragraph = doc.add_paragraph()
                                                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                                run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
                                                
                                                # 获取图片尺寸并插入
                                                try:
                                                    from PIL import Image as PILImage
                                                    with PILImage.open(compatible_img_path) as pil_img:
                                                        width, height = pil_img.size
                                                        logger.debug(f"段落转换后图片尺寸: {width}x{height}")
                                                        
                                                        if width > height:
                                                            max_width = Inches(6.5)
                                                        else:
                                                            max_width = Inches(4.5)
                                                        run.add_picture(str(compatible_img_path), width=max_width)
                                                        logger.info(f"段落图片插入成功: {img_src}")
                                                except Exception:
                                                    # 使用默认尺寸插入
                                                    max_width = Inches(5)
                                                    run.add_picture(str(compatible_img_path), width=max_width)
                                                    logger.info(f"段落图片插入成功(默认尺寸): {img_src}")
                                                
                                                processed_count += 1
                                            except Exception as e:
                                                logger.error(f"段落图片插入失败 {img_src}: {str(e)}")
                                                doc.add_paragraph(f"[图片插入失败: {img_src}]")
                                                processed_count += 1
                                        else:
                                            logger.warning(f"段落图片转换失败: {img_src}")
                                            doc.add_paragraph(f"[图片转换失败: {img_src}]")
                                            processed_count += 1
                                    else:
                                        logger.warning(f"段落图片文件不存在或无效: {img_path}")
                                        doc.add_paragraph(f"[图片文件缺失: {img_src}]")
                                        processed_count += 1
                            else:
                                # 收集文本内容
                                if hasattr(child, 'get_text'):
                                    paragraph_text_parts.append(child.get_text())
                                elif isinstance(child, str):
                                    paragraph_text_parts.append(child)
                        
                        # 处理最后的文本部分
                        if paragraph_text_parts:
                            text_content = ''.join(paragraph_text_parts).strip()
                            if text_content:
                                self._add_formatted_paragraph(doc, text_content, element)
                                processed_count += 1
                    else:
                        # 纯文本段落 - 保留格式
                        text = element.get_text(strip=True)
                        if text:
                            self._add_formatted_paragraph(doc, text, element)
                            processed_count += 1
                            
            except Exception as e:
                logger.warning(f"Word元素处理失败: {e}")
                continue
        
        logger.info(f"Word文档处理了 {processed_count} 个元素")
        return processed_count
        
    def _convert_image_for_office(self, img_path):
        """转换图片格式以确保与Office软件兼容"""
        try:
            from PIL import Image as PILImage
            import io
            
            # 检查文件是否存在
            if not img_path.exists():
                logger.warning(f"图片文件不存在: {img_path}")
                return None
            
            file_ext = img_path.suffix.lower()
            
            # SVG文件需要特殊处理
            if file_ext == '.svg':
                try:
                    # 尝试使用cairosvg转换SVG
                    try:
                        import cairosvg
                        png_path = img_path.with_suffix('.png')
                        cairosvg.svg2png(url=str(img_path), write_to=str(png_path))
                        logger.info(f"SVG转PNG成功: {png_path}")
                        return png_path
                    except ImportError:
                        logger.debug("cairosvg未安装，尝试其他方法")
                    
                    # 备用方案：使用Pillow处理（如果支持）
                    try:
                        from PIL import Image as PILImage
                        import subprocess
                        
                        # 尝试使用系统工具转换
                        png_path = img_path.with_suffix('.png')
                        # 创建一个简单的占位图片
                        placeholder_img = PILImage.new('RGB', (200, 100), color='lightgray')
                        placeholder_img.save(png_path)
                        logger.warning(f"SVG转换失败，创建占位图片: {png_path}")
                        return png_path
                    except Exception as e:
                        logger.warning(f"SVG处理完全失败: {e}")
                        return None
                        
                except Exception as e:
                    logger.warning(f"SVG转换失败: {e}")
                    return None
            
            # 检查是否是WebP格式但扩展名错误
            with open(img_path, 'rb') as f:
                header = f.read(12)
                
            is_webp = header.startswith(b'RIFF') and b'WEBP' in header
            
            if is_webp or file_ext == '.webp':
                try:
                    with PILImage.open(img_path) as pil_img:
                        # 转换WebP为PNG
                        png_path = img_path.with_suffix('.png')
                        
                        # 如果有透明通道，保持RGBA模式，否则转为RGB
                        if pil_img.mode in ('RGBA', 'LA'):
                            pil_img.save(png_path, 'PNG')
                        else:
                            rgb_img = pil_img.convert('RGB')
                            rgb_img.save(png_path, 'PNG')
                        
                        logger.info(f"WebP转PNG成功: {png_path}")
                        return png_path
                        
                except Exception as e:
                    logger.error(f"WebP转换失败: {e}")
                    return None
            
            # 对于其他格式，检查PIL是否能打开
            try:
                with PILImage.open(img_path) as pil_img:
                    # 如果能正常打开且格式兼容，直接返回
                    if pil_img.format in ['JPEG', 'PNG', 'GIF', 'BMP']:
                        logger.debug(f"图片格式兼容: {pil_img.format}")
                        return img_path
                    else:
                        # 转换为PNG
                        png_path = img_path.with_suffix('.png')
                        if pil_img.mode in ('RGBA', 'LA'):
                            pil_img.save(png_path, 'PNG')
                        else:
                            rgb_img = pil_img.convert('RGB')
                            rgb_img.save(png_path, 'PNG')
                        logger.info(f"图片转PNG成功: {png_path}")
                        return png_path
                        
            except Exception as e:
                logger.error(f"图片格式检查失败: {e}")
                return None
                
        except Exception as e:
            logger.error(f"图片转换过程失败: {e}")
            return None
    
    def _add_formatted_paragraph(self, doc, text_content, original_element):
        """添加带格式的段落到Word文档"""
        try:
            from docx.shared import RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            
            paragraph = doc.add_paragraph()
            
            # 检查原始元素中的格式化子元素
            if hasattr(original_element, 'find_all'):
                # 如果有格式化元素，按顺序处理
                formatted_elements = original_element.find_all(['strong', 'b', 'em', 'i', 'span', 'font'])
                if formatted_elements:
                    self._process_formatted_text(paragraph, original_element)
                else:
                    # 简单文本
                    paragraph.add_run(text_content)
            else:
                # 纯文本
                paragraph.add_run(text_content)
                
            return paragraph
            
        except Exception as e:
            logger.debug(f"格式化段落处理失败，使用纯文本: {e}")
            # 回退到简单文本
            return doc.add_paragraph(text_content)
    
    def _process_formatted_text(self, paragraph, element):
        """处理带格式的文本元素"""
        try:
            from docx.shared import RGBColor
            
            for child in element.children:
                if isinstance(child, str):
                    # 纯文本节点
                    if child.strip():
                        paragraph.add_run(child)
                elif hasattr(child, 'name'):
                    text = child.get_text()
                    if not text.strip():
                        continue
                        
                    run = paragraph.add_run(text)
                    
                    # 处理加粗
                    if child.name in ['strong', 'b']:
                        run.bold = True
                        logger.debug(f"应用加粗格式: {text[:20]}...")
                    
                    # 处理斜体
                    elif child.name in ['em', 'i']:
                        run.italic = True
                        logger.debug(f"应用斜体格式: {text[:20]}...")
                    
                    # 处理span和font标签中的样式
                    elif child.name in ['span', 'font']:
                        style_attr = child.get('style', '')
                        color_attr = child.get('color', '')
                        
                        # 检查颜色
                        color = None
                        if 'color:' in style_attr:
                            # 从style属性中提取颜色
                            import re
                            color_match = re.search(r'color:\s*([^;]+)', style_attr)
                            if color_match:
                                color = color_match.group(1).strip()
                        elif color_attr:
                            color = color_attr
                        
                        if color:
                            try:
                                # 处理常见颜色格式
                                if color.lower() == 'red' or color == '#ff0000' or color == '#FF0000':
                                    run.font.color.rgb = RGBColor(255, 0, 0)
                                    logger.debug(f"应用红色格式: {text[:20]}...")
                                elif color.lower() == 'blue' or color == '#0000ff' or color == '#0000FF':
                                    run.font.color.rgb = RGBColor(0, 0, 255)
                                elif color.lower() == 'green' or color == '#00ff00' or color == '#00FF00':
                                    run.font.color.rgb = RGBColor(0, 255, 0)
                                elif color.startswith('#') and len(color) == 7:
                                    # 十六进制颜色
                                    r = int(color[1:3], 16)
                                    g = int(color[3:5], 16)
                                    b = int(color[5:7], 16)
                                    run.font.color.rgb = RGBColor(r, g, b)
                                    logger.debug(f"应用颜色格式 {color}: {text[:20]}...")
                            except Exception as e:
                                logger.debug(f"颜色处理失败: {e}")
                        
                        # 检查加粗
                        if 'font-weight:' in style_attr and ('bold' in style_attr or '700' in style_attr):
                            run.bold = True
                            logger.debug(f"应用样式加粗: {text[:20]}...")
                    
                    # 递归处理嵌套的格式化元素
                    if child.find_all(['strong', 'b', 'em', 'i', 'span', 'font']):
                        # 如果还有嵌套的格式化元素，递归处理
                        nested_paragraph = paragraph._element.getparent()
                        self._process_formatted_text(paragraph, child)
        
        except Exception as e:
            logger.debug(f"格式化文本处理失败: {e}")
            # 回退到简单文本
            paragraph.add_run(element.get_text())
    
    
    def _get_articles_by_mp_api(self, account_name, max_articles=20):
        """使用微信公众平台API获取文章列表"""
        try:
            if not self.token or not self.fakeid:
                logger.warning("缺少token或fakeid")
                return []
            
            url = f"{self.mp_api_base}/appmsg"
            params = {
                'action': 'list_ex',
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': '1',
                'random': str(int(time.time() * 1000)),
                'query': '',
                'begin': '0',
                'count': str(min(max_articles, 20)),
                'type': '9',
                'fakeid': self.fakeid,
            }
            
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
            }
            self.session.headers.update(headers)
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'base_resp' in data and data.get('base_resp', {}).get('ret') == 0:
                app_msg_list = data.get('app_msg_list', [])
            elif 'app_msg_list' in data:
                app_msg_list = data.get('app_msg_list', [])
            else:
                logger.error("API返回格式错误")
                return []
            
            articles = []
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
                
        except Exception as e:
            logger.error(f"API获取文章失败: {e}")
            return []
    
    def _get_article_detail(self, url):
        """获取文章详细内容"""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            article_detail = {
                'url': url,
                'content': '',
                'author': '',
                'publish_time': '',
                'read_count': 0,
                'like_count': 0,
                'comment_count': 0
            }
            
            # 提取内容 - 多种选择器策略
            content_div = None
            content_selectors = [
                {'id': 'js_content'},
                {'class': 'rich_media_content'},
                {'class': 'rich_media_area_primary'},
                {'class': 'appmsg_wrapper'},
            ]
            
            for selector in content_selectors:
                content_div = soup.find('div', selector)
                if content_div:
                    logger.info(f"找到内容容器: {selector}")
                    break
            
            if not content_div:
                # 查找最大文本容器
                all_divs = soup.find_all('div')
                max_text_length = 0
                for div in all_divs:
                    text_length = len(div.get_text(strip=True))
                    if text_length > max_text_length and text_length > 100:
                        max_text_length = text_length
                        content_div = div
            
            if content_div:
                # 下载图片并处理内容
                content_div = self._download_images(content_div)
                article_detail['content'] = str(content_div)
                logger.info(f"内容提取成功，长度: {len(article_detail['content'])}")
            else:
                logger.warning("未找到合适的内容容器")
                article_detail['content'] = soup.get_text()
            
            # 提取作者
            author_elem = soup.find('span', {'class': 'rich_media_meta_text'}) or soup.find('a', {'id': 'js_name'})
            if author_elem:
                article_detail['author'] = author_elem.get_text().strip()
            
            # 提取发布时间
            time_elem = soup.find('em', {'id': 'post-date'})
            if time_elem:
                article_detail['publish_time'] = time_elem.get_text().strip()
            
            if not article_detail['publish_time']:
                article_detail['publish_time'] = datetime.now().strftime('%Y-%m-%d')
            
            return article_detail
            
        except Exception as e:
            logger.error(f"获取文章详情失败: {e}")
            return None
    
    def _download_images(self, content_div):
        """下载文章中的图片"""
        try:
            img_tags = content_div.find_all('img')
            
            if not img_tags:
                logger.info("没有找到图片")
                return content_div
                
            images_dir = self.base_output_dir / 'images'
            images_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"图片保存目录: {images_dir}")
            
            for img_tag in img_tags:
                try:
                    img_src = img_tag.get('src') or img_tag.get('data-src')
                    if not img_src:
                        continue
                    
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif not img_src.startswith('http'):
                        continue
                    
                    img_filename = self._generate_image_filename(img_src)
                    img_path = images_dir / img_filename
                    
                    if img_path.exists():
                        # 验证已存在的图片文件是否完整
                        if self._validate_image_file(img_path):
                            logger.debug(f"图片已存在且完整: {img_filename}")
                            img_tag['src'] = f"images/{img_filename}"
                            continue
                        else:
                            logger.warning(f"已存在图片文件损坏，重新下载: {img_filename}")
                            img_path.unlink()  # 删除损坏的文件
                    
                    logger.info(f"下载图片: {img_src}")
                    
                    # 设置更好的请求头
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Cache-Control': 'no-cache',
                        'Referer': 'https://mp.weixin.qq.com/'
                    }
                    
                    img_response = self.session.get(img_src, headers=headers, timeout=30, stream=True)
                    img_response.raise_for_status()
                    
                    # 检查内容类型和大小
                    content_type = img_response.headers.get('content-type', '')
                    content_length = img_response.headers.get('content-length')
                    
                    if not content_type.startswith('image/'):
                        logger.warning(f"非图片类型 {content_type}: {img_src}")
                        continue
                    
                    if content_length and int(content_length) < 100:
                        logger.warning(f"图片文件太小 {content_length} bytes，可能无效: {img_src}")
                        continue
                    
                    # 保存图片
                    with open(img_path, 'wb') as f:
                        for chunk in img_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    # 验证下载的图片文件
                    if self._validate_image_file(img_path):
                        logger.info(f"图片下载成功: {img_filename}")
                        img_tag['src'] = f"images/{img_filename}"
                    else:
                        logger.error(f"下载的图片文件无效，删除: {img_filename}")
                        img_path.unlink()
                        continue
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"下载图片失败 {img_src}: {e}")
                    continue
            
            logger.info(f"图片处理完成，共处理 {len(img_tags)} 个图片")
            return content_div
            
        except Exception as e:
            logger.error(f"图片处理失败: {e}")
            return content_div
    
    def _validate_image_file(self, img_path):
        """验证图片文件是否有效 - 改进的验证逻辑"""
        try:
            if not img_path.exists():
                return False
            
            # 检查文件大小 - 降低最小大小要求
            file_size = img_path.stat().st_size
            if file_size < 50:  # 从100降到50字节
                logger.debug(f"图片文件太小: {file_size} bytes")
                return False
            
            # 检查文件扩展名，SVG文件特殊处理
            file_ext = img_path.suffix.lower()
            if file_ext == '.svg':
                # SVG文件验证：检查是否包含SVG标签
                try:
                    with open(img_path, 'r', encoding='utf-8') as f:
                        content = f.read(1000)  # 只读前1000字符
                        if '<svg' in content.lower() or '<?xml' in content.lower():
                            logger.debug("SVG文件验证成功")
                            return True
                        else:
                            logger.debug("文件不包含SVG标签")
                            return False
                except Exception as e:
                    logger.debug(f"SVG文件验证失败: {e}")
                    # 如果读取失败但文件存在，可能是二进制SVG
                    return file_size > 200
            
            # 优先使用PIL验证（更准确）- 也能检测实际格式
            try:
                from PIL import Image
                with Image.open(img_path) as img:
                    # 尝试加载图片数据
                    img.load()
                    # 检查图片尺寸
                    width, height = img.size
                    if width > 0 and height > 0:
                        logger.debug(f"PIL验证成功: {img.format} {width}x{height}")
                        return True
                    else:
                        logger.debug(f"图片尺寸无效: {width}x{height}")
                        return False
            except ImportError:
                logger.debug("PIL未安装，使用文件头验证")
            except Exception as e:
                logger.debug(f"PIL验证失败: {e}")
            
            # 备用验证：检查文件头 - 增加WebP支持
            try:
                with open(img_path, 'rb') as f:
                    header = f.read(16)  # 读取更多字节
                    
                    # 检查常见图片格式的文件头
                    if (header.startswith(b'\xFF\xD8\xFF') or  # JPEG
                        header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                        header.startswith(b'GIF87a') or  # GIF87a
                        header.startswith(b'GIF89a') or  # GIF89a
                        (header.startswith(b'RIFF') and b'WEBP' in header) or  # WEBP
                        header.startswith(b'BM')):  # BMP
                        logger.debug("文件头验证成功")
                        return True
                
                # 如果文件头验证失败，但文件不是很小，可能是格式不常见但有效
                if file_size > 1000:  # 大于1KB的文件可能是有效图片
                    logger.debug(f"文件头验证失败但文件较大({file_size}bytes)，可能是有效图片")
                    return True
                
                logger.debug("文件头验证失败且文件较小")
                return False
                
            except Exception as e:
                logger.debug(f"文件头验证失败: {e}")
                # 如果所有验证都失败，但文件存在且不为空，保守地认为有效
                if file_size > 100:
                    logger.debug("验证失败但文件不为空，保守认为有效")
                    return True
                return False
                
        except Exception as e:
            logger.debug(f"图片验证异常: {e}")
            # 异常情况下，如果文件存在就认为有效
            return img_path.exists()
    
    def _generate_image_filename(self, img_url):
        """生成图片文件名"""
        try:
            parsed_url = urlparse(img_url)
            path = parsed_url.path
            
            if '.' in path:
                ext = path.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']:
                    ext = 'jpg'
            else:
                # 检查URL参数中的格式信息
                if 'wx_fmt=svg' in img_url.lower() or 'format=svg' in img_url.lower():
                    ext = 'svg'
                else:
                    ext = 'jpg'
            
            img_hash = hashlib.md5(img_url.encode()).hexdigest()[:16]
            return f"img_{img_hash}.{ext}"
            
        except Exception as e:
            logger.error(f"生成图片文件名失败: {e}")
            timestamp = str(int(time.time()))
            return f"img_{timestamp}.jpg"
    
    def _convert_timestamp(self, timestamp):
        """转换时间戳"""
        try:
            if timestamp:
                dt = datetime.fromtimestamp(int(timestamp))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            return datetime.now().strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def _generate_filename(self, article):
        """生成文件名"""
        pub_time = article.get('publish_time', '')
        try:
            if pub_time and '-' in pub_time:
                date_str = pub_time.split()[0].replace('-', '')
            else:
                date_str = datetime.now().strftime('%Y%m%d')
        except:
            date_str = datetime.now().strftime('%Y%m%d')
        
        title = article.get('title', '无标题')
        safe_title = self._safe_filename(title)[:30]
        unique_id = hashlib.md5(article['url'].encode()).hexdigest()[:8]
        
        return f"{date_str}_{unique_id}_{safe_title}"
    
    def _safe_filename(self, text):
        """生成安全文件名"""
        import re
        safe_text = re.sub(r'[<>:"/\|?*]', '', text.strip())
        safe_text = re.sub(r'\s+', '_', safe_text)
        return safe_text
    
    def _create_text_fallback_for_pdf(self, article, account_dir, filename_base):
        """PDF生成失败时的备用方案"""
        try:
            txt_path = account_dir / f"{filename_base}.pdf.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                soup = BeautifulSoup(article['content'], 'html.parser')
                f.write(f"PDF生成失败，文本内容：\n\n")
                f.write(f"标题: {article['title']}\n")
                f.write(f"作者: {article['author']}\n")
                f.write(f"发布时间: {article['publish_time']}\n")
                f.write(f"来源: {article['account_name']}\n\n")
                f.write(soup.get_text())
            logger.info(f"创建PDF备用文本文件: {txt_path}")
        except Exception as e:
            logger.error(f"创建PDF备用文件失败: {e}")
    
    def _create_text_fallback_for_docx(self, article, account_dir, filename_base):
        """Word生成失败时的备用方案"""
        try:
            txt_path = account_dir / f"{filename_base}.docx.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                soup = BeautifulSoup(article['content'], 'html.parser')
                f.write(f"Word生成失败，文本内容：\n\n")
                f.write(f"标题: {article['title']}\n")
                f.write(f"作者: {article['author']}\n")
                f.write(f"发布时间: {article['publish_time']}\n")
                f.write(f"来源: {article['account_name']}\n\n")
                f.write(soup.get_text())
            logger.info(f"创建Word备用文本文件: {txt_path}")
        except Exception as e:
            logger.error(f"创建Word备用文件失败: {e}")
    
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