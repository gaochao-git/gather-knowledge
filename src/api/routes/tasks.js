import express from 'express';
import logger from '../../core/logger.js';

const router = express.Router();

// 获取任务列表
router.get('/', async (req, res, next) => {
  try {
    const { status, limit = 50 } = req.query;
    let tasks;
    
    if (status) {
      tasks = await req.jobManager.getTasksByStatus(status, parseInt(limit));
    } else {
      tasks = await req.jobManager.getTaskHistory(parseInt(limit));
    }

    res.json({
      success: true,
      data: tasks,
      count: tasks.length
    });
  } catch (error) {
    next(error);
  }
});

// 获取任务详情
router.get('/:id', async (req, res, next) => {
  try {
    const task = await req.jobManager.getTaskById(req.params.id);
    
    if (!task) {
      return res.status(404).json({
        success: false,
        message: '任务不存在'
      });
    }

    res.json({
      success: true,
      data: task
    });
  } catch (error) {
    next(error);
  }
});

// 创建微信文章采集任务
router.post('/wechat/collect', async (req, res, next) => {
  try {
    const { accountUrl, articleUrls, maxArticles, priority, maxRetries } = req.body;
    
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
      priority,
      maxRetries
    };

    const task = await req.jobManager.createWechatCollectionTask(config);
    
    logger.info(`创建微信采集任务: ${task.name}`);
    
    res.json({
      success: true,
      data: task,
      message: '采集任务创建成功'
    });
  } catch (error) {
    next(error);
  }
});

// 创建定时微信采集任务
router.post('/wechat/schedule', async (req, res, next) => {
  try {
    const { name, cronExpression, config } = req.body;
    
    if (!name || !cronExpression || !config) {
      return res.status(400).json({
        success: false,
        message: '缺少必要参数: name, cronExpression, config'
      });
    }

    req.jobManager.scheduleWechatCollection(name, cronExpression, config);
    
    res.json({
      success: true,
      message: `定时任务 ${name} 创建成功`
    });
  } catch (error) {
    next(error);
  }
});

// 取消定时任务
router.delete('/schedule/:name', async (req, res, next) => {
  try {
    const success = req.jobManager.unscheduleTask(req.params.name);
    
    if (!success) {
      return res.status(404).json({
        success: false,
        message: '定时任务不存在'
      });
    }

    res.json({
      success: true,
      message: '定时任务取消成功'
    });
  } catch (error) {
    next(error);
  }
});

// 取消任务
router.post('/:id/cancel', async (req, res, next) => {
  try {
    const success = await req.jobManager.cancelTask(req.params.id);
    
    if (!success) {
      return res.status(404).json({
        success: false,
        message: '任务不存在或无法取消'
      });
    }

    res.json({
      success: true,
      message: '任务取消成功'
    });
  } catch (error) {
    next(error);
  }
});

// 重试任务
router.post('/:id/retry', async (req, res, next) => {
  try {
    const success = await req.jobManager.retryTask(req.params.id);
    
    if (!success) {
      return res.status(404).json({
        success: false,
        message: '任务不存在或无法重试'
      });
    }

    res.json({
      success: true,
      message: '任务已重新排队'
    });
  } catch (error) {
    next(error);
  }
});

// 获取任务统计
router.get('/stats/overview', async (req, res, next) => {
  try {
    const stats = await req.jobManager.getTaskStats();
    
    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    next(error);
  }
});

export default router;