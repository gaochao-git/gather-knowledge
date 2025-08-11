import express from 'express';
import WechatArticleCollector from '../../collectors/wechat/article-collector.js';
import ArticleModel from '../../storage/models/article-model.js';
import logger from '../../core/logger.js';

const router = express.Router();

// 测试微信采集器
router.post('/wechat/test', async (req, res, next) => {
  try {
    const { accountUrl, articleUrls, maxArticles = 5 } = req.body;
    
    if (!accountUrl && !articleUrls) {
      return res.status(400).json({
        success: false,
        message: '必须提供 accountUrl 或 articleUrls'
      });
    }

    const config = {
      accountUrl,
      articleUrls,
      maxArticles,
      timeout: 30000,
      retryAttempts: 1,
      requestDelay: 1000
    };

    const collector = new WechatArticleCollector(config);
    
    // 收集采集的文章
    const collectedArticles = [];
    collector.on('article_collected', (article) => {
      collectedArticles.push({
        title: article.title,
        url: article.url,
        publishTime: article.publishTime,
        author: article.author
      });
    });

    // 开始采集
    await collector.start();
    const stats = collector.getStats();

    res.json({
      success: true,
      data: {
        articles: collectedArticles,
        stats,
        accountInfo: collector.getAccountInfo()
      },
      message: `测试完成，采集了 ${collectedArticles.length} 篇文章`
    });

  } catch (error) {
    logger.error('微信采集器测试失败:', error);
    next(error);
  }
});

// 立即执行微信采集（保存到数据库）
router.post('/wechat/collect', async (req, res, next) => {
  try {
    const { accountUrl, articleUrls, maxArticles = 20 } = req.body;
    
    if (!accountUrl && !articleUrls) {
      return res.status(400).json({
        success: false,
        message: '必须提供 accountUrl 或 articleUrls'
      });
    }

    const config = {
      accountUrl,
      articleUrls,
      maxArticles,
      timeout: 30000,
      retryAttempts: 3,
      requestDelay: 2000
    };

    const collector = new WechatArticleCollector(config);
    
    // 保存采集的文章
    const savedArticles = [];
    collector.on('article_collected', async (article) => {
      try {
        const savedArticle = await ArticleModel.create(article);
        savedArticles.push(savedArticle);
      } catch (error) {
        logger.error('保存文章失败:', error);
      }
    });

    // 开始采集
    await collector.start();
    const stats = collector.getStats();

    res.json({
      success: true,
      data: {
        savedCount: savedArticles.length,
        stats,
        accountInfo: collector.getAccountInfo()
      },
      message: `采集完成，保存了 ${savedArticles.length} 篇文章`
    });

  } catch (error) {
    logger.error('微信文章采集失败:', error);
    next(error);
  }
});

// 获取支持的采集器列表
router.get('/', (req, res) => {
  res.json({
    success: true,
    data: [
      {
        name: 'wechat',
        displayName: '微信公众号采集器',
        description: '采集微信公众号文章',
        version: '1.0.0',
        configSchema: {
          accountUrl: {
            type: 'string',
            description: '公众号链接',
            required: false
          },
          articleUrls: {
            type: 'array',
            description: '文章链接列表',
            required: false
          },
          maxArticles: {
            type: 'number',
            description: '最大采集文章数',
            default: 20
          }
        }
      }
    ]
  });
});

// 获取微信采集器状态
router.get('/wechat/status', (req, res) => {
  res.json({
    success: true,
    data: {
      name: 'wechat-article-collector',
      status: 'available',
      version: '1.0.0',
      capabilities: [
        '公众号文章列表采集',
        '单篇文章详情采集',
        '文章内容解析',
        '账号信息提取',
        '自动重试机制',
        '性能统计'
      ],
      limitations: [
        '需要有效的文章链接',
        '受目标网站反爬虫策略限制',
        '采集速度受请求延迟影响'
      ]
    }
  });
});

export default router;