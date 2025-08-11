import BaseCollector from '../../core/base-collector.js';
import HttpClient from '../common/http-client.js';
import WechatParser from './wechat-parser.js';
import logger from '../../core/logger.js';
import config from '../../core/config.js';

class WechatArticleCollector extends BaseCollector {
  constructor(options = {}) {
    super('wechat-article-collector', {
      ...config.collectors.wechat,
      ...options
    });

    this.httpClient = new HttpClient({
      timeout: this.config.timeout,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
      }
    });

    this.articles = [];
    this.accountInfo = null;
  }

  async initialize() {
    await super.initialize();
    
    if (!this.config.accountUrl && !this.config.articleUrls) {
      throw new Error('必须提供 accountUrl 或 articleUrls 配置');
    }

    logger.info(`微信采集器配置: ${JSON.stringify(this.config, null, 2)}`);
  }

  async collect() {
    if (this.config.accountUrl) {
      await this.collectByAccount();
    } else if (this.config.articleUrls && Array.isArray(this.config.articleUrls)) {
      await this.collectByArticleUrls();
    }

    logger.info(`采集完成，共获取 ${this.articles.length} 篇文章`);
    return this.articles;
  }

  async collectByAccount() {
    logger.info(`开始采集公众号: ${this.config.accountUrl}`);
    
    try {
      const response = await this.executeWithRetry(() => 
        this.httpClient.get(this.config.accountUrl)
      );

      const html = response.data;
      this.accountInfo = WechatParser.extractAccountInfo(html);
      const articles = WechatParser.parseArticleList(html);

      logger.info(`从公众号页面解析到 ${articles.length} 篇文章`);

      for (const article of articles.slice(0, this.config.maxArticles || 10)) {
        await this.collectArticleDetail(article);
        this.incrementTotal();
        
        // 添加延迟避免被限制
        await this.delay(this.config.requestDelay || 2000);
      }

    } catch (error) {
      logger.error('采集公众号文章失败:', error);
      throw error;
    }
  }

  async collectByArticleUrls() {
    logger.info(`开始采集指定文章，共 ${this.config.articleUrls.length} 篇`);

    for (const url of this.config.articleUrls) {
      if (!WechatParser.isValidArticleUrl(url)) {
        logger.warn(`无效的文章URL: ${url}`);
        continue;
      }

      const article = { url: WechatParser.normalizeUrl(url) };
      await this.collectArticleDetail(article);
      this.incrementTotal();
      
      // 添加延迟
      await this.delay(this.config.requestDelay || 2000);
    }
  }

  async collectArticleDetail(article) {
    try {
      logger.info(`采集文章详情: ${article.title || article.url}`);

      const response = await this.executeWithRetry(() => 
        this.httpClient.get(article.url)
      );

      const articleDetail = WechatParser.parseArticleDetail(response.data);
      
      if (articleDetail) {
        const fullArticle = {
          ...article,
          ...articleDetail,
          url: WechatParser.normalizeUrl(article.url),
          collectedAt: new Date(),
          accountInfo: this.accountInfo,
          collector: this.name
        };

        this.articles.push(fullArticle);
        this.incrementSuccess();
        
        this.emit('article_collected', fullArticle);
        logger.info(`成功采集文章: ${fullArticle.title}`);
      } else {
        logger.warn(`解析文章详情失败: ${article.url}`);
        this.incrementFailed();
      }

    } catch (error) {
      logger.error(`采集文章详情失败 ${article.url}:`, error);
      this.incrementFailed();
    }
  }

  validateConfig() {
    if (!this.config.accountUrl && !this.config.articleUrls) {
      return false;
    }

    if (this.config.articleUrls && !Array.isArray(this.config.articleUrls)) {
      return false;
    }

    return true;
  }

  getCollectedArticles() {
    return this.articles;
  }

  getAccountInfo() {
    return this.accountInfo;
  }
}

export default WechatArticleCollector;