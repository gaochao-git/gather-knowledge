import * as cheerio from 'cheerio';
import logger from '../../core/logger.js';

class WechatParser {
  static parseArticleList(html) {
    const $ = cheerio.load(html);
    const articles = [];

    // 解析文章列表
    $('.news_item').each((index, element) => {
      const $item = $(element);
      const $link = $item.find('a.news_title');
      
      if ($link.length > 0) {
        const article = {
          title: $link.text().trim(),
          url: $link.attr('href'),
          publishTime: $item.find('.time').text().trim(),
          digest: $item.find('.news_digest').text().trim(),
          cover: $item.find('.news_cover img').attr('src') || null
        };

        if (article.title && article.url) {
          articles.push(article);
        }
      }
    });

    return articles;
  }

  static parseArticleDetail(html) {
    const $ = cheerio.load(html);
    
    try {
      const article = {
        title: $('#activity-name').text().trim() || $('.rich_media_title').text().trim(),
        author: $('.rich_media_meta_text').eq(0).text().trim(),
        publishTime: $('#publish_time').text().trim() || $('.rich_media_meta_text').eq(1).text().trim(),
        content: $('#js_content').html() || $('.rich_media_content').html(),
        readCount: null,
        likeCount: null,
        commentCount: null
      };

      // 提取阅读数、点赞数等
      const statsScript = $('script').filter((i, el) => {
        return $(el).html().includes('appmsgstat');
      }).html();

      if (statsScript) {
        const readMatch = statsScript.match(/read_num['"]\s*:\s*(\d+)/);
        const likeMatch = statsScript.match(/like_num['"]\s*:\s*(\d+)/);
        
        if (readMatch) article.readCount = parseInt(readMatch[1]);
        if (likeMatch) article.likeCount = parseInt(likeMatch[1]);
      }

      // 清理内容中的脚本和样式
      if (article.content) {
        const $content = cheerio.load(article.content);
        $content('script, style, .js_darkmode__mask').remove();
        article.content = $content.html();
      }

      return article;
    } catch (error) {
      logger.error('解析文章详情失败:', error);
      return null;
    }
  }

  static extractAccountInfo(html) {
    const $ = cheerio.load(html);
    
    return {
      name: $('.account_name').text().trim() || $('.profile_nickname').text().trim(),
      avatar: $('.account_avatar img').attr('src') || $('.profile_avatar img').attr('src'),
      description: $('.account_desc').text().trim() || $('.profile_desc').text().trim(),
      wechatId: $('.account_id').text().trim() || $('.profile_meta_value').text().trim()
    };
  }

  static isValidArticleUrl(url) {
    return url && (
      url.includes('mp.weixin.qq.com/s') || 
      url.includes('mp.weixin.qq.com/s?') ||
      url.startsWith('http://mp.weixin.qq.com') ||
      url.startsWith('https://mp.weixin.qq.com')
    );
  }

  static normalizeUrl(url) {
    if (!url) return null;
    
    // 移除不必要的参数，保留必要参数
    const urlObj = new URL(url);
    const keepParams = ['__biz', 'mid', 'idx', 'sn'];
    const newSearchParams = new URLSearchParams();
    
    keepParams.forEach(param => {
      if (urlObj.searchParams.has(param)) {
        newSearchParams.set(param, urlObj.searchParams.get(param));
      }
    });
    
    urlObj.search = newSearchParams.toString();
    return urlObj.toString();
  }
}

export default WechatParser;