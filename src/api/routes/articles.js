import express from 'express';
import ArticleModel from '../../storage/models/article-model.js';
import logger from '../../core/logger.js';

const router = express.Router();

// 获取文章列表
router.get('/', async (req, res, next) => {
  try {
    const { 
      account, 
      keyword, 
      limit = 20, 
      skip = 0, 
      sort = 'collectedAt',
      order = -1 
    } = req.query;

    let articles;
    
    if (keyword) {
      articles = await ArticleModel.search(keyword, {
        limit: parseInt(limit),
        skip: parseInt(skip)
      });
    } else if (account) {
      articles = await ArticleModel.findByAccount(account, {
        limit: parseInt(limit),
        skip: parseInt(skip),
        sort: { [sort]: parseInt(order) }
      });
    } else {
      articles = await ArticleModel.getRecentArticles(parseInt(limit));
    }

    res.json({
      success: true,
      data: articles,
      count: articles.length
    });
  } catch (error) {
    next(error);
  }
});

// 获取单个文章详情
router.get('/:id', async (req, res, next) => {
  try {
    const article = await ArticleModel.findById(req.params.id);
    
    if (!article) {
      return res.status(404).json({
        success: false,
        message: '文章不存在'
      });
    }

    res.json({
      success: true,
      data: article
    });
  } catch (error) {
    next(error);
  }
});

// 通过URL查找文章
router.get('/url/:encodedUrl', async (req, res, next) => {
  try {
    const url = decodeURIComponent(req.params.encodedUrl);
    const article = await ArticleModel.findByUrl(url);
    
    if (!article) {
      return res.status(404).json({
        success: false,
        message: '文章不存在'
      });
    }

    res.json({
      success: true,
      data: article
    });
  } catch (error) {
    next(error);
  }
});

// 搜索文章
router.post('/search', async (req, res, next) => {
  try {
    const { keyword, limit = 20, options = {} } = req.body;
    
    if (!keyword) {
      return res.status(400).json({
        success: false,
        message: '搜索关键词不能为空'
      });
    }

    const articles = await ArticleModel.search(keyword, {
      limit: parseInt(limit),
      ...options
    });

    res.json({
      success: true,
      data: articles,
      count: articles.length
    });
  } catch (error) {
    next(error);
  }
});

// 获取文章统计
router.get('/stats/overview', async (req, res, next) => {
  try {
    const stats = await ArticleModel.getStats();
    
    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    next(error);
  }
});

// 删除文章
router.delete('/:id', async (req, res, next) => {
  try {
    const success = await ArticleModel.delete(req.params.id);
    
    if (!success) {
      return res.status(404).json({
        success: false,
        message: '文章不存在'
      });
    }

    logger.info(`文章已删除: ${req.params.id}`);
    
    res.json({
      success: true,
      message: '文章删除成功'
    });
  } catch (error) {
    next(error);
  }
});

// 更新文章
router.put('/:id', async (req, res, next) => {
  try {
    const { title, content, tags, metadata } = req.body;
    
    const updateData = {};
    if (title) updateData.title = title;
    if (content) updateData.content = content;
    if (tags) updateData.tags = tags;
    if (metadata) updateData.metadata = metadata;

    const success = await ArticleModel.update(req.params.id, updateData);
    
    if (!success) {
      return res.status(404).json({
        success: false,
        message: '文章不存在'
      });
    }

    res.json({
      success: true,
      message: '文章更新成功'
    });
  } catch (error) {
    next(error);
  }
});

export default router;